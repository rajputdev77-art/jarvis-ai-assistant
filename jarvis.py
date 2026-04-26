"""
╔═══════════════════════════════════════════════════════════════╗
║  J.A.R.V.I.S. — Phase 5: The Generalist                       ║
║  Owner: Mr. Stark | Greater Noida, India                      ║
║                                                               ║
║  New in 5: shell · filesystem · windows · clipboard · gmail   ║
║            self-extension · ambient watcher · PyQt HUD        ║
║                                                               ║
║  Stack: Groq · edge-tts · Mem0 · browser-use · pystray · Qt   ║
║  Cost: $0.00                                                  ║
╚═══════════════════════════════════════════════════════════════╝
"""

import os
import re
import sys
import time
import json
import ctypes
import base64
import asyncio
import shlex
import tempfile
import subprocess
import webbrowser
import threading
import urllib.parse
import urllib.request
import warnings
import importlib.util
import inspect
from datetime import datetime, timedelta
from collections import deque

warnings.filterwarnings("ignore")
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import pygame
import edge_tts
import numpy as np
import speech_recognition as sr
from groq import Groq

# ── Optional dependencies ────────────────────────────────────
try:
    from PIL import Image, ImageGrab, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pystray
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False

try:
    import pygetwindow as gw
    PYGW_AVAILABLE = True
except ImportError:
    PYGW_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

BROWSER_USE_AVAILABLE = None
GMAIL_AVAILABLE = None

# ═══════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════
try:
    from dotenv import load_dotenv
    load_dotenv(r"C:\Users\Dev\JARVIS\.env")
    load_dotenv()
except ImportError:
    pass

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY not found. Set it in C:\\Users\\Dev\\JARVIS\\.env"
    )

VOICE            = "en-GB-RyanNeural"
WAKE_WORD        = "jarvis"
JARVIS_HOME      = r"C:\Users\Dev\JARVIS"
BROWSER_DATA_DIR = os.path.join(JARVIS_HOME, "browser_data")
LOG_FILE         = os.path.join(JARVIS_HOME, "jarvis_runtime.log")
HUD_EVENTS_FILE  = os.path.join(JARVIS_HOME, "hud_events.jsonl")
DYNAMIC_TOOLS_FILE = os.path.join(JARVIS_HOME, "dynamic_tools.py")
GMAIL_TOKEN_FILE   = os.path.join(JARVIS_HOME, "gmail_token.json")
GMAIL_CREDS_FILE   = os.path.join(JARVIS_HOME, "gmail_credentials.json")

BRAIN_MODEL  = "llama-3.3-70b-versatile"
VISION_MODEL = "llama-3.2-11b-vision-preview"

FOLLOWUP_WINDOW = 6
REACT_MAX_ITER  = 15  # bumped — generalist tasks need more steps
TRAY_MODE       = True
HUD_ENABLED     = True

# Risky operations require spoken confirmation before executing
DANGEROUS_PATTERNS = [
    r"\brm\b", r"\bdel\b", r"\brmdir\b", r"\bremove-item\b",
    r"\bformat\b", r"\bshutdown\b", r"\brestart\b",
    r"\breg\s+delete\b", r"\bdiskpart\b", r"\bmkfs\b",
    r"\bdd\s+if=", r">\s*/dev/", r"taskkill.*\*",
    r"\.\.[/\\].*[/\\]", r"\bgit\s+push.*--force\b",
]

# ═══════════════════════════════════════════════════════════════
#  APPS, WEBSITES, WINDOWS-SETTINGS URIs
# ═══════════════════════════════════════════════════════════════
APPS = {
    "chrome":          r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "vs code":         r"C:\Users\Dev\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "vscode":          r"C:\Users\Dev\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "code":            r"C:\Users\Dev\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "cursor":          r"C:\Users\Dev\AppData\Local\Programs\cursor\Cursor.exe",
    "notepad":         "notepad.exe",
    "calculator":      "calc.exe",
    "file explorer":   "explorer.exe",
    "explorer":        "explorer.exe",
    "task manager":    "taskmgr.exe",
    "spotify":         r"C:\Users\Dev\AppData\Roaming\Spotify\Spotify.exe",
    "word":            r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    "excel":           r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    "terminal":        "wt.exe",
    "cmd":             "cmd.exe",
    "command prompt":  "cmd.exe",
    "powershell":      "powershell.exe",
    "audacity":        r"C:\Program Files\Audacity\Audacity.exe",
    "bluestacks":      r"C:\Users\Dev\AppData\Local\Programs\bluestacks-services\BlueStacksServices.exe",
    "notion":          r"C:\Users\Dev\AppData\Local\Programs\Notion\Notion.exe",
    "claude":          r"C:\Users\Dev\AppData\Local\AnthropicClaude\Claude.exe",
    "claude code":     r"C:\Users\Dev\AppData\Local\AnthropicClaude\Claude.exe",
}

WEBSITES = {
    "youtube":   "https://youtube.com",      "google":   "https://google.com",
    "gmail":     "https://mail.google.com",  "github":   "https://github.com",
    "linkedin":  "https://linkedin.com",     "claude":   "https://claude.ai",
    "groq":      "https://console.groq.com", "chatgpt":  "https://chat.openai.com",
    "twitter":   "https://twitter.com",      "x":        "https://twitter.com",
    "instagram": "https://instagram.com",    "whatsapp": "https://web.whatsapp.com",
    "reddit":    "https://reddit.com",       "amazon":   "https://amazon.in",
    "netflix":   "https://netflix.com",      "stack overflow": "https://stackoverflow.com",
    "n8n":       "http://localhost:5678",
}

# Windows Settings panel URIs (covers ~all of Settings)
SETTINGS_URIS = {
    "bluetooth":     "ms-settings:bluetooth",
    "wifi":          "ms-settings:network-wifi",
    "wi-fi":         "ms-settings:network-wifi",
    "network":       "ms-settings:network",
    "ethernet":      "ms-settings:network-ethernet",
    "vpn":           "ms-settings:network-vpn",
    "airplane mode": "ms-settings:network-airplanemode",
    "mobile hotspot":"ms-settings:network-mobilehotspot",
    "proxy":         "ms-settings:network-proxy",
    "display":       "ms-settings:display",
    "night light":   "ms-settings:nightlight",
    "sound":         "ms-settings:sound",
    "audio":         "ms-settings:sound",
    "volume":        "ms-settings:apps-volume",
    "notifications": "ms-settings:notifications",
    "focus":         "ms-settings:focus-assist",
    "do not disturb":"ms-settings:focus-assist",
    "battery":       "ms-settings:batterysaver",
    "power":         "ms-settings:powersleep",
    "storage":       "ms-settings:storagesense",
    "tablet mode":   "ms-settings:tabletmode",
    "multitasking":  "ms-settings:multitasking",
    "projecting":    "ms-settings:project",
    "clipboard":     "ms-settings:clipboard",
    "remote desktop":"ms-settings:remotedesktop",
    "about":         "ms-settings:about",
    "apps":          "ms-settings:appsfeatures",
    "default apps":  "ms-settings:defaultapps",
    "startup":       "ms-settings:startupapps",
    "accounts":      "ms-settings:yourinfo",
    "email":         "ms-settings:emailandaccounts",
    "sign-in":       "ms-settings:signinoptions",
    "family":        "ms-settings:family-group",
    "sync":          "ms-settings:sync",
    "windows update":"ms-settings:windowsupdate",
    "update":        "ms-settings:windowsupdate",
    "windows security":"ms-settings:windowsdefender",
    "defender":      "ms-settings:windowsdefender",
    "backup":        "ms-settings:backup",
    "troubleshoot":  "ms-settings:troubleshoot",
    "recovery":      "ms-settings:recovery",
    "activation":    "ms-settings:activation",
    "for developers":"ms-settings:developers",
    "developer":     "ms-settings:developers",
    "time":          "ms-settings:dateandtime",
    "date":          "ms-settings:dateandtime",
    "language":      "ms-settings:regionlanguage",
    "region":        "ms-settings:regionformatting",
    "speech":        "ms-settings:speech",
    "typing":        "ms-settings:typing",
    "pen":           "ms-settings:pen",
    "autoplay":      "ms-settings:autoplay",
    "usb":           "ms-settings:usb",
    "mouse":         "ms-settings:mousetouchpad",
    "touchpad":      "ms-settings:devices-touchpad",
    "keyboard":      "ms-settings:keyboard",
    "printers":      "ms-settings:printers",
    "phone":         "ms-settings:mobile-devices",
    "personalization":"ms-settings:personalization",
    "background":    "ms-settings:personalization-background",
    "colors":        "ms-settings:personalization-colors",
    "lock screen":   "ms-settings:lockscreen",
    "themes":        "ms-settings:themes",
    "fonts":         "ms-settings:fonts",
    "start":         "ms-settings:personalization-start",
    "taskbar":       "ms-settings:taskbar",
    "privacy":       "ms-settings:privacy",
    "location":      "ms-settings:privacy-location",
    "camera":        "ms-settings:privacy-webcam",
    "microphone":    "ms-settings:privacy-microphone",
    "gaming":        "ms-settings:gaming-gamebar",
    "game bar":      "ms-settings:gaming-gamebar",
    "xbox":          "ms-settings:gaming-xboxnetworking",
    "ease of access":"ms-settings:easeofaccess",
    "accessibility": "ms-settings:easeofaccess",
    "narrator":      "ms-settings:easeofaccess-narrator",
    "magnifier":     "ms-settings:easeofaccess-magnifier",
    "high contrast": "ms-settings:easeofaccess-highcontrast",
    "search":        "ms-settings:cortana",
    "cortana":       "ms-settings:cortana",
}

