# JARVIS Phase 5 — The Generalist

**Date:** 2026-04-26  •  **Owner:** Mr. Stark

JARVIS is no longer limited by hardcoded tools. It now has **shell execution**,
**filesystem control**, **window/keyboard control**, **clipboard**, **80 Windows
Settings panels**, **Gmail API**, **clipboard ambient watcher**, **self-extension**
(it can write its own new tools), and a **PyQt6 floating glass HUD** so Mr. Stark
can watch every thought in real time.

---

## The 34-tool generalist registry

| Category | Tools |
|----------|-------|
| **Shell** | `run_shell` (PowerShell/cmd, anything goes) |
| **Filesystem** | `read_file`, `write_file`, `list_dir`, `find_files` |
| **App / URI** | `open_app` (knows your apps + .exe paths + folders + files + URIs), `open_settings` (80 Windows panels), `open_website` |
| **Window control** | `list_windows`, `focus_window`, `send_keys` (full SendKeys syntax) |
| **Clipboard** | `clipboard_read`, `clipboard_write` |
| **Process / network** | `list_processes`, `kill_process`, `http_get` (great for "is n8n running?") |
| **Vision** | `take_screenshot`, `analyze_screen` |
| **Email / messaging** | `gmail_read` (Gmail API — fast), `gmail_send`, `send_whatsapp` (browser-use), `browser_action` (generic) |
| **Information** | `get_time`, `get_date`, `get_weather`, `get_news`, `system_status`, `briefing` |
| **System control** | `system_control` (volume/media/lock/sleep/restart/shutdown) |
| **Scheduling** | `schedule_command` |
| **Memory** | `remember_fact` |
| **Self-extension** | `write_tool`, `reload_tools` |
| **Safety** | `confirm_with_user` |

Plus: any function defined in `dynamic_tools.py` (which JARVIS itself can extend
at runtime via `write_tool`).

---

## What "the generalist" actually means

Before: 18 hardcoded intents → 20 typed tools. Anything unknown failed.
Now: shell + filesystem + window control = JARVIS can do **anything Windows
can do from a command line or UI**.

Real examples that now work:

| Mr. Stark says | JARVIS chains |
|---|---|
| "Open Bluetooth" | `open_settings("bluetooth")` — instant |
| "Open Cursor and load my X folder and run it" | `open_app("cursor", args="C:/path/to/X")` → focus → `send_keys("^`")` to open terminal → `send_keys("npm start{ENTER}")` |
| "Check if n8n is running" | `http_get("http://localhost:5678")` → parse → report |
| "Tell me when Claude Code's rate limit resets" | `focus_window("Claude")` → `analyze_screen("when does the limit reset?")` → speak the answer |
| "Read my unread emails" | `gmail_read(query="is:unread", count=5)` — 100ms, not 30 seconds |
| "Build me a tool to control my Spotify" | `write_tool(name="spotify_play", description="...", code="def spotify_play(query):\\n    ...")` → `reload_tools` → use it next request |
| "What's on my clipboard, and is it broken?" | `clipboard_read` → if it looks like a stack trace, `analyze_screen` for context |

---

## Safety: plan-confirm-execute

Three layers protect against destructive damage:

1. **Pattern guard in `run_shell`** — refuses commands matching `rm`, `del`, `format`, `shutdown`, `reg delete`, `taskkill *`, `git push --force`, etc., until JARVIS first calls `confirm_with_user`.
2. **`write_file` overwrite guard** — refuses overwriting files outside `C:\Users\Dev\JARVIS\` without confirmation.
3. **`confirm_with_user(plan)`** — JARVIS speaks the plan and waits for spoken "yes/yeah/go/do it/proceed". Anything else aborts.

Safe operations (open apps, read files, settings, clipboard reads, list windows) execute without confirmation — that was Mr. Stark's explicit ask.

---

## The HUD (`hud.py`)

A separate process — frameless, always-on-top, top-right of your primary screen,
460×540, draggable, collapsible. Renders:

- **Pulsing state dot**: idle (grey) → listening (green) → thinking (amber) → working (purple) → speaking (blue)
- **State label** (STANDBY / LISTENING / THINKING / EXECUTING / SPEAKING)
- **Current focus** strip — what JARVIS is doing right now
- **Live event stream** — every tool call, every result, every spoken line, in real time
- **— and ✕ buttons** — collapse to header only, or hide completely
- **Tray menu "Open HUD"** — re-launches it

Jarvis writes events to `hud_events.jsonl` (line-delimited JSON, one event per
line). The HUD tails this file every 150ms. No socket complexity, no IPC issues.

---

## Self-extension

`write_tool(name, description, code)` writes a Python function to
`dynamic_tools.py`, syntax-checks it, then `reload_tools` re-imports the file.
Every public function in that file becomes a callable tool, with its docstring as
the description and parameter names as the arg schema.

So if Mr. Stark says *"You should be able to summarise YouTube videos by URL"*,
JARVIS can write the function, save it, reload, and use it on the next request —
no human in the loop, no code editor, no restart.

---

## Installation

```powershell
cd C:\Users\Dev\JARVIS
.\venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

For Gmail API (optional but highly recommended — replaces slow browser-use email):
1. Go to <https://console.cloud.google.com/apis/credentials>
2. Create OAuth client ID → Desktop app
3. Download the JSON, save as `C:\Users\Dev\JARVIS\gmail_credentials.json`
4. First call to `gmail_read` will pop a browser for OAuth consent. After that, the token caches in `gmail_token.json`.

Without `gmail_credentials.json`, JARVIS will tell you it's not configured and you can fall back to browser-use.

## Launch

```powershell
python C:\Users\Dev\JARVIS\jarvis.py
```

Or double-click your existing launcher. Tray icon appears bottom-right; the HUD pops top-right automatically.

---

## Files

```
C:\Users\Dev\JARVIS\
├── jarvis.py              # Main agent (Phase 5)
├── hud.py                 # PyQt6 HUD (separate process)
├── dynamic_tools.py       # JARVIS-authored tools (auto-extends)
├── .env                   # GROQ_API_KEY (gitignored)
├── requirements.txt       # All deps
├── jarvis_runtime.log     # Append-only log (gitignored)
├── hud_events.jsonl       # HUD event stream (gitignored)
├── browser_data/          # Persistent Chromium profile
├── memory_db/             # Qdrant vector store for Mem0
├── gmail_credentials.json # OAuth client (you download this)
└── gmail_token.json       # OAuth token (auto-created)
```
