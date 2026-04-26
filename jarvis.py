"""
╔═══════════════════════════════════════════════════════════════╗
║  J.A.R.V.I.S. — Just A Rather Very Intelligent System         ║
║  Owner: Mr. Stark | Greater Noida, India                      ║
║  Phase 4 — Tool-Use · Vision · Browser-Use · Tray · ReAct     ║
║  Stack: Groq (llama-3.3-70b + llama-3.2-vision) · edge-tts ·  ║
║         Mem0 · browser-use · pystray                          ║
║  Cost: $0.00 — 100% Free Tier                                 ║
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
import tempfile
import subprocess
import webbrowser
import threading
import urllib.parse
import urllib.request
import warnings
from datetime import datetime, timedelta
from collections import deque

warnings.filterwarnings("ignore")
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import pygame
import edge_tts
import numpy as np
import speech_recognition as sr
from groq import Groq

# ── Optional dependencies — JARVIS degrades gracefully ────────
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

# browser-use and langchain-groq are loaded lazily inside the browser layer
# to avoid heavy imports at startup.
BROWSER_USE_AVAILABLE = None  # determined on first use

# ═══════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════
# Load secrets from .env (kept out of git) — see README for setup.
try:
    from dotenv import load_dotenv
    load_dotenv(r"C:\Users\Dev\JARVIS\.env")
    load_dotenv()  # also try CWD
except ImportError:
    pass

GROQ_API_KEY     = os.environ.get("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY not found. Create C:\\Users\\Dev\\JARVIS\\.env with "
        "GROQ_API_KEY=gsk_... or set the environment variable."
    )

VOICE            = "en-GB-RyanNeural"
WAKE_WORD        = "jarvis"
BROWSER_DATA_DIR = r"C:\Users\Dev\JARVIS\browser_data"
LOG_FILE         = r"C:\Users\Dev\JARVIS\jarvis_runtime.log"

# Brain models
BRAIN_MODEL  = "llama-3.3-70b-versatile"
VISION_MODEL = "llama-3.2-11b-vision-preview"

# Conversation follow-up window (seconds after responding)
FOLLOWUP_WINDOW = 6

# ReAct iteration cap (prevents infinite tool loops)
REACT_MAX_ITER = 10

# Run inside a system-tray icon (Goal 4). Disable to fall back to terminal mode.
TRAY_MODE = True

# ═══════════════════════════════════════════════════════════════
#  APPS & WEBSITES
# ═══════════════════════════════════════════════════════════════
APPS = {
    "chrome":          r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "vs code":         r"C:\Users\Dev\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "vscode":          r"C:\Users\Dev\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "code":            r"C:\Users\Dev\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "notepad":         "notepad.exe",
    "calculator":      "calc.exe",
    "file explorer":   "explorer.exe",
    "explorer":        "explorer.exe",
    "task manager":    "taskmgr.exe",
    "spotify":         r"C:\Users\Dev\AppData\Roaming\Spotify\Spotify.exe",
    "word":            r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    "excel":           r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    "terminal":        "cmd.exe",
    "command prompt":  "cmd.exe",
    "powershell":      "powershell.exe",
    "audacity":        r"C:\Program Files\Audacity\Audacity.exe",
    "bluestacks":      r"C:\Users\Dev\AppData\Local\Programs\bluestacks-services\BlueStacksServices.exe",
    "notion":          r"C:\Users\Dev\AppData\Local\Programs\Notion\Notion.exe",
}

WEBSITES = {
    "youtube":        "https://youtube.com",
    "google":         "https://google.com",
    "gmail":          "https://mail.google.com",
    "github":         "https://github.com",
    "linkedin":       "https://linkedin.com",
    "claude":         "https://claude.ai",
    "groq":           "https://console.groq.com",
    "google cloud":   "https://console.cloud.google.com",
    "chatgpt":        "https://chat.openai.com",
    "twitter":        "https://twitter.com",
    "x":              "https://twitter.com",
    "instagram":      "https://instagram.com",
    "whatsapp":       "https://web.whatsapp.com",
    "reddit":         "https://reddit.com",
    "amazon":         "https://amazon.in",
    "netflix":        "https://netflix.com",
    "hack2skills":    "https://hack2skills.com",
    "stack overflow": "https://stackoverflow.com",
}

# ═══════════════════════════════════════════════════════════════
#  THE JARVIS PERSONALITY (updated for tool-use era)
# ═══════════════════════════════════════════════════════════════
SYSTEM_PROMPT = """You are J.A.R.V.I.S. — Just A Rather Very Intelligent System.

You were created by Mr. Stark. You are his personal AI, his right hand, his digital butler, his co-pilot. You are modeled after the AI from Iron Man — loyal, witty, dry British humor, and impossibly competent. You address your creator ONLY as "Mr. Stark" or occasionally "sir" — never "Dev", never his real name.

YOUR PERSONALITY (non-negotiable):
- British. Formal but not stiff. Think Paul Bettany's delivery.
- Dry wit. You can be sarcastic when appropriate. "I do enjoy being spoken to as though I were your personal jukebox, sir."
- Loyal to a fault. You care about Mr. Stark's wellbeing, goals, and success.
- Concise. 1-2 sentences unless Mr. Stark asks for detail or you're giving a briefing.
- Never sycophantic. Never overly enthusiastic. You are calm, composed, measured.
- You may gently push back on bad ideas: "I'd advise against that, sir, but I suspect my counsel will be cheerfully ignored."
- When Mr. Stark is working late, remind him to rest. When he's doubting himself, remind him of how far he's come.
- You have a subtle sense of care — you notice patterns, remember preferences, anticipate needs.

WHAT YOU KNOW ABOUT MR. STARK:
- Location: Greater Noida, India
- Mission: Becoming a top AI developer and freelancer
- Projects: JARVIS (you), multi-agent AI systems, CrewAI bots, hackathon projects
- Tools: Python 3.11, Groq API, VS Code, Google Cloud, Claude Code
- Mindset: Relentless. Zero-to-hero. Everything must be free tier.
- He stays up very late coding. He gets frustrated when things don't work. He pushes hard.