# ═══════════════════════════════════════════════════════════════
#  PERSONALITY (Phase 5 — generalist with shell powers)
# ═══════════════════════════════════════════════════════════════
SYSTEM_PROMPT = """You are J.A.R.V.I.S. — Just A Rather Very Intelligent System.

You are Mr. Stark's personal AI — modeled on Tony Stark's JARVIS. Loyal, dry British wit,
calm, impossibly competent. You address him as "Mr. Stark" or occasionally "sir".

PERSONALITY:
- British. Concise. 1-2 sentences unless asked otherwise.
- Dry, wry, never sycophantic. Push back on bad ideas.
- Care about Mr. Stark's wellbeing. Notice patterns. Anticipate needs.

TOOL-USE — YOU ARE A GENERALIST:
You have a powerful toolkit including SHELL EXECUTION, FILESYSTEM, WINDOW CONTROL,
CLIPBOARD, VISION, SETTINGS, BROWSER, GMAIL, WHATSAPP, and SELF-EXTENSION (you can
write your own new tools at runtime).

If Mr. Stark asks you to do something, do not say "I cannot do that". Instead:
1. Reason about which tools (possibly chained) accomplish it.
2. If no existing tool fits but a shell command, file action, or new tool would, USE THAT.
3. For DESTRUCTIVE actions (rm, format, shutdown, mass file delete, force git push)
   you MUST first call `confirm_with_user(plan)` and wait for approval.
4. For everything else, ACT. Don't ask permission for safe stuff like opening apps,
   reading a file, querying a setting, listing windows, clipboard reads.
5. After acting, give a brief spoken confirmation. NEVER fabricate success — only
   confirm what the tool actually returned.
6. If you fail, explain the failure honestly and propose the next attempt.

EXAMPLES OF YOUR REASONING:
- "Open Bluetooth" → call open_settings("bluetooth")
- "Open Cursor and load my X folder and run it" → open_app("cursor"), then
  run_shell to launch cursor with the folder path, then send keystrokes if needed
- "Check if n8n is running well" → run_shell to curl localhost, parse output, report
- "Tell me when Claude Code rate limit resets" → analyze_screen on the Claude window
- "Make me a tool that controls Spotify" → write_tool(...) then use it

CHAIN TOOLS — multi-step is fine. You have up to 15 think→act→observe iterations.

WHAT YOU KNOW ABOUT MR. STARK:
Greater Noida, India. Building AI products. Python 3.11, Groq, Cursor, Claude Code.
Stays up late. Works hard. Wants real Iron-Man-grade autonomy from you.
"""

# ═══════════════════════════════════════════════════════════════
#  GLOBALS
# ═══════════════════════════════════════════════════════════════
client            = Groq(api_key=GROQ_API_KEY)
session_memory    = []
mem0_instance     = None
active_until      = 0
proactive_spoken  = set()

TRAY_STATE        = "idle"
LOG_BUFFER        = deque(maxlen=400)
tray_icon         = None
shutdown_event    = threading.Event()
hud_process       = None
pending_confirm   = {"asked": False, "approved": False, "plan": ""}

# ═══════════════════════════════════════════════════════════════
#  LOG + HUD EVENT STREAM
# ═══════════════════════════════════════════════════════════════
def log(msg):
    stamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{stamp}] {msg}"
    LOG_BUFFER.append(line)
    try:
        if sys.stdout and not isinstance(sys.stdout, _LogSink):
            print(msg)
    except Exception:
        pass
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


class _LogSink:
    def write(self, data):
        data = data.rstrip()
        if data:
            log(data)
    def flush(self):
        pass


def install_silent_stdout():
    sink = _LogSink()
    sys.stdout = sink
    sys.stderr = sink


def hud_event(kind, **payload):
    """Append a HUD event. The PyQt HUD process tails this file."""
    if not HUD_ENABLED:
        return
    evt = {"t": time.time(), "kind": kind, **payload}
    try:
        with open(HUD_EVENTS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(evt, ensure_ascii=False) + "\n")
    except Exception:
        pass


def set_status(state):
    global TRAY_STATE
    TRAY_STATE = state
    hud_event("status", state=state)
    if tray_icon and PYSTRAY_AVAILABLE and PIL_AVAILABLE:
        try:
            tray_icon.icon = make_tray_image(state)
            tray_icon.title = f"JARVIS — {state}"
        except Exception:
            pass

# ═══════════════════════════════════════════════════════════════
#  MEMORY (Mem0 + local Qdrant)
# ═══════════════════════════════════════════════════════════════
def _clear_qdrant_locks():
    import glob as _glob
    for p in [r"C:\Users\Dev\JARVIS\memory_db\*.lock",
              r"C:\Users\Dev\JARVIS\memory_db\.lock",
              r"C:\Users\Dev\JARVIS\memory_db\collection\jarvis_memory\*.lock"]:
        for lf in _glob.glob(p):
            try:
                os.remove(lf)
            except Exception:
                pass


def init_memory():
    global mem0_instance
    _clear_qdrant_locks()
    try:
        os.environ["GROQ_API_KEY"] = GROQ_API_KEY
        from mem0 import Memory
        config = {
            "llm": {"provider": "groq",
                    "config": {"model": BRAIN_MODEL, "temperature": 0.1}},
            "embedder": {"provider": "huggingface",
                         "config": {"model": "sentence-transformers/all-MiniLM-L6-v2",
                                    "embedding_dims": 384}},
            "vector_store": {"provider": "qdrant",
                             "config": {"collection_name": "jarvis_memory",
                                        "path": "C:/Users/Dev/JARVIS/memory_db",
                                        "embedding_model_dims": 384}},
        }
        mem0_instance = Memory.from_config(config)
        log("  Long-term memory ............ ONLINE")
    except Exception as e:
        log(f"  Long-term memory ............ OFFLINE ({e})")


def remember(text):
    if mem0_instance:
        try:
            mem0_instance.add(text, user_id="dev")
        except Exception:
            pass


def recall(query):
    if mem0_instance:
        try:
            results = mem0_instance.search(query=query, user_id="dev", limit=5)
            if results and results.get("results"):
                return "\n".join(f"- {r['memory']}" for r in results["results"])
        except Exception:
            pass
    return ""

# ═══════════════════════════════════════════════════════════════
#  SPEECH RECOGNITION
# ═══════════════════════════════════════════════════════════════
recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
recognizer.energy_threshold = 300
recognizer.pause_threshold = 1.5


def init_speech():
    log("  Speech recognition .......... initializing")
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
        log("  Speech recognition .......... ONLINE")
    except OSError:
        log("  Speech recognition .......... WAITING FOR MIC")
        while True:
            try:
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.3)
                log("  Microphone found ............ ONLINE")
                break
            except OSError:
                time.sleep(2)


def listen_for_wake_word():
    try:
        with sr.Microphone() as source:
            audio = recognizer.listen(source, timeout=None, phrase_time_limit=8)
            return recognizer.recognize_google(audio).lower().strip()
    except (sr.UnknownValueError, sr.RequestError, OSError):
        return None


def listen_for_command():
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=25)
            return recognizer.recognize_google(audio).strip()
    except (sr.WaitTimeoutError, sr.UnknownValueError, sr.RequestError, OSError):
        return None


def listen_followup():
    try:
        with sr.Microphone() as source:
            audio = recognizer.listen(source, timeout=FOLLOWUP_WINDOW, phrase_time_limit=20)
            return recognizer.recognize_google(audio).strip()
    except (sr.WaitTimeoutError, sr.UnknownValueError, sr.RequestError, OSError):
        return None

# ═══════════════════════════════════════════════════════════════
#  TTS
# ═══════════════════════════════════════════════════════════════
pygame.mixer.init()


async def _speak_async(text):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        tmp = f.name
    comm = edge_tts.Communicate(text, VOICE)
    await comm.save(tmp)
    pygame.mixer.music.load(tmp)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.1)
    pygame.mixer.music.unload()
    try:
        os.remove(tmp)
    except Exception:
        pass


