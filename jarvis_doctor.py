"""
JARVIS Doctor — diagnose what's wrong when JARVIS doesn't respond.

Run:
    C:\\Users\\Dev\\JARVIS\\venv\\Scripts\\python.exe C:\\Users\\Dev\\JARVIS\\jarvis_doctor.py

Reports:
  - Is jarvis.py actually running? (process check)
  - When was the last activity in the log? (silent-crash detection)
  - Is the wake-word listener alive? (what did it last hear?)
  - Are the mic and speakers detected?
  - Is the brain reachable (Groq + Ollama fallback)?
  - Is ElevenLabs reachable?
  - Is the HUD process alive?

Pastes a clean PASS/FAIL report you can send to whoever's debugging.
"""

import os
import sys
import time
import json
from datetime import datetime

LOG_FILE = r"C:\Users\Dev\JARVIS\jarvis_runtime.log"
HUD_EVENTS = r"C:\Users\Dev\JARVIS\hud_events.jsonl"


def check(label, fn):
    try:
        ok, detail = fn()
        mark = "✓ PASS" if ok else "✗ FAIL"
        print(f"  {mark}  {label}")
        if detail:
            for ln in str(detail).splitlines()[:6]:
                print(f"          {ln}")
        return ok
    except Exception as e:
        print(f"  ! ERR   {label}: {e}")
        return False


def is_jarvis_running():
    try:
        import psutil
        for p in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info', 'create_time']):
            try:
                cl = ' '.join(str(x) for x in (p.info.get('cmdline') or []))
                nm = (p.info.get('name') or '').lower()
                if 'python' in nm and 'JARVIS' in cl and 'jarvis.py' in cl.lower():
                    mb = p.info['memory_info'].rss / 1024 / 1024 if p.info['memory_info'] else 0
                    age = (datetime.now() - datetime.fromtimestamp(p.info['create_time'])).total_seconds() / 60
                    return True, f"PID {p.info['pid']} {p.info['name']} {mb:.0f}MB age={age:.1f}min"
            except Exception:
                pass
        return False, "No jarvis.py process found. Launch with:\n  C:\\Users\\Dev\\JARVIS\\venv\\Scripts\\pythonw.exe C:\\Users\\Dev\\JARVIS\\jarvis.py"
    except ImportError:
        return False, "psutil not installed"


def log_freshness():
    if not os.path.exists(LOG_FILE):
        return False, "log file missing"
    age = time.time() - os.path.getmtime(LOG_FILE)
    if age > 600:
        return False, f"log not touched in {age:.0f}s — JARVIS may have crashed"
    return True, f"last log update {age:.0f}s ago"


def last_log_lines():
    if not os.path.exists(LOG_FILE):
        return False, "log missing"
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        tail = lines[-8:]
        return True, "".join(tail).strip()
    except Exception as e:
        return False, str(e)


def wake_word_alive():
    """Check if wake-word listener is hearing audio at all."""
    if not os.path.exists(LOG_FILE):
        return False, "no log"
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            data = f.read()
        # Look for recent [WakeWord] heard: entries
        recent = data.split("\n")[-200:]
        heard_lines = [l for l in recent if "[WakeWord] heard:" in l or "[WAKE]" in l]
        if heard_lines:
            return True, f"last heard: {heard_lines[-1][-200:]}"
        return False, ("no wake-word events in last 200 log lines — "
                       "listener may be paused or dead")
    except Exception as e:
        return False, str(e)


def microphone_detected():
    try:
        import sounddevice as sd
        inputs = [d for d in sd.query_devices() if d['max_input_channels'] > 0]
        if not inputs:
            return False, "no input devices"
        names = [f"[{d['name']}]" for d in inputs[:5]]
        return True, " ".join(names)
    except Exception as e:
        return False, str(e)


def whisper_loadable():
    try:
        from faster_whisper import WhisperModel
        return True, "faster-whisper importable"
    except Exception as e:
        return False, str(e)


def elevenlabs_configured():
    try:
        from dotenv import load_dotenv
        load_dotenv(r"C:\Users\Dev\JARVIS\.env")
    except ImportError: pass
    key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not key:
        return False, "ELEVENLABS_API_KEY not in .env"
    if not key.startswith("sk_"):
        return False, "ELEVENLABS_API_KEY looks malformed"
    return True, f"key set ({key[:6]}...{key[-4:]})"


def groq_reachable():
    try:
        from dotenv import load_dotenv
        load_dotenv(r"C:\Users\Dev\JARVIS\.env")
    except ImportError: pass
    try:
        from groq import Groq
        client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "ok"}],
            max_tokens=4,
        )
        return True, f"reply: {r.choices[0].message.content[:40]}"
    except Exception as e:
        return False, str(e)[:200]


def ollama_reachable():
    try:
        import urllib.request, json
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as r:
            data = json.loads(r.read().decode())
        models = [m['name'] for m in data.get("models", [])][:5]
        return True, f"{len(models)} models: {', '.join(models)}"
    except Exception as e:
        return False, str(e)[:150]


def hud_running():
    try:
        import psutil
        for p in psutil.process_iter(['name', 'cmdline']):
            cl = ' '.join(str(x) for x in (p.info.get('cmdline') or []))
            if 'hud_arc.py' in cl.lower() or 'hud.py' in cl.lower():
                return True, f"PID {p.pid} {p.info['name']}"
        return False, "no HUD process found"
    except Exception as e:
        return False, str(e)


def main():
    print()
    print("  ┌─────────────────────────────────────────────────┐")
    print("  │           JARVIS DOCTOR — diagnostic            │")
    print("  └─────────────────────────────────────────────────┘")
    print(f"  Run at: {datetime.now().isoformat(timespec='seconds')}")
    print()
    print("  CORE CHECKS")
    check("JARVIS process running", is_jarvis_running)
    check("Log fresh (touched within 10 min)", log_freshness)
    check("Wake-word listener alive", wake_word_alive)
    check("HUD process running", hud_running)
    print()
    print("  AUDIO STACK")
    check("Microphone(s) detected", microphone_detected)
    check("Whisper STT loadable", whisper_loadable)
    check("ElevenLabs TTS configured", elevenlabs_configured)
    print()
    print("  BRAIN")
    check("Groq cloud reachable", groq_reachable)
    check("Ollama local reachable", ollama_reachable)
    print()
    print("  RECENT LOG TAIL")
    ok, tail = last_log_lines()
    print(tail if tail else "  (empty)")
    print()
    print("  ┌─────────────────────────────────────────────────┐")
    print("  │  If everything PASSES but JARVIS still won't    │")
    print("  │  wake — say 'Jarvis' loud and clear into your   │")
    print("  │  microphone, then tail the log to see what it   │")
    print("  │  actually heard.                                │")
    print("  └─────────────────────────────────────────────────┘")


if __name__ == "__main__":
    main()
