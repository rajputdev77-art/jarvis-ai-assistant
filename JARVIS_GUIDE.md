# JARVIS — Your Complete Guide

Mr. Stark, this is the only document you need. Bookmark it.

---

## 1. WHERE EVERYTHING LIVES

| Thing | Exact path |
|------|------------|
| **Main folder** | `C:\Users\Dev\JARVIS\` |
| **Main script (the brain)** | `C:\Users\Dev\JARVIS\jarvis.py` |
| **HUD script (the visuals)** | `C:\Users\Dev\JARVIS\hud_arc.py` |
| **MCP server (for Cursor/Claude Desktop)** | `C:\Users\Dev\JARVIS\mcp_server.py` |
| **Personality config (edit me!)** | `C:\Users\Dev\JARVIS\personality.yaml` |
| **API keys + secrets** | `C:\Users\Dev\JARVIS\.env` |
| **Your project index (auto)** | `C:\Users\Dev\JARVIS\project_index.json` |
| **Runtime log (debug)** | `C:\Users\Dev\JARVIS\jarvis_runtime.log` |
| **Dynamic tools you/JARVIS wrote** | `C:\Users\Dev\JARVIS\dynamic_tools.py` |
| **Python virtual environment** | `C:\Users\Dev\JARVIS\venv\` |
| **Auto-start script (runs on boot)** | `C:\Users\Dev\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\JARVIS.cmd` |
| **Gmail OAuth credentials (you download this)** | `C:\Users\Dev\JARVIS\gmail_credentials.json` |

---

## 2. KEYBOARD SHORTCUTS — MEMORISE THESE THREE

| Shortcut | What it does |
|----------|--------------|
| **Win + J** | Toggle HUD: hidden → compact → fullscreen → hidden |
| **Ctrl + Shift + S** | **STOP JARVIS speaking immediately.** Works anywhere. |
| **ESC** | Close fullscreen HUD back to compact |

You can also say **"stop", "shut up", "be quiet", "jarvis stop", "enough"** to interrupt.

---

## 3. HOW TO START / STOP / RESTART

### Start manually (if it's not running)
Double-click: `C:\Users\Dev\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\JARVIS.cmd`

Or in PowerShell:
```
C:\Users\Dev\JARVIS\venv\Scripts\pythonw.exe C:\Users\Dev\JARVIS\jarvis.py
```

### Verify JARVIS is running
Open Task Manager → look for `pythonw.exe` using ~700 MB RAM.

### Stop JARVIS
- Say **"shutdown jarvis"** or **"goodbye jarvis"**
- OR right-click the tray icon → **Shutdown JARVIS**
- OR in PowerShell: `taskkill /F /IM pythonw.exe` (kills ALL pythonw, careful)

### Restart
Stop, then re-run the cmd above. Or right-click tray → **Restart JARVIS**.

### Auto-start on boot
**Already configured.** Every time you turn on your laptop and log in, JARVIS launches silently after a 12-second delay. No action needed from you.

---

## 4. HOW TO SEE THE DASHBOARD

The dashboard is **HIDDEN by default**. You summon it three ways:

1. **Press `Win + J`** anywhere on your screen
2. **Click the JARVIS tray icon** (the colored dot in your taskbar, bottom-right corner near the clock — you may need to click the ∧ arrow to find it in Windows 11's hidden overflow)
3. **Right-click tray icon** → **Open HUD**

The dashboard has two modes:
- **Compact** — small floating widget top-right, draggable, won't block your screen
- **Fullscreen Mark VII** — Iron-Man-style takeover. Click ⛶ in compact, OR press Win+J twice. **Press ESC or click EXIT to leave fullscreen.**

If the HUD seems "lost" — press **Win+J**. It will come back.

---

## 5. SETUP STEPS (one-time, optional but powerful)

### A. Telegram bot (so you can text JARVIS from anywhere)
1. On your phone, open Telegram, search `@BotFather`
2. Send `/newbot`, follow prompts, get a token like `8123456789:AAH...`
3. Open `C:\Users\Dev\JARVIS\.env` in Notepad
4. Add a line: `TELEGRAM_BOT_TOKEN=8123456789:AAH...`
5. Save. Restart JARVIS.
6. Send any message to your bot in Telegram once (so JARVIS learns your chat ID)
7. Now you can text JARVIS commands — "run a system scan", "what's on my screen" — from anywhere, and it replies.

### B. Gmail API (so JARVIS reads/sends email fast)
1. Go to https://console.cloud.google.com/apis/credentials
2. Create OAuth client ID → Desktop app → download the JSON
3. Save as: `C:\Users\Dev\JARVIS\gmail_credentials.json`
4. First `gmail_read` call from JARVIS will pop a browser asking for permission. Click allow. Token cached forever after.

### C. Sarvam multi-lingual voice (Hindi, Tamil, Telugu, etc.)
1. Sign up at https://dashboard.sarvam.ai (free tier)
2. Get your API key (`sk_xxxx...`)
3. In `.env` add: `SARVAM_API_KEY=sk_xxxx`
4. Edit `personality.yaml`:
   ```yaml
   voice:
     provider: "sarvam"
     sarvam_lang: "hi-IN"      # or ta-IN, te-IN, bn-IN, etc.
     sarvam_voice: "meera"
   ```
5. JARVIS now speaks Hindi (or whichever language). Auto-reloads in 5 seconds.

### D. JARVIS as an MCP server for Cursor
1. Open Cursor → Settings → MCP → "Add MCP Server"
2. Use this config:
   ```json
   {
     "mcpServers": {
       "jarvis": {
         "command": "C:\\Users\\Dev\\JARVIS\\venv\\Scripts\\python.exe",
         "args": ["C:\\Users\\Dev\\JARVIS\\mcp_server.py"]
       }
     }
   }
   ```
3. Restart Cursor. Now `@jarvis` in Cursor chat lets you call any of 26 JARVIS tools.

---

## 6. WHAT JARVIS CAN DO (capabilities, honestly)

### Voice commands — say "Jarvis" then…
- **System control:** "open Bluetooth / WiFi / display settings", "lock screen", "volume up/down/mute", "next track", "shutdown" (asks confirm)
- **App control:** "open Cursor", "open Chrome", "open my Trading project", "open WhatsApp", "close Spotify"
- **Files:** "find files matching *.py under Desktop", "read this file", "what's in my Downloads folder"
- **Web:** "search for X on google", "open YouTube", "get top news", "weather in Mumbai"
- **Vision:** "what's on my screen", "what's wrong with this code", "read this"
- **Email (after Gmail setup):** "read my unread emails", "send an email to X saying Y"
- **Telegram (after setup):** "send Telegram saying X" — JARVIS messages your chat
- **Projects:** "what are my projects", "what am I working on", "open my X project"
- **System status:** "how's the battery", "what's CPU usage", "is python running", "list my open windows"
- **Shell:** "run X command" — JARVIS executes PowerShell
- **Multi-step:** "find 3 AI jobs and email me the best one" — Avengers crew handles parallel tasks
- **Conversation:** "explain quantum computing", "what should I do today", "you're being annoying" — JARVIS just chats
- **Custom commands (edit personality.yaml):** "deploy my portfolio", "morning routine", "lock screen", or any trigger you define

### Ambient (automatic, no command needed)
- **Predictive observer:** Every 5 minutes, JARVIS looks at your screen. If it sees an error, low battery, calendar reminder, or something noteworthy, it speaks up. Otherwise silent.
- **Clipboard watcher:** Detects when you copy stack traces, errors. Shows in HUD log.
- **Window focus watcher:** Tracks which app you're in for context.
- **Late-night nudge:** After 2 AM, JARVIS suggests rest (once per night).
- **Low-battery nudge:** Below 15% on battery, JARVIS warns you.
- **Project index:** Every 30 minutes, re-scans your Desktop/Documents/Projects for new work. Knows what you're working on.

### What JARVIS CAN'T do (honest)
- **It can't see physical things** — no camera analysis of you/room
- **It can't control your phone directly** (use Telegram instead)
- **It can't really hold a long memory of an ongoing task across days** — Mem0 stores facts, but not deep state
- **It can't guarantee 100% voice recognition** — Google Speech is what we use (free). Background noise, accents, fast speech all reduce accuracy
- **It can't always interrupt itself mid-sentence** before Phase 8 — now you have **Ctrl+Shift+S** which works instantly
- **It can't write production code that runs perfectly first time** — it's an assistant, not an oracle
- **It can't access paid APIs** — no Anthropic API, no OpenAI paid models, no ElevenLabs voice
- **It can't reach networks behind firewalls** unless you tunnel them via `expose_to_internet`
- **WhatsApp Web is unreliable** — Meta breaks it weekly. Use Telegram instead. JARVIS will say so.

### Brain models JARVIS uses (with failover)
1. Groq `llama-3.3-70b-versatile` (primary)
2. Groq `llama-4-scout-17b` (failover 1)
3. Groq `llama-4-maverick-17b` (failover 2)
4. Groq `qwen3-32b` (failover 3)
5. Groq `deepseek-r1-distill-llama-70b` (failover 4)
6. **Ollama `qwen2.5-coder:14b` on your laptop** (unlimited, no quotas)

When Groq is rate-limited, JARVIS silently switches. You see no errors.

---

## 7. CONFIGURE / CUSTOMIZE — `personality.yaml`

Open `C:\Users\Dev\JARVIS\personality.yaml` in Notepad. Edit anything. Save. **JARVIS reloads it within 5 seconds — no restart needed.**

### Change how JARVIS addresses you
```yaml
address:
  primary: "Mr. Stark"   # ← change this
  secondary: "boss"      # ← or this
