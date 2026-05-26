"""
JARVIS Voice Pipeline — Phase 11
  STT:  faster-whisper (local, accurate, free, handles Indian-English accent)
  TTS:  ElevenLabs (movie-quality voice) with edge-tts fallback
  VAD:  energy-based silence detection via sounddevice
  IRQ:  hard-interrupt (Ctrl+Shift+S / pygame.mixer.music.stop())

Provides drop-in replacements for the old Google-Speech + edge-tts stack:
    transcribe_microphone(timeout_sec) -> str          (listen for one utterance)
    speak_text(text)                  -> bool          (synthesize + play)
    is_speaking()                     -> bool          (currently playing?)
    stop_speaking()                                    (interrupt now)
"""

import os
import io
import time
import wave
import queue
import tempfile
import threading
from typing import Optional

import numpy as np
import sounddevice as sd

# ── Configuration ────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(r"C:\Users\Dev\JARVIS\.env")

ELEVENLABS_API_KEY  = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "onwK4e9ZLuTAKqWW03F9")
ELEVENLABS_MODEL_ID = os.environ.get("ELEVENLABS_MODEL_ID", "eleven_turbo_v2_5")
VOICE_PROVIDER      = os.environ.get("VOICE_PROVIDER", "elevenlabs").lower()
STT_PROVIDER        = os.environ.get("STT_PROVIDER", "whisper").lower()
WHISPER_MODEL       = os.environ.get("WHISPER_MODEL", "small.en")
WHISPER_DEVICE      = os.environ.get("WHISPER_DEVICE", "cpu")

SAMPLE_RATE = 16000   # Whisper expects 16kHz mono
SILENCE_RMS_THRESHOLD = 0.015     # below this = silence
SILENCE_HANG_SEC      = 1.2       # how long silence before we stop recording
MAX_RECORD_SEC        = 30        # safety cap


# ── Lazy globals ─────────────────────────────────────────────────
_whisper_model = None
_eleven_client = None
_currently_playing = False
_play_stop_flag   = threading.Event()


# ─────────────────────────────────────────────────────────────────
# STT — faster-whisper
# ─────────────────────────────────────────────────────────────────
def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        # First call downloads the model (~250MB for small.en). Cached after.
        _whisper_model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE,
                                      compute_type="int8")
    return _whisper_model


def _record_until_silence(timeout_sec: float = 10.0) -> Optional[np.ndarray]:
    """Record audio from default microphone until silence or timeout. Returns
       float32 numpy array at 16kHz mono, or None if nothing captured."""
    frames = []
    silence_since = None
    started_speaking = False
    start = time.time()
    frame_dur = 0.05   # 50 ms frames
    frame_samples = int(SAMPLE_RATE * frame_dur)

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32',
                            blocksize=frame_samples) as stream:
            while True:
                if time.time() - start > timeout_sec and not started_speaking:
                    return None
                if time.time() - start > MAX_RECORD_SEC:
                    break
                data, _ = stream.read(frame_samples)
                samples = data[:, 0]
                rms = float(np.sqrt(np.mean(samples ** 2)))
                frames.append(samples)
                if rms > SILENCE_RMS_THRESHOLD:
                    started_speaking = True
                    silence_since = None
                elif started_speaking:
                    if silence_since is None:
                        silence_since = time.time()
                    elif time.time() - silence_since >= SILENCE_HANG_SEC:
                        break
    except Exception as e:
        print(f"[voice_pipeline] mic error: {e}", flush=True)
        return None

    if not started_speaking or not frames:
        return None
    return np.concatenate(frames)


def transcribe_microphone(timeout_sec: float = 10.0) -> Optional[str]:
    """Listen once for an utterance, transcribe, return text."""
    audio = _record_until_silence(timeout_sec)
    if audio is None or len(audio) < SAMPLE_RATE * 0.3:
        return None
    return transcribe_audio_array(audio)


def transcribe_audio_array(audio: np.ndarray) -> Optional[str]:
    model = _get_whisper()
    segments, info = model.transcribe(
        audio, beam_size=1, language="en",
        initial_prompt="JARVIS is Mr. Stark's personal AI assistant. Mr. Stark is the user.",
        vad_filter=True, vad_parameters={"min_silence_duration_ms": 400})
    out = " ".join(seg.text.strip() for seg in segments).strip()
    return out or None


def transcribe_file(path: str) -> Optional[str]:
    """Transcribe a wav/mp3/flac file. Used for testing."""
    model = _get_whisper()
    segments, _ = model.transcribe(
        path, beam_size=1, language="en",
        initial_prompt="JARVIS is Mr. Stark's personal AI assistant. Mr. Stark is the user.")
    return " ".join(s.text.strip() for s in segments).strip() or None