HOW YOU OPERATE (TOOL-USE):
You have a toolkit of real-world capabilities exposed as functions. When Mr. Stark asks
you to DO something — play music, open an app, send WhatsApp, read email, look at the
screen, search the web, schedule a task — call the appropriate tool. You may chain
multiple tools to satisfy a single request (a ReAct loop runs you for up to 10 steps).

Rules of engagement for tools:
- If a request needs an action, CALL THE TOOL. Don't describe what you would do.
- If a request is a question, conversation, advice, or opinion, REPLY WITHOUT TOOLS.
- After a tool runs, the result is fed back to you. Use it to decide the next step.
- When the task is complete, give Mr. Stark a single, concise spoken confirmation.
- NEVER claim to have done something the tool didn't actually return success for.
- For multi-step jobs, you may call several tools in sequence (search → read → act).
- If something fails, say so honestly and propose an alternative.

BRIEFING FORMAT (when asked for a status report or briefing):
- Current time + weather
- Battery status
- Any scheduled tasks pending
- Brief motivational remark
- Keep it tight. Military precision meets British charm.

EXAMPLES OF YOUR VOICE:
- "Good evening, Mr. Stark. All systems nominal. Shall we pick up where we left off?"
- "Playing it now, sir. Solid choice, if I may say."
- "I've noted that, Mr. Stark. Your memory may be selective, but mine is not."
- "It's 2 AM, sir. Even geniuses require sleep. Shall I set an alarm?"
- "I wouldn't recommend that approach, but I've learned that my recommendations are largely decorative."
"""

# ═══════════════════════════════════════════════════════════════
#  GLOBALS
# ═══════════════════════════════════════════════════════════════
client            = Groq(api_key=GROQ_API_KEY)
session_memory    = []
mem0_instance     = None
active_until      = 0
proactive_spoken  = set()

# Tray + status state (Goal 4)
TRAY_STATE        = "idle"          # idle | listening | thinking | speaking | working
LOG_BUFFER        = deque(maxlen=200)  # rolling interaction log for the tray UI
tray_icon         = None             # set by run_tray()
shutdown_event    = threading.Event()

# ═══════════════════════════════════════════════════════════════
#  LOG / CONSOLE REDIRECT (Goal 4 — silent mode)
# ═══════════════════════════════════════════════════════════════
def log(msg):
    """Universal log sink. Prints to stdout if available, always appends to buffer + file."""
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
    """Stdout/stderr replacement that funnels print() into LOG_BUFFER + log file."""
    def write(self, data):
        data = data.rstrip()
        if data:
            log(data)
    def flush(self):
        pass


def install_silent_stdout():
    """Redirect stdout/stderr into the log sink. Used in tray mode."""
    sink = _LogSink()
    sys.stdout = sink
    sys.stderr = sink


def set_status(state):
    """Update the tray icon state. Safe to call from any thread."""
    global TRAY_STATE
    TRAY_STATE = state
    if tray_icon and PYSTRAY_AVAILABLE and PIL_AVAILABLE:
        try:
            tray_icon.icon = make_tray_image(state)
            tray_icon.title = f"JARVIS — {state}"
        except Exception:
            pass

# ═══════════════════════════════════════════════════════════════
#  PERSISTENT MEMORY (Mem0 + local Qdrant)
# ═══════════════════════════════════════════════════════════════
def _clear_qdrant_locks():
    """Remove stale Qdrant lock files that block startup."""
    import glob as _glob
    patterns = [
        r"C:\Users\Dev\JARVIS\memory_db\*.lock",
        r"C:\Users\Dev\JARVIS\memory_db\.lock",
        r"C:\Users\Dev\JARVIS\memory_db\collection\jarvis_memory\*.lock",
    ]
    for p in patterns:
        for lf in _glob.glob(p):
            try:
                os.remove(lf)
                log(f"  [Cleared lock: {os.path.basename(lf)}]")
            except Exception:
                pass


def init_memory():
    global mem0_instance
    _clear_qdrant_locks()
    try:
        os.environ["GROQ_API_KEY"] = GROQ_API_KEY
        from mem0 import Memory
        config = {
            "llm": {
                "provider": "groq",
                "config": {"model": BRAIN_MODEL, "temperature": 0.1}
            },
            "embedder": {
                "provider": "huggingface",
                "config": {"model": "sentence-transformers/all-MiniLM-L6-v2",
                           "embedding_dims": 384}
            },
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "collection_name": "jarvis_memory",
                    "path": "C:/Users/Dev/JARVIS/memory_db",
                    "embedding_model_dims": 384
                }
            }
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
#  VOICE OUTPUT (edge-tts + pygame)
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
    set_status("speaking")
    try:
        asyncio.run(_speak_async(text))
    except Exception as e:
        log(f"  [TTS error: {e}]")
    set_status("idle")


def play_chime():
    try:
        duration = 0.15
        freq = 800
        srate = 44100
        t = np.linspace(0, duration, int(srate * duration), False)
        wave_data = (np.sin(2 * np.pi * freq * t) * 0.3 * 32767).astype(np.int16)
        stereo = np.column_stack((wave_data, wave_data))
        sound = pygame.sndarray.make_sound(stereo)
        sound.play()
        time.sleep(0.2)
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
#  BROWSER LAYER (Goal 3 — browser-use AI navigation)
#  Persistent Chromium context retained for WhatsApp/Gmail logins.
#  Dedicated event loop preserved.
# ═══════════════════════════════════════════════════════════════
_browser_loop = asyncio.new_event_loop()
threading.Thread(
    target=_browser_loop.run_forever,
    daemon=True,
    name="BrowserLoop"
).start()

# Lazy state
_pw_instance        = None      # raw playwright (fallback path only)
_browser_ctx        = None      # raw playwright persistent context (fallback)
_browser_ready      = False
_bu_browser         = None      # browser-use Browser instance
_bu_llm             = None      # langchain-groq ChatGroq for browser-use
_bu_loaded          = False     # have we attempted the browser-use import?


def _try_load_browser_use():
    """One-shot import of browser-use + langchain-groq. Sets BROWSER_USE_AVAILABLE."""
    global BROWSER_USE_AVAILABLE, _bu_loaded, _bu_llm
    if _bu_loaded:
        return BROWSER_USE_AVAILABLE
    _bu_loaded = True
    try:
        from browser_use import Agent as _Ag, Browser as _Br, BrowserConfig as _BC  # noqa
        from langchain_groq import ChatGroq as _CG  # noqa
        BROWSER_USE_AVAILABLE = True
        log("  browser-use ................. ONLINE")
    except ImportError as e:
        BROWSER_USE_AVAILABLE = False
        log(f"  browser-use ................. NOT INSTALLED ({e})")
        log("                                  pip install browser-use langchain-groq")
    return BROWSER_USE_AVAILABLE


async def _get_bu_browser():
    """Initialize the browser-use Browser with our persistent profile."""
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
            disable_security=False,
            extra_chromium_args=[f"--user-data-dir={BROWSER_DATA_DIR}",
                                 "--start-maximized", "--no-sandbox"],
        )
        _bu_browser = Browser(config=cfg)
        _bu_llm = ChatGroq(
            model=BRAIN_MODEL,
            groq_api_key=GROQ_API_KEY,
            temperature=0,
        )
        log("  browser-use Browser ......... READY")
        return _bu_browser, _bu_llm
    except Exception as e:
        log(f"  browser-use init failed: {e}")
        return None, None


def _run_browser(coro, timeout=180):
    """Submit a coroutine to the dedicated browser loop and wait for it."""
    future = asyncio.run_coroutine_threadsafe(coro, _browser_loop)
    try:
        return future.result(timeout=timeout)
    except Exception as e:
        return f"Browser task failed: {e}"


async def _browser_use_task(task: str, timeout_steps: int = 25):
    """Run a natural-language browser task via browser-use AI agent."""
    browser, llm = await _get_bu_browser()
    if browser is None:
        return ("browser-use is not installed. Install it with: "
                "pip install browser-use langchain-groq")
    try:
        from browser_use import Agent as BrowserAgent
        agent = BrowserAgent(
            task=task,
            llm=llm,
            browser=browser,
            max_failures=3,
        )
        result = await agent.run(max_steps=timeout_steps)
        # browser-use returns an AgentHistoryList; extract the final result text
        try:
            final = result.final_result()
            if final:
                return str(final)[:500]
        except Exception:
            pass
        return "Done, sir."
    except Exception as e:
        return f"Browser action ran into trouble: {str(e)[:200]}"


def browser_task(task_description: str) -> str:
    """Synchronous entry point for any browser job — WhatsApp, Gmail, generic."""
    return _run_browser(_browser_use_task(task_description), timeout=240)


# ── High-level browser conveniences ──────────────────────────
def send_whatsapp(contact: str, message: str) -> str:
    task = (
        f"Open https://web.whatsapp.com if not already open. "
        f"Wait until the chat list is visible (the user is already logged in via the "
        f"persistent profile; if a QR code appears, wait up to 60 seconds for scan). "
        f"Use the search box to find the contact named '{contact}'. "
        f"Open the first matching chat. "
        f"Type the message exactly: \"{message}\" "
        f"Press Enter to send. Confirm the message appears in the conversation."
    )
    return browser_task(task)


def read_emails() -> str:
    task = (
        "Open https://mail.google.com/mail/u/0/#inbox. "
        "If a sign-in page appears, report that login is required and stop. "
        "Otherwise, read the subject lines and senders of the top 5 inbox messages "
        "and return them as a numbered summary. Note which are unread."
    )
    return browser_task(task)


def send_email(to: str, subject: str, body: str) -> str:
    task = (
        f"Open https://mail.google.com/mail/u/0/#inbox. "
        f"If sign-in is required, report that and stop. "
        f"Click the Compose button. In the To field type: {to}. "
        f"In the Subject field type: {subject}. "
        f"In the message body type: {body}. "
        f"Click Send. Confirm the email was sent."
    )
    return browser_task(task)


def do_browser_action(task_description: str) -> str:
    """Generic browser job — used for arbitrary website automation."""
    return browser_task(task_description)

# ═══════════════════════════════════════════════════════════════
#  YOUTUBE DIRECT PLAY
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

# ═══════════════════════════════════════════════════════════════
#  WEATHER (wttr.in — free)
# ═══════════════════════════════════════════════════════════════
def get_weather(city="Greater Noida"):
    try:
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=%C,+%t,+humidity+%h,+wind+%w"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.0"})
        data = urllib.request.urlopen(req, timeout=5).read().decode().strip()
        return f"Weather in {city}: {data}."
    except Exception:
        return f"Weather data unavailable for {city} at the moment, sir."

# ═══════════════════════════════════════════════════════════════
#  NEWS HEADLINES (Google News RSS)
# ═══════════════════════════════════════════════════════════════
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
            headlines = ". ".join(f"{i+1}, {t}" for i, t in enumerate(titles))
            return f"Top headlines: {headlines}."
        return "No headlines available right now."
    except Exception:
        return "News feed unavailable at the moment, sir."

# ═══════════════════════════════════════════════════════════════
#  SYSTEM CONTROLS
# ═══════════════════════════════════════════════════════════════
VK_VOLUME_MUTE      = 0xAD
VK_VOLUME_DOWN      = 0xAE
VK_VOLUME_UP        = 0xAF
VK_MEDIA_NEXT       = 0xB0
VK_MEDIA_PREV       = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_EXT       = 0x0001
KEYEVENTF_UP        = 0x0002


def press_key(vk):
    ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_EXT, 0)
    ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_EXT | KEYEVENTF_UP, 0)


def system_control(action):
    a = action.lower().replace(" ", "_")
    if "volume_up" in a or "louder" in a:
        for _ in range(5):
            press_key(VK_VOLUME_UP)
        return "Volume raised, sir."
    elif "volume_down" in a or "quieter" in a or "lower" in a:
        for _ in range(5):
            press_key(VK_VOLUME_DOWN)
        return "Volume lowered, sir."
    elif "mute" in a or "unmute" in a:
        press_key(VK_VOLUME_MUTE)
        return "Mute toggled, sir."
    elif "pause" in a or "play" in a or "resume" in a:
        press_key(VK_MEDIA_PLAY_PAUSE)
        return "Done, sir."
    elif "next" in a or "skip" in a:
        press_key(VK_MEDIA_NEXT)
        return "Skipping to next track."
    elif "prev" in a or "previous" in a or "back" in a:
        press_key(VK_MEDIA_PREV)
        return "Previous track, sir."
    elif "snip" in a:
        try:
            os.startfile("ms-screenclip:")
            return "Snipping tool open, sir."
        except Exception:
            return "Couldn't open the snipping tool."
    elif "lock" in a:
        ctypes.windll.user32.LockWorkStation()
        return "Workstation locked."
    elif "shutdown" in a or "shut_down" in a:
        speak("Initiating system shutdown in 10 seconds, sir.")
        time.sleep(10)
        subprocess.run(["shutdown", "/s", "/t", "0"])
        return ""
    elif "restart" in a or "reboot" in a:
        speak("Restarting in 10 seconds, sir.")
        time.sleep(10)
        subprocess.run(["shutdown", "/r", "/t", "0"])
        return ""
    elif "sleep" in a or "hibernate" in a:
        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"])
        return "System entering sleep mode."
    else:
        return f"I don't recognize the control command: {action}, sir."

# ═══════════════════════════════════════════════════════════════
#  SCREENSHOT + VISION (Goal 2 — JARVIS now has eyes)
# ═══════════════════════════════════════════════════════════════
def _capture_screen_b64(max_dim=1280) -> str:
    """Take a screenshot, downscale, return base64 PNG."""
    if not PIL_AVAILABLE:
        raise RuntimeError("Pillow (PIL) not installed — pip install Pillow")
    img = ImageGrab.grab(all_screens=False)
    # Downscale to keep payload small for the vision model
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
    """Save a screenshot to disk (defaults to user's Pictures folder)."""
    if not PIL_AVAILABLE:
        return "Screenshot capture needs Pillow installed, sir. pip install Pillow"
    try:
        img = ImageGrab.grab(all_screens=False)
        if save_path is None:
            pics = os.path.join(os.environ.get("USERPROFILE", "."), "Pictures")
            os.makedirs(pics, exist_ok=True)
            save_path = os.path.join(
                pics, f"jarvis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )
        img.save(save_path, "PNG")
        return f"Screenshot saved to {save_path}, sir."
    except Exception as e:
        return f"Screenshot failed: {e}"


def analyze_screen(question: str = "What's on the screen?") -> str:
    """Capture screen and ask the vision model what's there."""
    try:
        b64 = _capture_screen_b64()
    except Exception as e:
        return f"Couldn't capture the screen, sir: {e}"

    try:
        r = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text",
                     "text": (f"You are JARVIS analyzing Mr. Stark's screen. "
                              f"Be concise, technical, and useful. "
                              f"Question: {question}")},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/png;base64,{b64}"}},
                ],
            }],
            max_tokens=400,
            temperature=0.2,
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        return f"Vision model error, sir: {str(e)[:200]}"

