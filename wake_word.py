"""
JARVIS Wake-Word Detector — Whisper-based, free, no external account.

Strategy:
  1. Continuously sample audio in 2-second windows via sounddevice.
  2. When energy crosses a threshold (speech detected), capture until silence.
  3. Transcribe the captured chunk with Whisper.
  4. If the transcript contains "jarvis" (or variants like "java"/"javis"),
     trigger the callback with the FULL transcript so the rest of the
     sentence can be used as the command (no need to listen again).

Pros vs Google Speech wake-word:
  - Works with Indian-English accents
  - No silent failures (we always know what was heard)
  - Doesn't require an internet round-trip per wake-word probe
  - Single shared mic stream (no contention with the command listener)

Pros vs Porcupine:
  - No Picovoice account, no API key, no signup
  - 100% free forever
  - Accent-tolerant (handles "jarvis" / "java" / "javis" / "jervis")
"""

import os
import time
import threading
from collections import deque
from typing import Optional, Callable

import numpy as np
import sounddevice as sd

SAMPLE_RATE        = 16000
FRAME_DUR          = 0.05   # 50 ms frames
ENERGY_THRESHOLD   = 0.015  # RMS gate
SILENCE_HANG_SEC   = 1.2    # silence to end utterance
MIN_UTTERANCE_SEC  = 0.4    # ignore noise blips
MAX_UTTERANCE_SEC  = 25     # safety cap

# Phase 14: STRICT wake-word — only exact "jarvis" forms.
# Previous fuzzy matches (javis/jervis/jarvi) were triggering on TV speech.
# Whisper transcribes "jarvis" reliably enough that fuzzy matching costs more
# in false positives than it gains.
WAKE_TRIGGERS = {"jarvis", "j.a.r.v.i.s", "j a r v i s"}


def _transcribe(audio: np.ndarray, whisper_model) -> str:
    """Run Whisper on a numpy audio buffer. Returns lowercase text."""
    try:
        segments, _ = whisper_model.transcribe(
            audio, beam_size=1, language="en",
            initial_prompt="The user calls JARVIS by name to wake him up. "
                           "JARVIS is the proper noun.",
            vad_filter=False)  # we did our own VAD
        text = " ".join(seg.text.strip() for seg in segments).strip().lower()
        return text
    except Exception:
        return ""


def has_wake_word(text: str) -> bool:
    if not text: return False
    t = text.lower()
    return any(trig in t for trig in WAKE_TRIGGERS)


def strip_wake_word(text: str) -> str:
    """Remove the wake word from the beginning of an utterance, return the
       command part."""
    if not text: return ""
    out = text.strip().lower()
    for trig in sorted(WAKE_TRIGGERS, key=len, reverse=True):
        if trig in out:
            out = out.replace(trig, "", 1)
            break
    return out.strip(" .,!?:;-")


class WakeWordListener:
    """Background thread that continuously listens, detects wake word via
       Whisper, calls callback with full transcript when triggered."""

    def __init__(self, whisper_model, on_wake: Callable[[str], None],
                 device: Optional[int] = None):
        self.whisper = whisper_model
        self.on_wake = on_wake
        self.device = device
        self._stop = threading.Event()
        self._thread = None
        self.last_heard = ""
        self.last_heard_time = 0
        self.pause_event = threading.Event()  # set = paused (don't listen)

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                         name="WakeWordListener")
        self._thread.start()

    def stop(self):
        self._stop.set()

    def pause(self):
        """Pause listening (e.g. while JARVIS is speaking — avoid echo)."""
        self.pause_event.set()

    def resume(self):
        self.pause_event.clear()

    def _loop(self):
        frame_samples = int(SAMPLE_RATE * FRAME_DUR)
        buffer = []
        in_utterance = False
        utterance_start = 0
        silence_since = None

        try:
            stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                                     dtype='float32', blocksize=frame_samples,
                                     device=self.device)
            stream.start()
        except Exception as e:
            print(f"[WakeWordListener] mic init failed: {e}", flush=True)
            return

        while not self._stop.is_set():
            if self.pause_event.is_set():
                time.sleep(0.1)
                buffer.clear()
                in_utterance = False
                continue

            try:
                data, _ = stream.read(frame_samples)
            except Exception:
                time.sleep(0.1); continue

            samples = data[:, 0]
            rms = float(np.sqrt(np.mean(samples ** 2)))

            if rms > ENERGY_THRESHOLD:
                if not in_utterance:
                    in_utterance = True
                    utterance_start = time.time()
                    buffer = []
                silence_since = None
                buffer.append(samples)
            elif in_utterance:
                buffer.append(samples)
                if silence_since is None:
                    silence_since = time.time()
                elif time.time() - silence_since >= SILENCE_HANG_SEC:
                    # End of utterance
                    dur = time.time() - utterance_start
                    if dur >= MIN_UTTERANCE_SEC and dur <= MAX_UTTERANCE_SEC:
                        audio = np.concatenate(buffer)
                        text = _transcribe(audio, self.whisper)
                        self.last_heard = text
                        self.last_heard_time = time.time()
                        if text:
                            print(f"[WakeWord] heard: {text!r}", flush=True)
                        if has_wake_word(text):
                            cmd = strip_wake_word(text)
                            self.pause_event.set()  # don't listen during processing
                            try:
                                self.on_wake(cmd or "")
                            except Exception as e:
                                print(f"[WakeWord] callback error: {e}", flush=True)
                            finally:
                                self.pause_event.clear()
                    # Reset
                    buffer = []
                    in_utterance = False
                    silence_since = None

        try: stream.stop(); stream.close()
        except Exception: pass


# ── Standalone test ─────────────────────────────────────────────
if __name__ == "__main__":
    print("Wake-word test — say 'Jarvis what time is it' or similar.")
    print("(Loading Whisper model — first run downloads ~250MB...)")
    from faster_whisper import WhisperModel
    model = WhisperModel("small.en", device="cpu", compute_type="int8")
    print("Whisper ready. Listening...")

    def on_wake(cmd):
        print(f"\n*** WAKE WORD TRIGGERED ***  command: {cmd!r}\n")

    listener = WakeWordListener(model, on_wake)
    listener.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")
        listener.stop()