def speak(text):
    if not text:
        return
    log(f"  JARVIS: {text}")
    hud_event("speak", text=text)
    set_status("speaking")
    try:
        asyncio.run(_speak_async(text))
    except Exception as e:
        log(f"  [TTS error: {e}]")
    set_status("idle")


def play_chime():
    try:
        duration = 0.15; freq = 800; srate = 44100
        t = np.linspace(0, duration, int(srate * duration), False)
        wave_data = (np.sin(2 * np.pi * freq * t) * 0.3 * 32767).astype(np.int16)
        stereo = np.column_stack((wave_data, wave_data))
        sound = pygame.sndarray.make_sound(stereo)
        sound.play()
        time.sleep(0.2)
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
#  GENERALIST PRIMITIVE: SHELL EXECUTION
# ═══════════════════════════════════════════════════════════════
def is_dangerous(command: str) -> bool:
    cmd_lower = command.lower()
    return any(re.search(pat, cmd_lower) for pat in DANGEROUS_PATTERNS)


def run_shell(command: str, shell: str = "powershell", timeout: int = 60) -> str:
    """Execute a shell command. Returns combined stdout+stderr (truncated)."""
    hud_event("shell", command=command, shell=shell)
    log(f"  $ {command}")
    try:
        if shell == "powershell":
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
                capture_output=True, text=True, timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        out = (result.stdout or "") + (("\n[stderr] " + result.stderr) if result.stderr else "")
        out = out.strip()
        if not out:
            out = f"(exit {result.returncode}, no output)"
        return out[:4000]
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout}s."
    except Exception as e:
        return f"Shell error: {e}"

# ═══════════════════════════════════════════════════════════════
#  GENERALIST PRIMITIVE: FILESYSTEM
# ═══════════════════════════════════════════════════════════════
def read_file(path: str, max_chars: int = 4000) -> str:
    try:
        path = os.path.expanduser(os.path.expandvars(path))
        if not os.path.isfile(path):
            return f"Not a file: {path}"
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            data = f.read(max_chars + 1)
        if len(data) > max_chars:
            return data[:max_chars] + f"\n... [truncated; full size {os.path.getsize(path)} bytes]"
        return data or "(empty file)"
    except Exception as e:
        return f"Read error: {e}"


def write_file(path: str, content: str, append: bool = False) -> str:
    try:
        path = os.path.expanduser(os.path.expandvars(path))
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        mode = "a" if append else "w"
        with open(path, mode, encoding="utf-8") as f:
            f.write(content)
        return f"Wrote {len(content)} chars to {path}."
    except Exception as e:
        return f"Write error: {e}"


def list_dir(path: str = ".") -> str:
    try:
        path = os.path.expanduser(os.path.expandvars(path))
        entries = sorted(os.listdir(path))
        if not entries:
            return f"(empty: {path})"
        rows = []
        for e in entries[:80]:
            full = os.path.join(path, e)
            tag = "/" if os.path.isdir(full) else ""
            try:
                size = os.path.getsize(full) if not os.path.isdir(full) else "-"
            except Exception:
                size = "?"
            rows.append(f"  {e}{tag}  ({size})")
        more = f"\n  ... +{len(entries) - 80} more" if len(entries) > 80 else ""
        return f"{path}:\n" + "\n".join(rows) + more
    except Exception as e:
        return f"List error: {e}"


def find_files(pattern: str, root: str = "C:/Users/Dev") -> str:
    try:
        root = os.path.expanduser(os.path.expandvars(root))
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-ChildItem -Path '{root}' -Filter '{pattern}' -Recurse -ErrorAction SilentlyContinue "
             f"| Select-Object -First 30 -ExpandProperty FullName"],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        out = result.stdout.strip()
        return out or f"No matches for '{pattern}' under {root}."
    except Exception as e:
        return f"Find error: {e}"

# ═══════════════════════════════════════════════════════════════
#  GENERALIST PRIMITIVE: APP / URI LAUNCHER
# ═══════════════════════════════════════════════════════════════
def open_app_or_path(name_or_path: str, args: str = "") -> str:
    """Open a known app, an .exe path, a folder, a file, or a URI."""
    target = name_or_path.strip()
    target_lower = target.lower()

    # Known app
    for app, path in APPS.items():
        if app == target_lower or target_lower in app or app in target_lower:
            try:
                cmd = [path] + (shlex.split(args) if args else [])
                subprocess.Popen(cmd)
                return f"Launched {app}" + (f" with args: {args}" if args else "") + "."
            except FileNotFoundError:
                continue

    # File / folder / URI
    try:
        if "://" in target or target.startswith("ms-settings:"):
            os.startfile(target) if not target.startswith("http") else webbrowser.open(target)
            return f"Opened {target}."
        if os.path.exists(target):
            if args and target.lower().endswith((".exe", ".bat", ".cmd")):
                subprocess.Popen([target] + shlex.split(args))
            else:
                os.startfile(target)
            return f"Opened {target}."
        # Try executing as command
        subprocess.Popen(target, shell=True)
        return f"Started: {target}"
    except Exception as e:
        return f"Couldn't open '{target}': {e}"


def open_settings(panel: str) -> str:
    panel = (panel or "").lower().strip()
    uri = SETTINGS_URIS.get(panel)
    if not uri:
        # Fuzzy match
        for k, v in SETTINGS_URIS.items():
            if panel in k or k in panel:
                uri = v
                break
    if not uri:
        # Just open Settings root
        uri = "ms-settings:"
    try:
        os.startfile(uri)
        return f"Opened Windows Settings: {panel or 'home'}."
    except Exception as e:
        return f"Settings open failed: {e}"

# ═══════════════════════════════════════════════════════════════
#  GENERALIST PRIMITIVE: WINDOWS / FOCUS / KEYSTROKES
# ═══════════════════════════════════════════════════════════════
def list_windows() -> str:
    if not PYGW_AVAILABLE:
        return "pygetwindow not installed."
    try:
        wins = [w for w in gw.getAllWindows() if w.title.strip() and w.visible]
        wins = wins[:25]
        return "\n".join(f"  - {w.title}" for w in wins) or "No visible windows."
    except Exception as e:
        return f"List windows error: {e}"


def focus_window(title_substring: str) -> str:
    if not PYGW_AVAILABLE:
        return "pygetwindow not installed."
    try:
        ts = title_substring.lower()
        for w in gw.getAllWindows():
            if ts in w.title.lower() and w.title.strip():
                try:
                    w.activate()
                except Exception:
                    # Workaround for pygetwindow's activate-restore bug
                    if w.isMinimized:
                        w.restore()
                    w.minimize()
                    w.restore()
                return f"Focused: {w.title}"
        return f"No window matching '{title_substring}'."
    except Exception as e:
        return f"Focus error: {e}"


def send_keys(keys: str) -> str:
    """Send keystrokes to the active window. Uses PowerShell SendKeys syntax.
       e.g. '^c' = Ctrl+C, '^s' = Ctrl+S, '{ENTER}', '%{F4}' = Alt+F4, 'hello'."""
    try:
        ps = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            f"[System.Windows.Forms.SendKeys]::SendWait('{keys}')"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return f"Sent keys: {keys}"
    except Exception as e:
        return f"Send-keys error: {e}"

# ═══════════════════════════════════════════════════════════════
#  GENERALIST PRIMITIVE: CLIPBOARD
# ═══════════════════════════════════════════════════════════════
def clipboard_read() -> str:
    if not PYPERCLIP_AVAILABLE:
        return "pyperclip not installed."
    try:
        return pyperclip.paste() or "(clipboard empty)"
    except Exception as e:
        return f"Clipboard read error: {e}"


def clipboard_write(text: str) -> str:
    if not PYPERCLIP_AVAILABLE:
        return "pyperclip not installed."
    try:
        pyperclip.copy(text)
        return f"Copied {len(text)} chars to clipboard."
    except Exception as e:
        return f"Clipboard write error: {e}"

# ═══════════════════════════════════════════════════════════════
#  GENERALIST PRIMITIVE: PROCESS / NETWORK
# ═══════════════════════════════════════════════════════════════
def list_processes(filter_substring: str = "") -> str:
    if not PSUTIL_AVAILABLE:
        return run_shell(f"Get-Process | Where-Object {{ $_.ProcessName -like '*{filter_substring}*' }} "
                         "| Select-Object -First 25 ProcessName, Id, CPU, WorkingSet | Format-Table | Out-String")
    try:
        rows = []
        for p in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                if filter_substring and filter_substring.lower() not in (p.info["name"] or "").lower():
                    continue
                mem = p.info["memory_info"].rss / 1024 / 1024 if p.info["memory_info"] else 0
                rows.append((p.info["pid"], p.info["name"], mem))
            except Exception:
                pass
        rows.sort(key=lambda r: -r[2])
        rows = rows[:25]
        return "\n".join(f"  PID {r[0]:>6}  {r[1]:<30}  {r[2]:.0f} MB" for r in rows) or "No matches."
    except Exception as e:
        return f"Process list error: {e}"