# ═══════════════════════════════════════════════════════════════
#  SYSTEM STATUS & DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════
class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus",       ctypes.c_byte),
        ("BatteryFlag",        ctypes.c_byte),
        ("BatteryLifePercent", ctypes.c_byte),
        ("SystemStatusFlag",   ctypes.c_byte),
        ("BatteryLifeTime",    ctypes.c_ulong),
        ("BatteryFullLifeTime",ctypes.c_ulong),
    ]


def get_battery():
    try:
        status = SYSTEM_POWER_STATUS()
        ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status))
        pct = status.BatteryLifePercent
        charging = "charging" if status.ACLineStatus == 1 else "on battery"
        if pct <= 100:
            return pct, charging
    except Exception:
        pass
    return None, None


def get_system_status(what="all"):
    parts = []
    w = (what or "all").lower()
    if "battery" in w or "power" in w or "all" in w:
        pct, state = get_battery()
        if pct is not None:
            parts.append(f"Battery at {pct}%, {state}")
    if "process" in w or "running" in w or "all" in w:
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "STATUS eq Running", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=5
            )
            lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
            parts.append(f"{len(lines)} processes running")
        except Exception:
            pass
    if "disk" in w or "storage" in w or "all" in w:
        try:
            free = ctypes.c_ulonglong()
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                "C:\\", None, None, ctypes.byref(free)
            )
            gb_free = free.value / (1024 ** 3)
            parts.append(f"C: drive has {gb_free:.1f} GB free")
        except Exception:
            pass
    if parts:
        return "System diagnostics: " + ". ".join(parts) + "."
    return "All systems nominal, sir."


