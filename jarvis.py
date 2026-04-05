"""
JARVIS — Personal AI Assistant
Voice-activated AI assistant built in Python. Free stack. No paid subscriptions.
Hears your voice, thinks using Groq AI, speaks back in a natural British voice,
and can control your computer by voice.

Author: Dev
Phase: 3 Complete (Voice + AI + Memory + Computer Control + Intent Classification)
"""

import speech_recognition as sr
import edge_tts
import asyncio
import pygame
import os
import re
import tempfile
import subprocess
import webbrowser
import urllib.parse
import urllib.request
import threading
import time
from datetime import datetime, timedelta
from groq import Groq
from dotenv import load_dotenv

# ── Load Environment Variables ─────────────────────────────
load_dotenv()

# ── Configuration ──────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY not found. Create a .env file with: GROQ_API_KEY=your_key_here\n"
        "Get a free key at https://console.groq.com"
    )

JARVIS_NAME = "Jarvis"
VOICE = "en-GB-RyanNeural"
WAKE_WORD = "jarvis"

# ── App Map (Windows paths — customize for your system) ────
APPS = {
    "chrome":         r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "vs code":        r"C:\Users\Dev\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "vscode":         r"C:\Users\Dev\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "code":           r"C:\Users\Dev\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "notepad":        "notepad.exe",
    "calculator":     "calc.exe",
    "file explorer":  "explorer.exe",
    "explorer":       "explorer.exe",
    "task manager":   "taskmgr.exe",
    "spotify":        r"C:\Users\Dev\AppData\Roaming\Spotify\Spotify.exe",
    "word":           r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    "excel":          r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    "terminal":       "cmd.exe",
    "command prompt":  "cmd.exe",
}

# ── Website Map ────────────────────────────────────────────
WEBSITES = {
    "youtube":      "https://youtube.com",
    "google":       "https://google.com",
    "gmail":        "https://mail.google.com",
    "github":       "https://github.com",
    "linkedin":     "https://linkedin.com",
    "claude":       "https://claude.ai",
    "groq":         "https://console.groq.com",
    "google cloud": "https://console.cloud.google.com",
    "chatgpt":      "https://chat.openai.com",
    "twitter":      "https://twitter.com",
    "instagram":    "https://instagram.com",
    "whatsapp":     "https://web.whatsapp.com",
}

# ── Permanent Memory (System Prompt) ──────────────────────
PERMANENT_MEMORY = """You are JARVIS — a personal AI assistant, inspired by Iron Man's JARVIS.

RULES FOR YOU:
- Address the user as "Mr. Stark"
- Be concise. 1-2 sentences max unless asked for detail
- Do NOT mention the time unless specifically asked "what time is it"
- Do NOT pretend to perform actions. You CANNOT play music, open apps, or browse the web.
  The system handles those actions separately. You only handle conversation and questions.
- If asked to do something you can't do (like play a song, open an app),
  say "I'll handle that for you, Mr. Stark" — the system takes care of execution.
- Keep the user focused and motivated
- Reference their goals when relevant
"""

# ── Session Memory ─────────────────────────────────────────
session_memory = []

# ── Scheduled Tasks ────────────────────────────────────────
scheduled_tasks = []
scheduler_lock = threading.Lock()


def add_scheduled_task(run_at, description, action_fn):
    """Add a task to run at a specific time."""
    with scheduler_lock:
        scheduled_tasks.append({
            "run_at": run_at,
            "description": description,
            "action": action_fn,
            "done": False,
        })


def scheduler_thread(speak_fn):
    """Background thread that checks and runs scheduled tasks."""
    while True:
        now = datetime.now()
        with scheduler_lock:
            for task in scheduled_tasks:
                if not task["done"] and now >= task["run_at"]:
                    task["done"] = True
                    print(f"\nJARVIS: Running scheduled task — {task['description']}")
                    try:
                        task["action"]()
                        speak_fn(f"Mr. Stark, scheduled task complete: {task['description']}")
                    except Exception as e:
                        print(f"JARVIS: Task failed — {e}")
        time.sleep(30)


# ── AI Brain ──────────────────────────────────────────────
client = Groq(api_key=GROQ_API_KEY)