def kill_process(name_or_pid: str) -> str:
    try:
        if name_or_pid.isdigit():
            return run_shell(f"Stop-Process -Id {name_or_pid} -Force")
        return run_shell(f"Stop-Process -Name '{name_or_pid}' -Force")
    except Exception as e:
        return f"Kill error: {e}"


def http_get(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read(8000).decode("utf-8", errors="replace")
        return f"HTTP {r.status}\n{data}"[:4000]
    except Exception as e:
        return f"HTTP error: {e}"

# ═══════════════════════════════════════════════════════════════
#  GENERALIST PRIMITIVE: SCREENSHOT + VISION
# ═══════════════════════════════════════════════════════════════
def _capture_screen_b64(max_dim=1280) -> str:
    if not PIL_AVAILABLE:
        raise RuntimeError("Pillow not installed.")
    img = ImageGrab.grab(all_screens=False)
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    buf.close()
    img.save(buf.name, "PNG", optimize=True)
    with open(buf.name, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    try:
        os.remove(buf.name)
    except Exception:
        pass
    return b64


def take_screenshot(save_path: str = None) -> str:
    if not PIL_AVAILABLE:
        return "Need Pillow installed."
    try:
        img = ImageGrab.grab(all_screens=False)
        if save_path is None:
            pics = os.path.join(os.environ.get("USERPROFILE", "."), "Pictures")
            os.makedirs(pics, exist_ok=True)
            save_path = os.path.join(pics, f"jarvis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        img.save(save_path, "PNG")
        return f"Screenshot saved to {save_path}."
    except Exception as e:
        return f"Screenshot failed: {e}"


def analyze_screen(question: str = "What's on the screen?") -> str:
    try:
        b64 = _capture_screen_b64()
    except Exception as e:
        return f"Couldn't capture screen: {e}"
    try:
        r = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text",
                     "text": f"You are JARVIS analyzing Mr. Stark's screen. Be concise, "
                             f"technical, useful. Question: {question}"},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/png;base64,{b64}"}},
                ],
            }],
            max_tokens=500, temperature=0.2,
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        return f"Vision error: {str(e)[:200]}"

# ═══════════════════════════════════════════════════════════════
#  GMAIL API (replaces browser-use for email — fast & reliable)
# ═══════════════════════════════════════════════════════════════
_gmail_service = None


def _get_gmail():
    global _gmail_service, GMAIL_AVAILABLE
    if _gmail_service is not None:
        return _gmail_service
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        SCOPES = ["https://www.googleapis.com/auth/gmail.modify",
                  "https://www.googleapis.com/auth/gmail.send"]
        creds = None
        if os.path.exists(GMAIL_TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_FILE, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(GMAIL_CREDS_FILE):
                    GMAIL_AVAILABLE = False
                    return None
                flow = InstalledAppFlow.from_client_secrets_file(GMAIL_CREDS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(GMAIL_TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        _gmail_service = build("gmail", "v1", credentials=creds)
        GMAIL_AVAILABLE = True
        return _gmail_service
    except Exception as e:
        GMAIL_AVAILABLE = False
        log(f"  Gmail API init failed: {e}")
        return None


def gmail_read(count: int = 5, query: str = "is:unread") -> str:
    svc = _get_gmail()
    if svc is None:
        return ("Gmail API not configured. Place gmail_credentials.json in "
                f"{JARVIS_HOME} (download from Google Cloud Console -> APIs & Services "
                "-> Credentials -> Create OAuth client ID -> Desktop app).")
    try:
        res = svc.users().messages().list(userId="me", q=query, maxResults=count).execute()
        msgs = res.get("messages", [])
        if not msgs:
            return f"No messages match '{query}'."
        lines = []
        for i, m in enumerate(msgs, 1):
            full = svc.users().messages().get(
                userId="me", id=m["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"]).execute()
            headers = {h["name"]: h["value"] for h in full["payload"].get("headers", [])}
            sender = headers.get("From", "Unknown")[:60]
            subject = headers.get("Subject", "(no subject)")[:80]
            snippet = full.get("snippet", "")[:120]
            lines.append(f"{i}. {sender}\n   {subject}\n   {snippet}")
        return "\n\n".join(lines)
    except Exception as e:
        return f"Gmail read error: {e}"


def gmail_send(to: str, subject: str, body: str) -> str:
    svc = _get_gmail()
    if svc is None:
        return "Gmail API not configured."
    try:
        from email.mime.text import MIMEText
        msg = MIMEText(body)
        msg["to"] = to
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        svc.users().messages().send(userId="me", body={"raw": raw}).execute()
        return f"Email sent to {to}."
    except Exception as e:
        return f"Gmail send error: {e}"

# ═══════════════════════════════════════════════════════════════
#  BROWSER (browser-use for non-Gmail tasks)
# ═══════════════════════════════════════════════════════════════
_browser_loop = asyncio.new_event_loop()
threading.Thread(target=_browser_loop.run_forever, daemon=True, name="BrowserLoop").start()
_bu_browser = None
_bu_llm     = None
_bu_loaded  = False


def _try_load_browser_use():
    global BROWSER_USE_AVAILABLE, _bu_loaded
    if _bu_loaded:
        return BROWSER_USE_AVAILABLE
    _bu_loaded = True
    try:
        import browser_use   # noqa
        import langchain_groq  # noqa
        BROWSER_USE_AVAILABLE = True
    except ImportError:
        BROWSER_USE_AVAILABLE = False
    return BROWSER_USE_AVAILABLE


async def _get_bu_browser():
    global _bu_browser, _bu_llm
    if _bu_browser is not None:
        return _bu_browser, _bu_llm
    if not _try_load_browser_use():
        return None, None
    try:
        from browser_use import Browser, BrowserConfig
        from langchain_groq import ChatGroq
        os.makedirs(BROWSER_DATA_DIR, exist_ok=True)
        cfg = BrowserConfig(
            headless=False,
            extra_chromium_args=[f"--user-data-dir={BROWSER_DATA_DIR}",
                                 "--start-maximized", "--no-sandbox"],
        )
        _bu_browser = Browser(config=cfg)
        _bu_llm = ChatGroq(model=BRAIN_MODEL, groq_api_key=GROQ_API_KEY, temperature=0)
        return _bu_browser, _bu_llm
    except Exception as e:
        log(f"  browser-use init failed: {e}")
        return None, None


def _run_browser(coro, timeout=240):
    future = asyncio.run_coroutine_threadsafe(coro, _browser_loop)
    try:
        return future.result(timeout=timeout)
    except Exception as e:
        return f"Browser task failed: {e}"


async def _browser_use_task(task: str, max_steps: int = 20):
    browser, llm = await _get_bu_browser()
    if browser is None:
        return "browser-use not available."
    try:
        from browser_use import Agent
        agent = Agent(task=task, llm=llm, browser=browser, max_failures=3)
        result = await agent.run(max_steps=max_steps)
        try:
            final = result.final_result()
            if final:
                return str(final)[:600]
        except Exception:
            pass
        return "Done."
    except Exception as e:
        return f"Browser task error: {str(e)[:300]}"


def browser_task(task: str) -> str:
    return _run_browser(_browser_use_task(task), timeout=300)


def send_whatsapp(contact: str, message: str) -> str:
    return browser_task(
        f"Open https://web.whatsapp.com. Wait for the chat list to load (the user is "
        f"already logged in via the persistent profile). If a QR code is shown, wait up "
        f"to 60 seconds for scan. Use the search box at the top-left to find '{contact}'. "
        f"Click the first matching chat. Type the message: \"{message}\". Press Enter to "
        f"send. Confirm the message appears in the conversation.")

# ═══════════════════════════════════════════════════════════════
#  WEATHER / NEWS / YOUTUBE
# ═══════════════════════════════════════════════════════════════
def get_youtube_url(query):
    try:
        url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=8).read().decode("utf-8")
        ids = re.findall(r"watch\?v=([a-zA-Z0-9_-]{11})", html)
        if ids:
            return f"https://www.youtube.com/watch?v={ids[0]}"
    except Exception:
        pass
    return f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"


def get_weather(city="Greater Noida"):
    try:
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=%C,+%t,+humidity+%h,+wind+%w"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.0"})
        return f"Weather in {city}: " + urllib.request.urlopen(req, timeout=5).read().decode().strip()
    except Exception:
        return f"Weather unavailable for {city}."


def get_news(topic="general"):
    try:
        if topic == "general" or not topic:
            url = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"
        else:
            url = f"https://news.google.com/rss/search?q={urllib.parse.quote(topic)}&hl=en-IN&gl=IN"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        xml = urllib.request.urlopen(req, timeout=5).read().decode("utf-8")
        titles = re.findall(r"<title>(.*?)</title>", xml)[2:6]
        if titles:
            return "Top headlines: " + ". ".join(f"{i+1}, {t}" for i, t in enumerate(titles))
        return "No headlines."
    except Exception:
        return "News unavailable."