```

### Change voice
```yaml
voice:
  edge_voice: "en-GB-RyanNeural"   # British male (default)
  # Other good options:
  # "en-GB-SoniaNeural"  British female
  # "en-US-GuyNeural"     American male
  # "en-IN-PrabhatNeural" Indian male
  # "en-IN-NeerjaNeural"  Indian female
```

### Change behavior limits
```yaml
behavior:
  max_sentences_spoken: 2   # ← raise to allow longer replies
  formality: "casual"        # ← or "high"
  wit: "high"                # ← off / low / medium / high
  pushback: false            # ← stops JARVIS from disagreeing with you
  proactive: false           # ← disables predictive observer speaking up
```

### Change response templates
```yaml
responses:
  greeting_morning: "Rise and shine, sir. The world awaits."   # ← edit
  acknowledge:      "Got it."                                   # ← edit
  unknown:          "Sorry boss, didn't catch that."            # ← edit
```

### Add custom voice commands
```yaml
custom_commands:
  - trigger: "start my workday"
    action: "shell"
    args: "start chrome github.com gmail.com && code C:\\Users\\Dev\\Desktop\\Trading"
    reply: "Workday mode engaged, sir."

  - trigger: "open my notes"
    action: "open"
    args: "C:\\Users\\Dev\\Documents\\notes.md"
    reply: "Notes opening."