def classify_intent(user_input):
    """Use AI to understand what the user wants — no fragile keyword matching."""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "system",
                "content": """Classify the user's voice command. Reply in EXACTLY this format — two lines, nothing else:

INTENT: <intent>
QUERY: <extracted data>

Possible intents:
- play_music — wants to hear a song, artist, album, or music video. QUERY = just the song/artist name, cleaned up.
- open_website — wants to open a website. QUERY = website name (e.g. "youtube", "gmail", "github").
- open_app — wants to launch an application. QUERY = app name (e.g. "chrome", "vs code", "spotify").
- search_web — wants to google/search something. QUERY = the search terms.
- schedule — wants to do something at a specific time or in X minutes. QUERY = the full original command.
- get_time — asking what time it is. QUERY = none.
- get_date — asking what date/day it is. QUERY = none.
- conversation — a question, chat, or anything else. QUERY = none.

Examples:
"stan by eminem" → INTENT: play_music  QUERY: Stan by Eminem
"iris goo goo dolls" → INTENT: play_music  QUERY: Iris by Goo Goo Dolls
"play some lofi" → INTENT: play_music  QUERY: lofi
"open gmail" → INTENT: open_website  QUERY: gmail
"launch vs code" → INTENT: open_app  QUERY: vs code
"what's the capital of France" → INTENT: conversation  QUERY: none
"at 5:30 AM open chrome" → INTENT: schedule  QUERY: at 5:30 AM open chrome
"search for python tutorials" → INTENT: search_web  QUERY: python tutorials"""
            }, {
                "role": "user",
                "content": user_input
            }],
            max_tokens=30,
            temperature=0
        )
        result = response.choices[0].message.content.strip()
        intent_match = re.search(r'INTENT:\s*(\S+)', result)
        query_match = re.search(r'QUERY:\s*(.+)', result)
        intent = intent_match.group(1) if intent_match else "conversation"
        query = query_match.group(1).strip() if query_match else ""
        if query.lower() == "none":
            query = ""
        return intent, query
    except Exception:
        return "conversation", ""


def ask_jarvis(user_input):
    """Send a message to the AI brain and get a response."""
    session_memory.append({"role": "user", "content": user_input})
    messages = [{"role": "system", "content": PERMANENT_MEMORY}] + session_memory[-20:]
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages
    )
    reply = response.choices[0].message.content
    session_memory.append({"role": "assistant", "content": reply})
    return reply


# ── YouTube Direct Play ────────────────────────────────────
def get_youtube_video_url(query):
    """Fetch the first video URL from YouTube search results."""
    try:
        search_url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
        req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=8).read().decode("utf-8")
        video_ids = re.findall(r"watch\?v=([a-zA-Z0-9_-]{11})", html)
        if video_ids:
            return f"https://www.youtube.com/watch?v={video_ids[0]}"
    except Exception:
        pass
    return f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"


# ── Schedule Parser ────────────────────────────────────────
def parse_and_schedule(text):
    """Parse 'at HH:MM AM/PM <cmd>' or 'in X minutes <cmd>' and schedule it."""
    at_match = re.search(r'at\s+(\d{1,2})[:\s](\d{2})\s*(am|pm)\s+(.*)', text, re.IGNORECASE)
    if at_match:
        hour, minute = int(at_match.group(1)), int(at_match.group(2))
        ampm, cmd_text = at_match.group(3).lower(), at_match.group(4).strip()
        if ampm == "pm" and hour != 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
        now = datetime.now()
        run_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if run_at <= now:
            run_at += timedelta(days=1)
        add_scheduled_task(run_at, cmd_text, lambda c=cmd_text: execute_action(*classify_intent(c), c))
        return f"Got it, Mr. Stark. I'll {cmd_text} at {run_at.strftime('%I:%M %p')}."

    in_match = re.search(r'in\s+(\d+)\s*(minute|minutes|min|hour|hours|hr)\s+(.*)', text, re.IGNORECASE)
    if in_match:
        amount = int(in_match.group(1))
        unit = in_match.group(2).lower()
        cmd_text = in_match.group(3).strip()
        delta = timedelta(hours=amount) if "hour" in unit or "hr" in unit else timedelta(minutes=amount)
        run_at = datetime.now() + delta
        add_scheduled_task(run_at, cmd_text, lambda c=cmd_text: execute_action(*classify_intent(c), c))
        return f"Got it, Mr. Stark. I'll {cmd_text} in {amount} {unit}."

    return None