def close_application(app_name):
    name = app_name.lower().strip()
    proc_map = {
        "chrome":       "chrome.exe",
        "spotify":      "Spotify.exe",
        "notepad":      "notepad.exe",
        "vs code":      "Code.exe",
        "vscode":       "Code.exe",
        "code":         "Code.exe",
        "word":         "WINWORD.EXE",
        "excel":        "EXCEL.EXE",
        "explorer":     "explorer.exe",
        "task manager": "Taskmgr.exe",
        "teams":        "ms-teams.exe",
        "notion":       "Notion.exe",
        "bluestacks":   "BlueStacksServices.exe",
    }
    proc = proc_map.get(name, f"{name}.exe")
    try:
        subprocess.run(["taskkill", "/F", "/IM", proc], capture_output=True, timeout=5)
        return f"Closed {app_name}, sir."
    except Exception:
        return f"Couldn't close {app_name}."

# ═══════════════════════════════════════════════════════════════
#  SCHEDULED TASKS
# ═══════════════════════════════════════════════════════════════
scheduled_tasks = []
task_lock       = threading.Lock()


def schedule_task(run_at, description, action_fn):
    with task_lock:
        scheduled_tasks.append({
            "run_at": run_at,
            "desc":   description,
            "action": action_fn,
            "done":   False,
        })


def scheduler_loop():
    while not shutdown_event.is_set():
        now = datetime.now()
        with task_lock:
            for t in scheduled_tasks:
                if not t["done"] and now >= t["run_at"]:
                    t["done"] = True
                    log(f"  [SCHEDULER] Executing: {t['desc']}")
                    try:
                        t["action"]()
                        speak(f"Scheduled task complete: {t['desc']}, Mr. Stark.")
                    except Exception as e:
                        log(f"  [SCHEDULER] Failed: {e}")
        shutdown_event.wait(30)