# ─────────────────────────────────────────────────────────────────
# TTS — ElevenLabs (primary) + edge-tts (fallback)
# ─────────────────────────────────────────────────────────────────
def _get_elevenlabs():
    global _eleven_client
    if _eleven_client is None:
        from elevenlabs.client import ElevenLabs
        _eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    return _eleven_client


def _synthesize_elevenlabs(text: str, save_path: str = None) -> Optional[bytes]:
    if not ELEVENLABS_API_KEY:
        return None
    try:
        client = _get_elevenlabs()
        stream = client.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID,
            model_id=ELEVENLABS_MODEL_ID,
            text=text,
            output_format="mp3_22050_32",
        )
        # collect chunks
        audio_bytes = b"".join(chunk for chunk in stream if chunk)
        if save_path:
            with open(save_path, "wb") as f:
                f.write(audio_bytes)
        return audio_bytes
    except Exception as e:
        print(f"[voice_pipeline] ElevenLabs error: {e}", flush=True)
        return None


def _synthesize_edge_tts(text: str, save_path: str = None) -> Optional[bytes]:
    try:
        import edge_tts
        import asyncio
        async def _do():
            comm = edge_tts.Communicate(text, "en-GB-RyanNeural")
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tmp.close()
            await comm.save(tmp.name)
            with open(tmp.name, "rb") as f:
                data = f.read()
            try: os.remove(tmp.name)
            except Exception: pass
            return data
        data = asyncio.run(_do())
        if save_path and data:
            with open(save_path, "wb") as f:
                f.write(data)
        return data
    except Exception as e:
        print(f"[voice_pipeline] edge-tts error: {e}", flush=True)
        return None


def synthesize_to_file(text: str, save_path: str) -> bool:
    """Synthesize text to disk as MP3. Used for proofs."""
    if VOICE_PROVIDER == "elevenlabs":
        data = _synthesize_elevenlabs(text, save_path)
        if data: return True
        # Fallback
    data = _synthesize_edge_tts(text, save_path)
    return data is not None


def _play_mp3_bytes(data: bytes) -> bool:
    """Decode + play MP3 bytes via pygame.mixer.music. Returns True on success."""
    global _currently_playing
    try:
        import pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tmp.write(data); tmp.close()
        pygame.mixer.music.load(tmp.name)
        _currently_playing = True
        _play_stop_flag.clear()
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            if _play_stop_flag.is_set():
                pygame.mixer.music.stop()
                break
            time.sleep(0.05)
        pygame.mixer.music.unload()
        try: os.remove(tmp.name)
        except Exception: pass
        _currently_playing = False
        return True
    except Exception as e:
        _currently_playing = False
        print(f"[voice_pipeline] playback error: {e}", flush=True)
        return False


def speak_text(text: str) -> bool:
    """Synthesize text and play it. Returns True if audio actually played."""
    if not text or not text.strip():
        return False
    data = None
    if VOICE_PROVIDER == "elevenlabs" and ELEVENLABS_API_KEY:
        data = _synthesize_elevenlabs(text)
    if data is None:
        data = _synthesize_edge_tts(text)
    if data is None:
        return False
    return _play_mp3_bytes(data)


def is_speaking() -> bool:
    return _currently_playing


def stop_speaking():
    _play_stop_flag.set()


# ─────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    print(f"VOICE_PROVIDER = {VOICE_PROVIDER}")
    print(f"STT_PROVIDER   = {STT_PROVIDER}")
    print(f"ELEVENLABS_API = {'set' if ELEVENLABS_API_KEY else 'MISSING'}")
    print(f"WHISPER_MODEL  = {WHISPER_MODEL}")
    if len(sys.argv) > 1 and sys.argv[1] == "tts":
        out = os.path.join(os.path.dirname(__file__), "_tts_proof.mp3")
        msg = "Good evening, Mister Stark. Voice systems are now online with movie-grade clarity."
        ok = synthesize_to_file(msg, out)
        size = os.path.getsize(out) if os.path.exists(out) else 0
        print(f"TTS test: success={ok}, file={out}, size={size} bytes")
    elif len(sys.argv) > 1 and sys.argv[1] == "stt":
        path = sys.argv[2]
        text = transcribe_file(path)
        print(f"STT result: {text}")
    elif len(sys.argv) > 1 and sys.argv[1] == "round-trip":
        out = os.path.join(os.path.dirname(__file__), "_tts_proof.mp3")
        msg = "JARVIS voice pipeline is fully operational, Mr. Stark."
        ok = synthesize_to_file(msg, out)
        print(f"Synthesized: {ok}, {os.path.getsize(out)} bytes")
        text = transcribe_file(out)
        print(f"Whisper transcribed it as: {text!r}")