# ── Action Executor ────────────────────────────────────────
def execute_action(intent, query, original_input):
    """Execute an action based on classified intent. Returns a spoken response."""

    if intent == "play_music":
        if not query:
            query = original_input
        url = get_youtube_video_url(query)
        webbrowser.open(url)
        return f"Playing {query} now, Mr. Stark."

    elif intent == "open_website":
        q = query.lower()
        for site, url in WEBSITES.items():
            if site in q or q in site:
                webbrowser.open(url)
                return f"Opening {site}, Mr. Stark."
        webbrowser.open(f"https://{query}.com")
        return f"Opening {query}, Mr. Stark."

    elif intent == "open_app":
        q = query.lower()
        for app, path in APPS.items():
            if app in q or q in app:
                try:
                    subprocess.Popen(path)
                    return f"Launching {app}, Mr. Stark."
                except FileNotFoundError:
                    return f"Can't find {app} at the expected path."
        return f"I don't know where {query} is installed, Mr. Stark."

    elif intent == "search_web":
        if query:
            url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            webbrowser.open(url)
            return f"Here are the results for {query}."
        return None

    elif intent == "schedule":
        result = parse_and_schedule(original_input.lower())
        if result:
            return result
        return "I couldn't understand the time. Try saying 'at 5:30 AM' or 'in 30 minutes'."

    elif intent == "get_time":
        return f"It's {datetime.now().strftime('%I:%M %p')}, Mr. Stark."

    elif intent == "get_date":
        return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}."

    elif intent == "conversation":
        return ask_jarvis(original_input)

    return ask_jarvis(original_input)


# ── Voice Output (edge-tts + pygame) ──────────────────────
pygame.mixer.init()


async def speak_async(text):
    """Convert text to speech using edge-tts and play with pygame."""
    print(f"\n{JARVIS_NAME}: {text}\n")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        tmp_path = f.name
    communicator = edge_tts.Communicate(text, VOICE)
    await communicator.save(tmp_path)
    pygame.mixer.music.load(tmp_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.1)
    pygame.mixer.music.unload()
    try:
        os.remove(tmp_path)
    except OSError:
        pass


def speak(text):
    """Synchronous wrapper for speak_async."""
    asyncio.run(speak_async(text))


# ── Voice Input ────────────────────────────────────────────
recognizer = sr.Recognizer()


def listen_passively():
    """Always-on listener — waits for wake word. No timeout, patient."""
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=None, phrase_time_limit=12)
            text = recognizer.recognize_google(audio).lower()
            return text
    except (sr.UnknownValueError, sr.RequestError, OSError):
        return None


def listen_command():
    """Active listener after wake word — longer patience for full commands."""
    try:
        with sr.Microphone() as source:
            print("Listening for command...")
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=25)
            text = recognizer.recognize_google(audio)
            print(f"You: {text}")
            return text
    except sr.WaitTimeoutError:
        return None
    except (sr.UnknownValueError, sr.RequestError, OSError):
        return None


# ── Greeting ───────────────────────────────────────────────
def get_greeting():
    """Generate a time-appropriate greeting."""
    hour = datetime.now().hour
    if hour < 12:
        period = "Good morning"
    elif hour < 17:
        period = "Good afternoon"
    else:
        period = "Good evening"
    return f"{period}, Mr. Stark. JARVIS is online and fully operational. Say my name when you need me."


# ── Main Loop ──────────────────────────────────────────────
def main():
    print("=" * 50)
    print("  JARVIS — Personal AI Assistant")
    print("  Say 'Jarvis' to wake me up")
    print("  Say 'Jarvis shutdown' to quit")
    print("=" * 50)

    # Start scheduler in background
    t = threading.Thread(target=scheduler_thread, args=(speak,), daemon=True)
    t.start()

    speak(get_greeting())

    while True:
        heard = listen_passively()
        if heard is None:
            continue

        if WAKE_WORD not in heard:
            continue

        # Extract anything said after "jarvis"
        command = heard.replace(WAKE_WORD, "").strip()

        if len(command) < 3:
            speak("Yes, Mr. Stark?")
            command_input = listen_command()
            if command_input is None:
                continue
        else:
            command_input = command
            print(f"You: {command_input}")

        # Shutdown check
        if any(w in command_input.lower() for w in ["shutdown", "exit", "goodbye", "go to sleep"]):
            speak("Shutting down. Good luck, Mr. Stark.")
            break

        # Classify intent with AI, then execute
        print("JARVIS: Processing...")
        intent, query = classify_intent(command_input)
        print(f"  → Intent: {intent} | Query: {query}")
        response = execute_action(intent, query, command_input)
        speak(response)


if __name__ == "__main__":
    main()