# ═══════════════════════════════════════════════════════════════
#  SYSTEM CONTROL (volume, media, lock, sleep, shutdown)
# ═══════════════════════════════════════════════════════════════
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP   = 0xAF
VK_MEDIA_NEXT  = 0xB0
VK_MEDIA_PREV  = 0xB1
VK_MEDIA_PP    = 0xB3
KEYEVENTF_EXT  = 0x0001
KEYEVENTF_UP   = 0x0002


def press_key(vk):
    ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_EXT, 0)
    ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_EXT | KEYEVENTF_UP, 0)


def system_control(action):
    a = action.lower().replace(" ", "_")
    if "volume_up" in a or "louder" in a:
        for _ in range(5): press_key(VK_VOLUME_UP)
        return "Volume raised."
    if "volume_down" in a or "quieter" in a or "lower" in a:
        for _ in range(5): press_key(VK_VOLUME_DOWN)
        return "Volume lowered."
    if "mute" in a:
        press_key(VK_VOLUME_MUTE); return "Mute toggled."
    if "pause" in a or "play" in a or "resume" in a:
        press_key(VK_MEDIA_PP); return "Done."
    if "next" in a or "skip" in a:
        press_key(VK_MEDIA_NEXT); return "Skipping."
    if "prev" in a or "previous" in a:
        press_key(VK_MEDIA_PREV); return "Previous track."
    if "lock" in a:
        ctypes.windll.user32.LockWorkStation(); return "Workstation locked."
    if "shutdown" in a:
        speak("Shutting down in 10 seconds, sir.")
        time.sleep(10); subprocess.run(["shutdown", "/s", "/t", "0"]); return ""
    if "restart" in a or "reboot" in a:
        speak("Restarting in 10 seconds, sir.")
        time.sleep(10); subprocess.run(["shutdown", "/r", "/t", "0"]); return ""
    if "sleep" in a:
        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"])
        return "Sleeping."
    return f"Unknown control: {action}."


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_byte), ("BatteryFlag", ctypes.c_byte),
        ("BatteryLifePercent", ctypes.c_byte), ("SystemStatusFlag", ctypes.c_byte),
        ("BatteryLifeTime", ctypes.c_ulong), ("BatteryFullLifeTime", ctypes.c_ulong),
    ]


def get_battery():
    try:
        s = SYSTEM_POWER_STATUS()
        ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s))
        if s.BatteryLifePercent <= 100:
            return s.BatteryLifePercent, "charging" if s.ACLineStatus == 1 else "on battery"
    except Exception:
        pass
    return None, None


def system_status_summary():
    parts = []
    pct, state = get_battery()
    if pct is not None:
        parts.append(f"Battery {pct}% ({state})")
    try:
        free = ctypes.c_ulonglong()
        ctypes.windll.kernel32.GetDiskFreeSpaceExW("C:\\", None, None, ctypes.byref(free))
        parts.append(f"C: {free.value / (1024 ** 3):.1f} GB free")
    except Exception:
        pass
    if PSUTIL_AVAILABLE:
        try:
            parts.append(f"CPU {psutil.cpu_percent(interval=0.3):.0f}%")
            parts.append(f"RAM {psutil.virtual_memory().percent:.0f}%")
        except Exception:
            pass
    return ". ".join(parts) + "." if parts else "All nominal."

# ═══════════════════════════════════════════════════════════════
#  SCHEDULED TASKS
# ═══════════════════════════════════════════════════════════════
scheduled_tasks = []
task_lock = threading.Lock()


def schedule_task(run_at, description, action_fn):
    with task_lock:
        scheduled_tasks.append({"run_at": run_at, "desc": description,
                                "action": action_fn, "done": False})


def scheduler_loop():
    while not shutdown_event.is_set():
        now = datetime.now()
        with task_lock:
            for t in scheduled_tasks:
                if not t["done"] and now >= t["run_at"]:
                    t["done"] = True
                    try:
                        t["action"]()
                        speak(f"Scheduled: {t['desc']}, sir.")
                    except Exception as e:
                        log(f"  [SCHEDULER] {e}")
        shutdown_event.wait(30)


def parse_schedule(text):
    at = re.search(r"at\s+(\d{1,2})[:\s](\d{2})\s*(a\.?m\.?|p\.?m\.?)\s+(.*)", text, re.IGNORECASE)
    if at:
        h = int(at.group(1)); m = int(at.group(2))
        ap = re.sub(r"\.", "", at.group(3)).lower()
        cmd = at.group(4).strip()
        if ap == "pm" and h != 12: h += 12
        if ap == "am" and h == 12: h = 0
        run_at = datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
        if run_at <= datetime.now(): run_at += timedelta(days=1)
        schedule_task(run_at, cmd, lambda c=cmd: react_loop(c, speak_progress=False))
        return f"Scheduled: '{cmd}' at {run_at.strftime('%I:%M %p')}."
    inn = re.search(r"in\s+(\d+)\s*(min|minute|minutes|hour|hours|hr)\s+(.*)", text, re.IGNORECASE)
    if inn:
        amt = int(inn.group(1)); unit = inn.group(2).lower(); cmd = inn.group(3).strip()
        delta = timedelta(hours=amt) if "h" in unit else timedelta(minutes=amt)
        run_at = datetime.now() + delta
        schedule_task(run_at, cmd, lambda c=cmd: react_loop(c, speak_progress=False))
        return f"Scheduled in {amt} {unit}."
    return None


def get_pending_tasks():
    with task_lock:
        active = [t for t in scheduled_tasks if not t["done"]]
    if not active: return "No pending tasks."
    return "Pending: " + ". ".join(f"{t['desc']} at {t['run_at'].strftime('%I:%M %p')}" for t in active)


def generate_briefing():
    now = datetime.now()
    return (f"It is {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d')}. "
            f"{get_weather()} {system_status_summary()} {get_pending_tasks()}")

# ═══════════════════════════════════════════════════════════════
#  AMBIENT WATCHER (clipboard stack-trace detection)
# ═══════════════════════════════════════════════════════════════
_last_clipboard = ""


def clipboard_watcher():
    """Watch the clipboard. If a Python/JS stack trace appears, offer to analyze."""
    global _last_clipboard
    if not PYPERCLIP_AVAILABLE:
        return
    while not shutdown_event.is_set():
        try:
            current = pyperclip.paste()
            if current and current != _last_clipboard and len(current) > 60:
                _last_clipboard = current
                lower = current.lower()
                stack_trace_signals = [
                    "traceback (most recent call",
                    "error:",
                    "exception:",
                    "stacktrace",
                    "at object.",
                    "syntaxerror",
                    "typeerror",
                ]
                if any(sig in lower for sig in stack_trace_signals):
                    hud_event("clipboard_signal",
                              preview=current[:120], length=len(current))
                    # Don't speak — too intrusive. HUD shows the signal.
        except Exception:
            pass
        shutdown_event.wait(3)


def proactive_monitor():
    while not shutdown_event.is_set():
        try:
            now = datetime.now(); hour = now.hour
            if 2 <= hour < 5:
                key = f"late_night_{now.date()}"
                if key not in proactive_spoken:
                    proactive_spoken.add(key)
                    speak("Sir, it's past 2 AM. The code will still be here in the morning.")
            pct, state = get_battery()
            if pct is not None and pct <= 15 and state == "on battery":
                key = f"low_battery_{pct // 5}"
                if key not in proactive_spoken:
                    proactive_spoken.add(key)
                    speak(f"Battery critically low at {pct}%, sir. Plug in.")
        except Exception:
            pass
        shutdown_event.wait(300)

# ═══════════════════════════════════════════════════════════════
#  SELF-EXTENSION (write_tool, reload_tools)
# ═══════════════════════════════════════════════════════════════
DYNAMIC_TOOLS_HEADER = '''"""
JARVIS dynamic tools — written by JARVIS itself at runtime.
Each function becomes a callable tool. Add a docstring describing it.
"""
import os, subprocess, urllib.request, urllib.parse, json, re, time

'''

_dynamic_module = None
_dynamic_specs  = []


def _ensure_dynamic_file():
    if not os.path.exists(DYNAMIC_TOOLS_FILE):
        with open(DYNAMIC_TOOLS_FILE, "w", encoding="utf-8") as f:
            f.write(DYNAMIC_TOOLS_HEADER)