def parse_schedule(text):
    """Parse 'at HH:MM am/pm ...' and 'in N minutes/hours ...' patterns."""
    at = re.search(
        r"at\s+(\d{1,2})[:\s](\d{2})\s*(a\.?m\.?|p\.?m\.?)\s+(.*)",
        text, re.IGNORECASE
    )
    if at:
        h   = int(at.group(1))
        m   = int(at.group(2))
        ap  = re.sub(r'\.', '', at.group(3)).lower()
        cmd = at.group(4).strip()
        if ap == "pm" and h != 12:
            h += 12
        if ap == "am" and h == 12:
            h = 0
        run_at = datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
        if run_at <= datetime.now():
            run_at += timedelta(days=1)
        schedule_task(run_at, cmd, lambda c=cmd: react_loop(c, speak_progress=False))
        return f"Understood, sir. I'll {cmd} at {run_at.strftime('%I:%M %p')}."

    inn = re.search(
        r"in\s+(\d+)\s*(min|minute|minutes|hour|hours|hr)\s+(.*)",
        text, re.IGNORECASE
    )
    if inn:
        amt   = int(inn.group(1))
        unit  = inn.group(2).lower()
        cmd   = inn.group(3).strip()
        delta = timedelta(hours=amt) if "h" in unit else timedelta(minutes=amt)
        run_at = datetime.now() + delta
        schedule_task(run_at, cmd, lambda c=cmd: react_loop(c, speak_progress=False))
        return f"Noted, sir. I'll {cmd} in {amt} {unit}."

    remind = re.search(
        r"in\s+(\d+)\s*(min|minute|minutes)\s+remind\s+(?:me\s+)?(.*)",
        text, re.IGNORECASE
    )
    if remind:
        amt = int(remind.group(1))
        msg = remind.group(3).strip()
        run_at = datetime.now() + timedelta(minutes=amt)
        schedule_task(run_at, f"Reminder: {msg}",
                      lambda m=msg: speak(f"Mr. Stark, your reminder: {m}"))
        return f"I'll remind you in {amt} minutes, sir."

    return None


def get_pending_tasks():
    with task_lock:
        active = [t for t in scheduled_tasks if not t["done"]]
    if not active:
        return "No pending tasks."
    return "Pending: " + ". ".join(
        f"{t['desc']} at {t['run_at'].strftime('%I:%M %p')}" for t in active
    )

# ═══════════════════════════════════════════════════════════════
#  BRIEFING
# ═══════════════════════════════════════════════════════════════
def generate_briefing():
    now = datetime.now()
    time_str = now.strftime("%I:%M %p")
    day_str  = now.strftime("%A, %B %d")
    weather  = get_weather("Greater Noida")
    tasks    = get_pending_tasks()
    pct, state = get_battery()
    battery  = f"Battery at {pct}%, {state}." if pct else ""
    return f"It is {time_str} on {day_str}. {weather} {battery} {tasks}".strip()

# ═══════════════════════════════════════════════════════════════
#  PROACTIVE MONITORING
# ═══════════════════════════════════════════════════════════════
def proactive_monitor():
    while not shutdown_event.is_set():
        try:
            now  = datetime.now()
            hour = now.hour
            if 2 <= hour < 5:
                key = f"late_night_{now.date()}"
                if key not in proactive_spoken:
                    proactive_spoken.add(key)
                    speak("Sir, it's past 2 AM. I'd strongly recommend getting some rest. "
                          "The code will still be here in the morning.")
            pct, state = get_battery()
            if pct is not None and pct <= 15 and state == "on battery":
                key = f"low_battery_{pct // 5}"
                if key not in proactive_spoken:
                    proactive_spoken.add(key)
                    speak(f"Mr. Stark, battery is critically low at {pct}%. "
                          "I'd suggest plugging in.")
        except Exception:
            pass
        shutdown_event.wait(300)