```

Save the file → say the trigger → JARVIS runs it.

---

## 8. TROUBLESHOOTING

### "JARVIS doesn't respond to my voice"
- Check microphone is working in Windows Sound Settings
- Check `pythonw.exe` is in Task Manager (~700 MB)
- Restart: kill pythonw, re-run `JARVIS.cmd`
- Background noise — try a quieter room

### "JARVIS won't stop talking"
- **Press Ctrl+Shift+S** — instant stop, anywhere
- Say **"stop"** or **"shut up"** — also works
- Worst case: Task Manager → kill `pythonw.exe`

### "I can't find the HUD / it's lost"
- **Press Win+J** — brings it back
- If Win+J doesn't work, JARVIS isn't running. Start it via `JARVIS.cmd`

### "I can't see the tray icon"
- Windows 11 hides new tray icons by default
- Click the **∧** arrow next to your clock (bottom-right) to see hidden icons
- Drag the JARVIS icon out of the hidden area onto your visible tray
- OR Settings → Personalization → Taskbar → "Other system tray icons" → toggle JARVIS to On

### "JARVIS is saying I rate-limited / 429 / error code"
- It shouldn't be visible to you anymore — Phase 5.1 added auto-failover
- If you see it, check `jarvis_runtime.log` and tell me

### "I want JARVIS to NOT auto-start on boot"
- Delete: `C:\Users\Dev\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\JARVIS.cmd`

### "Voice quality is bad / sounds robotic"
- Default edge-tts voice is good but not perfect
- Try other voices (see section 7)
- For movie-quality voice, you'd need ElevenLabs ($5/mo — not free)

---

## 9. THE FILE TREE

```
C:\Users\Dev\JARVIS\
├── jarvis.py                  ← The brain. Voice loop, tools, agents.
├── hud_arc.py                 ← The dashboard (PyQt6, hidden by default).
├── mcp_server.py              ← MCP server for Cursor/Claude Desktop.
├── personality.yaml           ← EDIT THIS to change JARVIS's behavior.
├── dynamic_tools.py           ← Tools JARVIS wrote for itself at runtime.
├── .env                       ← Secrets (Groq key, Telegram token, Sarvam key).
├── project_index.json         ← Auto-scanned list of your projects.
├── jarvis_runtime.log         ← Append-only log (check when debugging).
├── hud_events.jsonl           ← Event stream the HUD reads.
├── hud_stderr.log             ← HUD crashes go here.
├── cloudflared_*.log          ← Tunnel logs.
├── gmail_credentials.json     ← OAuth (you download, see section 5B).
├── gmail_token.json           ← Auto-cached after first OAuth.
├── requirements.txt           ← All Python deps.
├── browser_data\              ← Persistent Chromium profile.
├── memory_db\                 ← Qdrant vector store for long-term memory.
└── venv\                      ← Python virtualenv.
```

---

## 10. THE FIVE LAWS OF JARVIS

JARVIS operates under these rules (in the system prompt):

1. **TRUTH OVER PERFORMANCE** — Never invents. Only reports what tools actually returned.
2. **VERIFY BEFORE CLAIMING** — Calls `verify_*` tools after world-affecting actions.
3. **CHAIN, DON'T GIVE UP** — Up to 12 iterations to solve a task.
4. **DELEGATE WHEN HELPFUL** — `dispatch_crew` for multi-domain jobs.
5. **BREVITY** — Max 2 sentences spoken aloud. Detail goes to the HUD.

Edit these by changing `SYSTEM_PROMPT` in `jarvis.py` (advanced) or, easier, lean on `personality.yaml`.

---

*All systems nominal, sir.*