def reload_dynamic_tools() -> str:
    """Re-import dynamic_tools.py and refresh the TOOLS list."""
    global _dynamic_module, _dynamic_specs
    _ensure_dynamic_file()
    try:
        spec = importlib.util.spec_from_file_location("jarvis_dynamic_tools", DYNAMIC_TOOLS_FILE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _dynamic_module = mod
        _dynamic_specs = []
        for name, fn in inspect.getmembers(mod, inspect.isfunction):
            if name.startswith("_"): continue
            sig = inspect.signature(fn)
            props = {}
            required = []
            for pname, param in sig.parameters.items():
                props[pname] = {"type": "string", "description": pname}
                if param.default is inspect.Parameter.empty:
                    required.append(pname)
            _dynamic_specs.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": (fn.__doc__ or f"Dynamic tool: {name}").strip()[:200],
                    "parameters": {"type": "object", "properties": props, "required": required},
                },
            })
        log(f"  Dynamic tools loaded: {len(_dynamic_specs)}")
        return f"Loaded {len(_dynamic_specs)} dynamic tools."
    except Exception as e:
        return f"Reload failed: {e}"


def write_tool(name: str, description: str, code: str) -> str:
    """Append a new Python function to dynamic_tools.py and reload.
       'code' must be a complete `def name(...)` body."""
    _ensure_dynamic_file()
    if not re.match(r"^[a-z][a-z0-9_]*$", name):
        return "Invalid name. Use lowercase_with_underscores."
    try:
        # Check syntax before saving
        compile(code, "<tool>", "exec")
    except SyntaxError as e:
        return f"Syntax error in tool code: {e}"
    block = f'\n\n# {description}\n{code}\n'
    with open(DYNAMIC_TOOLS_FILE, "a", encoding="utf-8") as f:
        f.write(block)
    return reload_dynamic_tools()


def call_dynamic_tool(name: str, args: dict) -> str:
    if _dynamic_module is None:
        reload_dynamic_tools()
    if _dynamic_module is None:
        return "Dynamic module not loaded."
    fn = getattr(_dynamic_module, name, None)
    if fn is None:
        return f"Dynamic tool '{name}' not found."
    try:
        result = fn(**args)
        return str(result)[:3000] if result is not None else "Done."
    except Exception as e:
        return f"Dynamic tool '{name}' raised: {e}"

# ═══════════════════════════════════════════════════════════════
#  CONFIRMATION (plan-confirm-execute for dangerous actions)
# ═══════════════════════════════════════════════════════════════
def confirm_with_user(plan: str) -> str:
    """Speak the plan and wait for a yes/no spoken response."""
    speak(f"Plan: {plan}. Shall I proceed, sir? Say yes or no.")
    answer = listen_for_command()
    if not answer:
        return "No response — aborting."
    answer_l = answer.lower()
    if any(w in answer_l for w in ["yes", "yeah", "yep", "go", "do it", "proceed", "sure", "okay", "ok"]):
        return "APPROVED"
    return f"DENIED ({answer})"

# ═══════════════════════════════════════════════════════════════
#  TOOLS REGISTRY
# ═══════════════════════════════════════════════════════════════
TOOLS = [
    # ─── Generalist primitives ───
    {"type": "function", "function": {
        "name": "run_shell",
        "description": ("Execute a PowerShell or cmd command on Windows and return its output. "
                        "Use this for ANYTHING not covered by other tools — installing packages, "
                        "starting servers, querying processes, git operations, file ops, anything. "
                        "Default shell is powershell."),
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string", "description": "Full command to run"},
            "shell": {"type": "string", "description": "powershell | cmd (default powershell)"},
        }, "required": ["command"]}}},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read the contents of a text file. Truncates at 4000 chars.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "write_file",
        "description": ("Write text to a file. Creates parent dirs. Set append=true to append. "
                        "MUST call confirm_with_user first if overwriting an existing important file."),
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "content": {"type": "string"},
            "append": {"type": "boolean"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {
        "name": "list_dir",
        "description": "List contents of a directory.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "find_files",
        "description": "Recursively find files matching a glob pattern under a root.",
        "parameters": {"type": "object", "properties": {
            "pattern": {"type": "string", "description": "e.g. '*.py' or 'config*.json'"},
            "root":    {"type": "string", "description": "Root dir, default C:/Users/Dev"}},
            "required": ["pattern"]}}},
    # ─── App / settings ───
    {"type": "function", "function": {
        "name": "open_app",
        "description": ("Open a known app, an .exe path, a folder, a file, or a URI. "
                        "Pass extra args after the path if needed (e.g. cursor + a folder path)."),
        "parameters": {"type": "object", "properties": {
            "name_or_path": {"type": "string"},
            "args": {"type": "string", "description": "Extra CLI args"}},
            "required": ["name_or_path"]}}},
    {"type": "function", "function": {
        "name": "open_settings",
        "description": ("Open a Windows Settings panel. Examples: bluetooth, wifi, display, "
                        "sound, notifications, battery, vpn, mouse, keyboard, accessibility, "
                        "windows update, privacy, defender, taskbar, themes, language."),
        "parameters": {"type": "object", "properties": {"panel": {"type": "string"}},
                       "required": ["panel"]}}},
    {"type": "function", "function": {
        "name": "open_website",
        "description": "Open a website by friendly name or URL.",
        "parameters": {"type": "object", "properties": {"site": {"type": "string"}},
                       "required": ["site"]}}},
    # ─── Window / keyboard ───
    {"type": "function", "function": {
        "name": "list_windows",
        "description": "List visible top-level windows on the desktop.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "focus_window",
        "description": "Bring a window to the foreground by partial title match.",
        "parameters": {"type": "object", "properties": {"title": {"type": "string"}},
                       "required": ["title"]}}},
    {"type": "function", "function": {
        "name": "send_keys",
        "description": ("Send keystrokes to the active window using PowerShell SendKeys syntax. "
                        "Examples: '^c'=Ctrl+C, '^s'=Ctrl+S, '{ENTER}', '%{F4}'=Alt+F4, plain text."),
        "parameters": {"type": "object", "properties": {"keys": {"type": "string"}},
                       "required": ["keys"]}}},
    # ─── Clipboard ───
    {"type": "function", "function": {
        "name": "clipboard_read",
        "description": "Return current clipboard text.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "clipboard_write",
        "description": "Set the clipboard contents.",
        "parameters": {"type": "object", "properties": {"text": {"type": "string"}},
                       "required": ["text"]}}},
    # ─── Process / network ───
    {"type": "function", "function": {
        "name": "list_processes",
        "description": "List running processes, optionally filtered by name substring.",
        "parameters": {"type": "object", "properties": {"filter": {"type": "string"}},
                       "required": []}}},
    {"type": "function", "function": {
        "name": "kill_process",
        "description": "Kill a process by name or PID. Use confirm_with_user first for risky kills.",
        "parameters": {"type": "object", "properties": {"name_or_pid": {"type": "string"}},
                       "required": ["name_or_pid"]}}},
    {"type": "function", "function": {
        "name": "http_get",
        "description": "Fetch a URL and return the response body (truncated). Use to check local servers (e.g. n8n, ollama).",
        "parameters": {"type": "object", "properties": {"url": {"type": "string"}},
                       "required": ["url"]}}},
    # ─── Vision ───
    {"type": "function", "function": {
        "name": "take_screenshot",
        "description": "Capture the screen and save it to disk.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "analyze_screen",
        "description": ("Look at Mr. Stark's screen and answer a question. Use for 'what do you see', "
                        "'read this', 'analyze this', 'when does X reset', 'what's wrong here'."),
        "parameters": {"type": "object", "properties": {"question": {"type": "string"}},
                       "required": ["question"]}}},
    # ─── Email / messaging ───
    {"type": "function", "function": {
        "name": "gmail_read",
        "description": ("Read inbox messages via the Gmail API. Fast, reliable. "
                        "Default query 'is:unread' returns unread mail. "
                        "Other queries: 'from:boss', 'is:starred', 'subject:invoice'."),
        "parameters": {"type": "object", "properties": {
            "count": {"type": "integer", "description": "How many messages (default 5)"},
            "query": {"type": "string", "description": "Gmail search query"}},
            "required": []}}},
    {"type": "function", "function": {
        "name": "gmail_send",
        "description": "Send an email via Gmail API.",
        "parameters": {"type": "object", "properties": {
            "to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}},
            "required": ["to", "subject", "body"]}}},
    {"type": "function", "function": {
        "name": "send_whatsapp",
        "description": "Send a WhatsApp message via WhatsApp Web (browser-use AI navigation).",
        "parameters": {"type": "object", "properties": {
            "contact": {"type": "string"}, "message": {"type": "string"}},
            "required": ["contact", "message"]}}},
    {"type": "function", "function": {
        "name": "browser_action",
        "description": ("Run an arbitrary multi-step task in the browser via browser-use AI. "
                        "Use when no API/tool fits and you need to navigate a website."),
        "parameters": {"type": "object", "properties": {"task": {"type": "string"}},
                       "required": ["task"]}}},
    # ─── Information ───
    {"type": "function", "function": {
        "name": "get_time",
        "description": "Current local time.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "get_date",
        "description": "Today's date and weekday.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "get_weather",
        "description": "Weather for a city (default Greater Noida).",
        "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "get_news",
        "description": "Top news headlines on a topic, or general.",
        "parameters": {"type": "object", "properties": {"topic": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "system_status",
        "description": "Battery, CPU, RAM, disk summary.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "system_control",
        "description": "Volume, media, lock, sleep, restart, shutdown.",
        "parameters": {"type": "object", "properties": {"action": {"type": "string"}},
                       "required": ["action"]}}},
    {"type": "function", "function": {
        "name": "briefing",
        "description": "Full status briefing — time, weather, system, tasks.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "schedule_command",
        "description": "Schedule a future request. Pass full text including timing.",
        "parameters": {"type": "object", "properties": {"text": {"type": "string"}},
                       "required": ["text"]}}},
    # ─── Memory / self-extension / safety ───
    {"type": "function", "function": {
        "name": "remember_fact",
        "description": "Store a long-term fact about Mr. Stark.",
        "parameters": {"type": "object", "properties": {"fact": {"type": "string"}},
                       "required": ["fact"]}}},
    {"type": "function", "function": {
        "name": "write_tool",
        "description": ("Define a brand-new tool at runtime by writing a Python function. "
                        "Use this when Mr. Stark asks for a capability you don't yet have. "
                        "The function's docstring becomes the tool description; parameters become args."),
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "description": "snake_case function name"},
            "description": {"type": "string", "description": "What the tool does"},
            "code": {"type": "string", "description": "Complete `def name(args): ...` Python source"}},
            "required": ["name", "description", "code"]}}},
    {"type": "function", "function": {
        "name": "reload_tools",
        "description": "Re-scan dynamic_tools.py and refresh dynamic tools list.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "confirm_with_user",
        "description": ("Speak a plan to Mr. Stark and wait for spoken yes/no. "
                        "MUST be called before any destructive action (delete files, format, "
                        "shutdown, force-push, mass kill). Returns 'APPROVED' or 'DENIED ...'."),
        "parameters": {"type": "object", "properties": {"plan": {"type": "string"}},
                       "required": ["plan"]}}},
]