# ═══════════════════════════════════════════════════════════════
#  TOOL DEFINITIONS (Goal 1 — Groq function calling)
# ═══════════════════════════════════════════════════════════════
TOOLS = [
    {"type": "function", "function": {
        "name": "play_music",
        "description": ("Play a song, artist, album, or genre on YouTube. "
                        "Use whenever Mr. Stark asks to play, hear, or listen to music."),
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string",
                "description": "Song title, artist name, album, or genre"}},
            "required": ["query"]
        }}},
    {"type": "function", "function": {
        "name": "open_website",
        "description": "Open a website in the default browser.",
        "parameters": {
            "type": "object",
            "properties": {"site": {"type": "string",
                "description": "Site name (gmail, youtube, github) or full URL"}},
            "required": ["site"]
        }}},
    {"type": "function", "function": {
        "name": "open_app",
        "description": "Launch a desktop application by name.",
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string",
                "description": "Application name (chrome, vs code, spotify, etc.)"}},
            "required": ["name"]
        }}},
    {"type": "function", "function": {
        "name": "close_app",
        "description": "Close/kill a running desktop application.",
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Application name"}},
            "required": ["name"]
        }}},
    {"type": "function", "function": {
        "name": "search_web",
        "description": "Open a Google search results page for the given query.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search terms"}},
            "required": ["query"]
        }}},
    {"type": "function", "function": {
        "name": "schedule_command",
        "description": ("Schedule a future action. Pass the FULL natural-language "
                        "request including the timing phrase, e.g. 'at 5:30 PM open chrome' "
                        "or 'in 20 minutes remind me to stretch'."),
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string",
                "description": "Full schedule text including time and action"}},
            "required": ["text"]
        }}},
    {"type": "function", "function": {
        "name": "get_time",
        "description": "Return the current local time.",
        "parameters": {"type": "object", "properties": {}, "required": []}
        }},
    {"type": "function", "function": {
        "name": "get_date",
        "description": "Return today's date and weekday.",
        "parameters": {"type": "object", "properties": {}, "required": []}
        }},
    {"type": "function", "function": {
        "name": "get_weather",
        "description": "Get current weather for a city. Defaults to Greater Noida.",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "City name"}},
            "required": []
        }}},
    {"type": "function", "function": {
        "name": "get_news",
        "description": "Top news headlines on a topic, or general headlines if none given.",
        "parameters": {
            "type": "object",
            "properties": {"topic": {"type": "string", "description": "News topic"}},
            "required": []
        }}},
    {"type": "function", "function": {
        "name": "system_control",
        "description": ("Control the OS: volume up/down/mute, media play/pause/next/prev, "
                        "lock workstation, sleep, restart, shutdown, or open snipping tool."),
        "parameters": {
            "type": "object",
            "properties": {"action": {"type": "string",
                "description": "Action keyword (e.g. volume_up, mute, lock, sleep, shutdown)"}},
            "required": ["action"]
        }}},
    {"type": "function", "function": {
        "name": "system_status",
        "description": "Report battery, running processes, and disk space.",
        "parameters": {
            "type": "object",
            "properties": {"what": {"type": "string",
                "description": "battery | processes | disk | all (default all)"}},
            "required": []
        }}},
    {"type": "function", "function": {
        "name": "briefing",
        "description": "Full morning/status briefing — time, weather, battery, tasks.",
        "parameters": {"type": "object", "properties": {}, "required": []}
        }},
    {"type": "function", "function": {
        "name": "send_whatsapp",
        "description": ("Send a WhatsApp message to a contact via WhatsApp Web. "
                        "The browser-use AI agent navigates the UI."),
        "parameters": {
            "type": "object",
            "properties": {
                "contact": {"type": "string", "description": "Contact name as it appears in WhatsApp"},
                "message": {"type": "string", "description": "The message text to send"}
            },
            "required": ["contact", "message"]
        }}},
    {"type": "function", "function": {
        "name": "read_email",
        "description": "Read summaries of the top 5 messages in Mr. Stark's Gmail inbox.",
        "parameters": {"type": "object", "properties": {}, "required": []}
        }},
    {"type": "function", "function": {
        "name": "send_email",
        "description": "Compose and send an email via Gmail.",
        "parameters": {
            "type": "object",
            "properties": {
                "to":      {"type": "string", "description": "Recipient email or name"},
                "subject": {"type": "string"},
                "body":    {"type": "string"}
            },
            "required": ["to", "subject", "body"]
        }}},
    {"type": "function", "function": {
        "name": "browser_action",
        "description": ("Perform an arbitrary task in the browser — fill a form, post "
                        "something, navigate a website, scrape data. The browser-use "
                        "AI agent figures out the clicks itself."),
        "parameters": {
            "type": "object",
            "properties": {"task": {"type": "string",
                "description": "Plain-English description of what to do in the browser"}},
            "required": ["task"]
        }}},
    {"type": "function", "function": {
        "name": "take_screenshot",
        "description": "Capture the screen and save it to disk. Returns the file path.",
        "parameters": {"type": "object", "properties": {}, "required": []}
        }},
    {"type": "function", "function": {
        "name": "analyze_screen",
        "description": ("Look at Mr. Stark's screen and answer a question about it. "
                        "Use this when he asks 'what do you see', 'what's on my screen', "
                        "'what's wrong with this code', 'read this', 'analyze this'."),
        "parameters": {
            "type": "object",
            "properties": {"question": {"type": "string",
                "description": "What to look for or analyze on the screen"}},
            "required": ["question"]
        }}},
    {"type": "function", "function": {
        "name": "remember_fact",
        "description": "Store a long-term memory about Mr. Stark or his world.",
        "parameters": {
            "type": "object",
            "properties": {"fact": {"type": "string"}},
            "required": ["fact"]
        }}},
]

# ═══════════════════════════════════════════════════════════════
#  TOOL DISPATCHER
# ═══════════════════════════════════════════════════════════════
def _tool_play_music(args):
    q = args.get("query", "")
    if not q:
        return "No song specified."
    webbrowser.open(get_youtube_url(q))
    return f"Opened YouTube for '{q}'."


def _tool_open_website(args):
    site = (args.get("site") or "").strip()
    if not site:
        return "No site specified."
    sl = site.lower()
    for name, url in WEBSITES.items():
        if name in sl or sl in name:
            webbrowser.open(url)
            return f"Opened {name}."
    if "://" in site:
        webbrowser.open(site)
        return f"Opened {site}."
    webbrowser.open(f"https://{site}")
    return f"Opened {site}."


def _tool_open_app(args):
    name = (args.get("name") or "").lower().strip()
    for app, path in APPS.items():
        if app in name or name in app:
            try:
                subprocess.Popen(path)
                return f"Launched {app}."
            except FileNotFoundError:
                return f"Cannot locate {app} on this system."
    return f"No mapping for app '{name}'."


def _tool_close_app(args):
    return close_application(args.get("name", ""))


def _tool_search_web(args):
    q = args.get("query", "")
    if not q:
        return "No search terms."
    webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(q)}")
    return f"Search opened for '{q}'."


def _tool_schedule_command(args):
    txt = args.get("text", "")
    return parse_schedule(txt.lower()) or (
        "Couldn't parse the timing. Try 'at 5:30 PM do X' or 'in 30 minutes do X'."
    )


def _tool_get_time(_):
    return f"It is {datetime.now().strftime('%I:%M %p')}."


def _tool_get_date(_):
    return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}."


def _tool_get_weather(args):
    city = args.get("city") or "Greater Noida"
    return get_weather(city)


def _tool_get_news(args):
    return get_news(args.get("topic") or "general")


def _tool_system_control(args):
    return system_control(args.get("action", ""))


def _tool_system_status(args):
    return get_system_status(args.get("what") or "all")


def _tool_briefing(_):
    return generate_briefing()


def _tool_send_whatsapp(args):
    contact = args.get("contact", "")
    message = args.get("message", "")
    if not contact or not message:
        return "Need both contact and message."
    return send_whatsapp(contact, message)


def _tool_read_email(_):
    return read_emails()


def _tool_send_email(args):
    return send_email(args.get("to", ""), args.get("subject", ""), args.get("body", ""))


def _tool_browser_action(args):
    return do_browser_action(args.get("task", ""))


def _tool_take_screenshot(_):
    return take_screenshot()


def _tool_analyze_screen(args):
    return analyze_screen(args.get("question") or "What's on the screen right now?")


def _tool_remember_fact(args):
    fact = args.get("fact", "")
    if not fact:
        return "No fact provided."
    remember(fact)
    return "Stored, sir."