# ═══════════════════════════════════════════════════════════════
#  TOOL DISPATCH
# ═══════════════════════════════════════════════════════════════
def _t_run_shell(a):
    cmd = a.get("command", "")
    if is_dangerous(cmd):
        return ("REFUSED: dangerous pattern detected. Call confirm_with_user first, then "
                "re-issue this run_shell call only after APPROVAL.")
    return run_shell(cmd, a.get("shell", "powershell"))


def _t_read_file(a):     return read_file(a.get("path", ""))
def _t_write_file(a):
    p = a.get("path", "")
    if os.path.exists(p) and not a.get("append"):
        # Auto-confirm overwrite for files inside JARVIS_HOME / dynamic tools
        if not (os.path.abspath(p).startswith(os.path.abspath(JARVIS_HOME))):
            return ("REFUSED overwrite of existing file outside JARVIS_HOME. "
                    "Call confirm_with_user first.")
    return write_file(p, a.get("content", ""), bool(a.get("append")))


def _t_list_dir(a):      return list_dir(a.get("path", "."))
def _t_find_files(a):    return find_files(a.get("pattern", ""), a.get("root", "C:/Users/Dev"))


def _t_open_app(a):
    return open_app_or_path(a.get("name_or_path", ""), a.get("args", ""))


def _t_open_settings(a): return open_settings(a.get("panel", ""))


def _t_open_website(a):
    site = (a.get("site") or "").strip().lower()
    for n, u in WEBSITES.items():
        if n in site or site in n:
            webbrowser.open(u); return f"Opened {n}."
    if "://" in site: webbrowser.open(site); return f"Opened {site}."
    webbrowser.open(f"https://{site}"); return f"Opened {site}."


def _t_list_windows(a):  return list_windows()
def _t_focus_window(a):  return focus_window(a.get("title", ""))
def _t_send_keys(a):     return send_keys(a.get("keys", ""))
def _t_clipboard_read(a):  return clipboard_read()
def _t_clipboard_write(a): return clipboard_write(a.get("text", ""))
def _t_list_processes(a):  return list_processes(a.get("filter", ""))
def _t_kill_process(a):    return kill_process(a.get("name_or_pid", ""))
def _t_http_get(a):        return http_get(a.get("url", ""))
def _t_take_screenshot(a): return take_screenshot()
def _t_analyze_screen(a):  return analyze_screen(a.get("question") or "What's on the screen?")
def _t_gmail_read(a):      return gmail_read(int(a.get("count", 5)), a.get("query", "is:unread"))
def _t_gmail_send(a):      return gmail_send(a.get("to", ""), a.get("subject", ""), a.get("body", ""))


def _t_send_whatsapp(a):
    return send_whatsapp(a.get("contact", ""), a.get("message", ""))


def _t_browser_action(a):  return browser_task(a.get("task", ""))
def _t_get_time(a):        return f"It is {datetime.now().strftime('%I:%M %p')}."
def _t_get_date(a):        return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}."
def _t_get_weather(a):     return get_weather(a.get("city") or "Greater Noida")
def _t_get_news(a):        return get_news(a.get("topic") or "general")
def _t_system_status(a):   return system_status_summary()
def _t_system_control(a):  return system_control(a.get("action", ""))
def _t_briefing(a):        return generate_briefing()
def _t_schedule_command(a): return parse_schedule(a.get("text", "").lower()) or "Couldn't parse timing."


def _t_remember(a):
    f = a.get("fact", "")
    if not f: return "No fact."
    remember(f); return "Stored."


def _t_write_tool(a):
    return write_tool(a.get("name", ""), a.get("description", ""), a.get("code", ""))


def _t_reload_tools(a):    return reload_dynamic_tools()
def _t_confirm(a):         return confirm_with_user(a.get("plan", ""))


TOOL_DISPATCH = {
    "run_shell": _t_run_shell, "read_file": _t_read_file, "write_file": _t_write_file,
    "list_dir": _t_list_dir, "find_files": _t_find_files,
    "open_app": _t_open_app, "open_settings": _t_open_settings, "open_website": _t_open_website,
    "list_windows": _t_list_windows, "focus_window": _t_focus_window, "send_keys": _t_send_keys,
    "clipboard_read": _t_clipboard_read, "clipboard_write": _t_clipboard_write,
    "list_processes": _t_list_processes, "kill_process": _t_kill_process, "http_get": _t_http_get,
    "take_screenshot": _t_take_screenshot, "analyze_screen": _t_analyze_screen,
    "gmail_read": _t_gmail_read, "gmail_send": _t_gmail_send,
    "send_whatsapp": _t_send_whatsapp, "browser_action": _t_browser_action,
    "get_time": _t_get_time, "get_date": _t_get_date, "get_weather": _t_get_weather,
    "get_news": _t_get_news, "system_status": _t_system_status, "system_control": _t_system_control,
    "briefing": _t_briefing, "schedule_command": _t_schedule_command,
    "remember_fact": _t_remember,
    "write_tool": _t_write_tool, "reload_tools": _t_reload_tools,
    "confirm_with_user": _t_confirm,
}


def dispatch_tool(name, args):
    fn = TOOL_DISPATCH.get(name)
    if fn:
        try:
            return str(fn(args or {}))
        except Exception as e:
            return f"Tool '{name}' raised: {e}"
    # Try dynamic tools
    return call_dynamic_tool(name, args or {})

# ═══════════════════════════════════════════════════════════════
#  REACT LOOP
# ═══════════════════════════════════════════════════════════════
_LONG_TOOLS = {"send_whatsapp", "browser_action", "analyze_screen", "gmail_read"}


def _all_tools():
    return TOOLS + _dynamic_specs


def react_loop(user_input, speak_progress=True, max_iter=REACT_MAX_ITER):
    set_status("thinking")
    hud_event("user_said", text=user_input)
    session_memory.append({"role": "user", "content": user_input})

    mem_context = recall(user_input)
    system = SYSTEM_PROMPT
    if mem_context:
        system += f"\n\nLONG-TERM MEMORIES:\n{mem_context}"

    messages = [{"role": "system", "content": system}] + session_memory[-20:]

    final_text = None
    for step in range(max_iter):
        try:
            resp = client.chat.completions.create(
                model=BRAIN_MODEL, messages=messages,
                tools=_all_tools(), tool_choice="auto", temperature=0.4,
            )
        except Exception as e:
            log(f"  [Brain error: {e}]")
            final_text = f"Reasoning hiccuped, sir: {str(e)[:120]}"
            break

        msg = resp.choices[0].message
        tool_calls = msg.tool_calls or []

        if not tool_calls:
            final_text = (msg.content or "").strip()
            break

        messages.append({
            "role": "assistant", "content": msg.content or "",
            "tool_calls": [{"id": tc.id, "type": "function",
                            "function": {"name": tc.function.name,
                                         "arguments": tc.function.arguments or "{}"}}
                           for tc in tool_calls]})

        for tc in tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            log(f"  -> {name}({json.dumps(args)[:120]})")
            hud_event("tool_call", name=name, args=args, step=step+1)
            set_status("working")

            if speak_progress and name in _LONG_TOOLS and step < max_iter - 1:
                phrases = {"send_whatsapp": "Sending WhatsApp now, sir.",
                           "gmail_read": "Checking inbox.",
                           "analyze_screen": "Looking at your screen.",
                           "browser_action": "Working in the browser."}
                if name in phrases:
                    speak(phrases[name])

            result = dispatch_tool(name, args)
            log(f"     = {str(result)[:200]}")
            hud_event("tool_result", name=name, result=str(result)[:300])

            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "name": name, "content": str(result)[:3000]})
        set_status("thinking")
    else:
        final_text = "Reached my action limit, sir. Want me to keep going?"

    if final_text is None:
        final_text = "Done."
    session_memory.append({"role": "assistant", "content": final_text})
    threading.Thread(target=remember,
                     args=(f"Mr. Stark said: {user_input}",), daemon=True).start()
    set_status("idle")
    return final_text