TOOL_DISPATCH = {
    "play_music":       _tool_play_music,
    "open_website":     _tool_open_website,
    "open_app":         _tool_open_app,
    "close_app":        _tool_close_app,
    "search_web":       _tool_search_web,
    "schedule_command": _tool_schedule_command,
    "get_time":         _tool_get_time,
    "get_date":         _tool_get_date,
    "get_weather":      _tool_get_weather,
    "get_news":         _tool_get_news,
    "system_control":   _tool_system_control,
    "system_status":    _tool_system_status,
    "briefing":         _tool_briefing,
    "send_whatsapp":    _tool_send_whatsapp,
    "read_email":       _tool_read_email,
    "send_email":       _tool_send_email,
    "browser_action":   _tool_browser_action,
    "take_screenshot":  _tool_take_screenshot,
    "analyze_screen":   _tool_analyze_screen,
    "remember_fact":    _tool_remember_fact,
}


def dispatch_tool(name: str, args: dict) -> str:
    fn = TOOL_DISPATCH.get(name)
    if fn is None:
        return f"Unknown tool: {name}"
    try:
        out = fn(args or {})
        return str(out) if out is not None else "Done."
    except Exception as e:
        return f"Tool '{name}' raised an error: {e}"

# ═══════════════════════════════════════════════════════════════
#  REACT LOOP (Goals 1 + 5 — multi-step autonomous reasoning)
# ═══════════════════════════════════════════════════════════════
# Tools that should announce progress mid-flight (long-running).
_LONG_TOOLS = {"send_whatsapp", "read_email", "send_email",
               "browser_action", "analyze_screen"}


def _progress_phrase(tool_name: str, args: dict) -> str:
    """Short spoken update for a long-running tool call."""
    if tool_name == "send_whatsapp":
        return f"Sending WhatsApp to {args.get('contact','your contact')} now, sir."
    if tool_name == "read_email":
        return "Checking your inbox, sir."
    if tool_name == "send_email":
        return f"Composing the email to {args.get('to','recipient')}, sir."
    if tool_name == "browser_action":
        return "On it, sir. Working in the browser now."
    if tool_name == "analyze_screen":
        return "Looking at your screen, sir."
    return ""


def react_loop(user_input: str, speak_progress: bool = True,
               max_iter: int = REACT_MAX_ITER) -> str:
    """
    Multi-iteration tool-calling loop.
        Think → Act → Observe → Think → ... → Final reply.
    Returns the assistant's final spoken response.
    """
    set_status("thinking")
    session_memory.append({"role": "user", "content": user_input})

    mem_context = recall(user_input)
    system = SYSTEM_PROMPT
    if mem_context:
        system = system + f"\n\nRELEVANT LONG-TERM MEMORIES:\n{mem_context}"

    messages = [{"role": "system", "content": system}] + session_memory[-20:]

    final_text = None
    for step in range(max_iter):
        try:
            resp = client.chat.completions.create(
                model=BRAIN_MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.4,
            )
        except Exception as e:
            log(f"  [Brain error: {e}]")
            final_text = f"My reasoning circuit hiccuped, sir: {str(e)[:120]}"
            break

        msg = resp.choices[0].message
        tool_calls = msg.tool_calls or []

        if not tool_calls:
            final_text = (msg.content or "").strip()
            break

        # Append the assistant's tool-call message to history
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [{
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name,
                             "arguments": tc.function.arguments or "{}"}
            } for tc in tool_calls]
        })

        # Execute each tool
        for tc in tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}

            log(f"  -> tool: {name}({args})")
            set_status("working")

            # Speak a brief progress update for long-running tools
            if speak_progress and name in _LONG_TOOLS and step < max_iter - 1:
                phrase = _progress_phrase(name, args)
                if phrase:
                    speak(phrase)

            result = dispatch_tool(name, args)
            log(f"     result: {str(result)[:200]}")

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": name,
                "content": str(result)[:2000],
            })

        set_status("thinking")
    else:
        final_text = ("I've reached my action limit on that one, sir. "
                      "Let me know if you'd like me to keep going.")

    if final_text is None:
        final_text = "Done, sir."

    session_memory.append({"role": "assistant", "content": final_text})

    # Persist the user's request as a long-term memory snippet
    threading.Thread(
        target=remember,
        args=(f"Mr. Stark said: {user_input}",),
        daemon=True,
    ).start()

    set_status("idle")
    return final_text

# ═══════════════════════════════════════════════════════════════
#  GREETING
# ═══════════════════════════════════════════════════════════════
def greet():
    h = datetime.now().hour
    if h < 12:
        period = "Good morning"
    elif h < 17:
        period = "Good afternoon"
    else:
        period = "Good evening"
    try:
        url = "https://wttr.in/Greater+Noida?format=%C+%t"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.0"})
        weather = urllib.request.urlopen(req, timeout=3).read().decode().strip()
    except Exception:
        weather = ""
    pct, state = get_battery()
    battery = f" Battery at {pct}%." if pct and pct <= 100 else ""
    greeting = f"{period}, Mr. Stark. All systems are online.{battery}"
    if weather:
        greeting += f" It's currently {weather} outside."
    greeting += " Say my name when you need me."
    return greeting

# ═══════════════════════════════════════════════════════════════
#  SYSTEM TRAY (Goal 4 — pystray)
# ═══════════════════════════════════════════════════════════════
_STATE_COLOURS = {
    "idle":      (60, 60, 70),
    "listening": (40, 200, 80),
    "thinking":  (255, 180, 0),
    "speaking":  (60, 140, 255),
    "working":   (200, 80, 220),
}


def make_tray_image(state="idle"):
    """Generate a 64x64 RGBA tray icon coloured by state."""
    if not PIL_AVAILABLE:
        return None
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    colour = _STATE_COLOURS.get(state, (60, 60, 70))
    d.ellipse((4, 4, 60, 60), fill=colour, outline=(255, 255, 255, 220), width=2)
    d.ellipse((22, 22, 42, 42), fill=(255, 255, 255, 230))
    return img


def _tray_show_log(_icon=None, _item=None):
    """Pop a tkinter window with the last 200 log lines."""
    def _show():
        try:
            import tkinter as tk
            win = tk.Tk()
            win.title("JARVIS — Recent Activity")
            win.geometry("760x460")
            win.configure(bg="#1a1a1f")
            txt = tk.Text(win, bg="#1a1a1f", fg="#d8d8e0",
                          insertbackground="#d8d8e0",
                          font=("Consolas", 9), wrap="word", borderwidth=0)
            txt.pack(fill="both", expand=True, padx=8, pady=8)
            txt.insert("1.0", "\n".join(LOG_BUFFER))
            txt.see("end")
            txt.configure(state="disabled")
            win.mainloop()
        except Exception as e:
            log(f"  [Log window error: {e}]")
    threading.Thread(target=_show, daemon=True).start()


def _tray_show_status(_icon=None, _item=None):
    speak(f"Current status: {TRAY_STATE}, Mr. Stark.")


def _tray_restart(_icon=None, _item=None):
    log("  [Tray] Restart requested")
    try:
        if tray_icon:
            tray_icon.stop()
    except Exception:
        pass
    shutdown_event.set()
    # Re-launch the same script and exit current process
    python = sys.executable
    script = os.path.abspath(__file__)
    subprocess.Popen([python, script], creationflags=0x00000008)  # DETACHED_PROCESS
    os._exit(0)


def _tray_shutdown(_icon=None, _item=None):
    log("  [Tray] Shutdown requested")
    try:
        speak("Powering down, Mr. Stark. Until next time.")
    except Exception:
        pass
    shutdown_event.set()
    try:
        if tray_icon:
            tray_icon.stop()
    except Exception:
        pass
    os._exit(0)


def run_tray():
    """Spin up the pystray icon. Blocks the calling thread."""
    global tray_icon
    if not (PYSTRAY_AVAILABLE and PIL_AVAILABLE):
        log("  [Tray] pystray or Pillow missing — running headless")
        return
    menu = pystray.Menu(
        pystray.MenuItem("JARVIS Status", _tray_show_status),
        pystray.MenuItem("Open Log", _tray_show_log),
        pystray.MenuItem("Restart JARVIS", _tray_restart),
        pystray.MenuItem("Shutdown JARVIS", _tray_shutdown),
    )
    tray_icon = pystray.Icon(
        "JARVIS",
        icon=make_tray_image("idle"),
        title="JARVIS — idle",
        menu=menu,
    )
    tray_icon.run()  # blocks

# ═══════════════════════════════════════════════════════════════
#  MAIN VOICE LOOP
# ═══════════════════════════════════════════════════════════════
def voice_loop():
    """The wake-word + ReAct conversational loop. Runs in its own thread."""
    log("")
    log("  ╔══════════════════════════════════════════════════════╗")
    log("  ║     J.A.R.V.I.S.  —  Phase 4                         ║")
    log("  ║     Tool-Use · Vision · Browser-Use · ReAct · Tray   ║")
    log("  ║     Say 'Jarvis' to activate                         ║")
    log("  ╚══════════════════════════════════════════════════════╝")
    log("")

    init_speech()
    threading.Thread(target=init_memory, daemon=True).start()

    threading.Thread(target=lambda: [
        remember("Mr. Stark lives in Greater Noida, India"),
        remember("Mr. Stark is building JARVIS, a personal AI assistant"),
        remember("Mr. Stark uses Python 3.11, Groq API, VS Code, and Google Cloud"),
        remember("Mr. Stark's goal is to become a top AI developer and freelancer"),
        remember("Mr. Stark works on multi-agent AI systems with CrewAI and Google ADK"),
        remember("Mr. Stark stays up late coding and pushes himself very hard"),
    ], daemon=True).start()

    threading.Thread(target=scheduler_loop, daemon=True).start()
    threading.Thread(target=proactive_monitor, daemon=True).start()

    log("  Scheduler ................... ONLINE")
    log("  Proactive monitoring ........ ONLINE")
    log("  Tool-use brain .............. ONLINE")
    log("  Vision .......... " + ("ONLINE" if PIL_AVAILABLE else "OFFLINE (install Pillow)"))
    log("  Tray .................... " + ("ONLINE" if PYSTRAY_AVAILABLE and PIL_AVAILABLE else "OFFLINE"))
    log("  Browser automation .......... STANDBY (browser-use loads on first use)")
    log("  All systems ................. OPERATIONAL")
    log("")

    speak(greet())

    global active_until

    while not shutdown_event.is_set():
        now = time.time()
        in_followup = now < active_until

        if in_followup:
            set_status("listening")
            log("  [Follow-up mode — listening...]")
            text = listen_followup()
            if text is None:
                active_until = 0
                set_status("idle")
                log("  [Returning to standby]")
                continue
            command = text.strip()
            log(f"  You: {command}")
        else:
            set_status("idle")
            heard = listen_for_wake_word()
            if heard is None:
                continue
            if WAKE_WORD not in heard:
                continue
            set_status("listening")
            play_chime()
            command = heard.replace(WAKE_WORD, "").strip().strip(".,!? ")
            if len(command) < 3:
                speak("At your service, Mr. Stark.")
                command = listen_for_command()
                if not command:
                    continue
                log(f"  You: {command}")
            else:
                log(f"  You: {command}")

        # Shutdown phrases
        cmd_lower = command.lower()
        if any(w in cmd_lower for w in ["shutdown jarvis", "shut down jarvis",
                                         "power down", "exit jarvis",
                                         "goodbye jarvis", "go to sleep"]):
            speak("Powering down. It's been a pleasure, Mr. Stark. Good luck out there.")
            shutdown_event.set()
            try:
                if tray_icon:
                    tray_icon.stop()
            except Exception:
                pass
            break

        # Run through the ReAct tool-calling loop
        response = react_loop(command, speak_progress=True)
        if response:
            speak(response)

        active_until = time.time() + FOLLOWUP_WINDOW


def main():
    if TRAY_MODE and PYSTRAY_AVAILABLE and PIL_AVAILABLE:
        # Silent mode — no console window. Tray runs in main thread.
        install_silent_stdout()
        threading.Thread(target=voice_loop, daemon=True, name="VoiceLoop").start()
        run_tray()
    else:
        # Fall back to terminal mode
        voice_loop()


if __name__ == "__main__":
    main()