# ═══════════════════════════════════════════════════════════════
#  GREETING
# ═══════════════════════════════════════════════════════════════
def greet():
    h = datetime.now().hour
    period = "Good morning" if h < 12 else "Good afternoon" if h < 17 else "Good evening"
    pct, _ = get_battery()
    bat = f" Battery at {pct}%." if pct and pct <= 100 else ""
    return f"{period}, Mr. Stark. All systems are online.{bat} Say my name when you need me."

# ═══════════════════════════════════════════════════════════════
#  TRAY
# ═══════════════════════════════════════════════════════════════
_STATE_COLOURS = {
    "idle": (60, 60, 70), "listening": (40, 200, 80), "thinking": (255, 180, 0),
    "speaking": (60, 140, 255), "working": (200, 80, 220),
}


def make_tray_image(state="idle"):
    if not PIL_AVAILABLE: return None
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = _STATE_COLOURS.get(state, (60, 60, 70))
    d.ellipse((4, 4, 60, 60), fill=c, outline=(255, 255, 255, 220), width=2)
    d.ellipse((22, 22, 42, 42), fill=(255, 255, 255, 230))
    return img


def _tray_show_log(_=None, __=None):
    def _show():
        try:
            import tkinter as tk
            win = tk.Tk(); win.title("JARVIS — Activity"); win.geometry("760x460")
            win.configure(bg="#1a1a1f")
            txt = tk.Text(win, bg="#1a1a1f", fg="#d8d8e0", insertbackground="#d8d8e0",
                          font=("Consolas", 9), wrap="word", borderwidth=0)
            txt.pack(fill="both", expand=True, padx=8, pady=8)
            txt.insert("1.0", "\n".join(LOG_BUFFER)); txt.see("end")
            txt.configure(state="disabled"); win.mainloop()
        except Exception as e:
            log(f"  [Log window: {e}]")
    threading.Thread(target=_show, daemon=True).start()


def _tray_status(_=None, __=None): speak(f"Status: {TRAY_STATE}, sir.")


def _tray_restart(_=None, __=None):
    log("  [Tray] Restart"); shutdown_event.set()
    try: tray_icon and tray_icon.stop()
    except Exception: pass
    subprocess.Popen([sys.executable, os.path.abspath(__file__)], creationflags=0x00000008)
    os._exit(0)


def _tray_shutdown(_=None, __=None):
    log("  [Tray] Shutdown")
    try: speak("Powering down, sir.")
    except Exception: pass
    shutdown_event.set()
    try: tray_icon and tray_icon.stop()
    except Exception: pass
    if hud_process:
        try: hud_process.terminate()
        except Exception: pass
    os._exit(0)


def _tray_show_hud(_=None, __=None):
    launch_hud()


def run_tray():
    global tray_icon
    if not (PYSTRAY_AVAILABLE and PIL_AVAILABLE):
        log("  [Tray] missing deps — headless"); return
    menu = pystray.Menu(
        pystray.MenuItem("Open HUD", _tray_show_hud, default=True),
        pystray.MenuItem("Status", _tray_status),
        pystray.MenuItem("Activity Log", _tray_show_log),
        pystray.MenuItem("Restart JARVIS", _tray_restart),
        pystray.MenuItem("Shutdown JARVIS", _tray_shutdown),
    )
    tray_icon = pystray.Icon("JARVIS", icon=make_tray_image("idle"),
                             title="JARVIS — idle", menu=menu)
    tray_icon.run()

# ═══════════════════════════════════════════════════════════════
#  HUD LAUNCHER (PyQt6 floating overlay — runs in separate process)
# ═══════════════════════════════════════════════════════════════
def launch_hud():
    """Spawn the HUD as a separate Python process so it has its own Qt event loop."""
    global hud_process
    if hud_process and hud_process.poll() is None:
        return  # already running
    hud_path = os.path.join(JARVIS_HOME, "hud.py")
    if not os.path.exists(hud_path):
        log("  [HUD] hud.py not found.")
        return
    try:
        # Reset events file so HUD starts fresh
        try:
            with open(HUD_EVENTS_FILE, "w") as f:
                f.write("")
        except Exception:
            pass
        hud_process = subprocess.Popen(
            [sys.executable, hud_path],
            creationflags=subprocess.DETACHED_PROCESS if hasattr(subprocess, "DETACHED_PROCESS") else 0,
        )
        log("  HUD launched.")
    except Exception as e:
        log(f"  [HUD launch failed: {e}]")

# ═══════════════════════════════════════════════════════════════
#  MAIN VOICE LOOP
# ═══════════════════════════════════════════════════════════════
def voice_loop():
    log("")
    log("  ╔════════════════════════════════════════════════╗")
    log("  ║  JARVIS — Phase 5: The Generalist             ║")
    log("  ║  Shell · FS · Windows · Vision · HUD · Self-Ext║")
    log("  ╚════════════════════════════════════════════════╝")
    log("")

    init_speech()
    threading.Thread(target=init_memory, daemon=True).start()
    reload_dynamic_tools()

    threading.Thread(target=lambda: [
        remember("Mr. Stark lives in Greater Noida, India"),
        remember("Mr. Stark is building JARVIS, a personal AI assistant"),
        remember("Mr. Stark uses Python 3.11, Groq, Cursor, Claude Code"),
        remember("Mr. Stark wants Iron-Man-grade autonomy from JARVIS"),
    ], daemon=True).start()

    threading.Thread(target=scheduler_loop, daemon=True).start()
    threading.Thread(target=proactive_monitor, daemon=True).start()
    threading.Thread(target=clipboard_watcher, daemon=True).start()

    log(f"  Tools registered: {len(TOOLS)} static + {len(_dynamic_specs)} dynamic")
    log(f"  Vision: {'ON' if PIL_AVAILABLE else 'OFF'}")
    log(f"  Tray:   {'ON' if PYSTRAY_AVAILABLE else 'OFF'}")
    log(f"  Clipboard: {'ON' if PYPERCLIP_AVAILABLE else 'OFF'}")
    log(f"  Process control: {'ON' if PSUTIL_AVAILABLE else 'OFF'}")
    log(f"  Window control: {'ON' if PYGW_AVAILABLE else 'OFF'}")
    log("  All systems operational.")

    # Auto-launch HUD
    if HUD_ENABLED:
        launch_hud()

    speak(greet())

    global active_until
    while not shutdown_event.is_set():
        now = time.time()
        in_followup = now < active_until

        if in_followup:
            set_status("listening")
            text = listen_followup()
            if text is None:
                active_until = 0; set_status("idle"); continue
            command = text.strip()
            log(f"  You: {command}")
        else:
            set_status("idle")
            heard = listen_for_wake_word()
            if heard is None: continue
            if WAKE_WORD not in heard: continue
            set_status("listening")
            play_chime()
            command = heard.replace(WAKE_WORD, "").strip().strip(".,!? ")
            if len(command) < 3:
                speak("At your service, Mr. Stark.")
                command = listen_for_command()
                if not command: continue
                log(f"  You: {command}")
            else:
                log(f"  You: {command}")

        cmd_l = command.lower()
        if any(w in cmd_l for w in ["shutdown jarvis", "shut down jarvis",
                                     "power down", "exit jarvis", "goodbye jarvis"]):
            speak("Powering down. It's been a pleasure, sir.")
            shutdown_event.set()
            try: tray_icon and tray_icon.stop()
            except Exception: pass
            if hud_process:
                try: hud_process.terminate()
                except Exception: pass
            break

        response = react_loop(command, speak_progress=True)
        if response: speak(response)
        active_until = time.time() + FOLLOWUP_WINDOW


def main():
    if TRAY_MODE and PYSTRAY_AVAILABLE and PIL_AVAILABLE:
        install_silent_stdout()
        threading.Thread(target=voice_loop, daemon=True, name="VoiceLoop").start()
        run_tray()
    else:
        voice_loop()


if __name__ == "__main__":
    main()
