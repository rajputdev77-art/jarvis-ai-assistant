# JARVIS — Personal AI Assistant

A fully voice-activated personal AI assistant built in Python. Inspired by Iron Man's JARVIS. 100% free stack — no paid subscriptions, no cloud costs.

JARVIS hears your voice, thinks using a 70-billion parameter AI model, speaks back in a natural British accent, and can control your computer entirely by voice.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![Groq](https://img.shields.io/badge/AI-Groq%20API-orange)
![Platform](https://img.shields.io/badge/Platform-Windows%2011-0078D6?logo=windows)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Phase%203%20Complete-brightgreen)

---

## The Problem It Solves

Most AI assistants (Siri, Alexa, Google) are locked ecosystems — you can't customize them, they don't know your personal context, and they cost money for advanced features. JARVIS is different:

- **Fully customizable** — you control every behavior, every response
- **Knows you personally** — your name, goals, projects, context is baked into its memory
- **Controls your PC** — opens apps, websites, plays music, all by voice
- **Completely free** — Groq API free tier, Microsoft edge-tts, Google Speech API
- **Runs locally** — your data stays on your machine

---

## Why It Matters

This isn't just a demo — it's a working personal assistant that runs on your desktop every day. It proves that with the right free tools, anyone can build their own AI assistant that rivals commercial products.

If you're a developer learning AI, this is a complete reference project showing:
- How to integrate LLM APIs (Groq) into real applications
- Voice input/output pipeline in Python
- AI-powered intent classification (no hardcoded rules)
- System architecture for extensible voice assistants

---

## How It Works (Step-by-Step)

### The Main Loop
```
You speak → Microphone captures audio → Google Speech API converts to text
     ↓
Wake word "Jarvis" detected?
     ↓ Yes
AI classifies your intent (play music? open app? question? schedule task?)
     ↓
Action executed (open Chrome, play YouTube, search Google, etc.)
     ↓
Response generated → edge-tts converts to British voice → Speaker plays audio
     ↓
Back to listening...
```

### Detailed Flow

1. **Passive Listening** — JARVIS runs a continuous microphone listener, waiting for the wake word "Jarvis"
2. **Wake Word Detection** — When "Jarvis" is heard, it either:
   - Extracts the command if said in one breath ("Jarvis open Chrome")
   - Responds "Yes, Mr. Stark?" and listens for the full command
3. **Intent Classification** — Your command is sent to Groq AI (llama-3.3-70b-versatile) which classifies it into one of 8 intents: `play_music`, `open_website`, `open_app`, `search_web`, `schedule`, `get_time`, `get_date`, or `conversation`
4. **Action Execution** — Based on intent:
   - **Music** → Searches YouTube, opens the first video directly
   - **Website** → Opens from a configurable website map
   - **App** → Launches from a configurable app map
   - **Search** → Opens Google with your query
   - **Schedule** → Schedules a task for later ("at 5:30 AM open Chrome")
   - **Time/Date** → Responds instantly (no AI call needed)
   - **Conversation** → Sends to AI brain with full session memory
5. **Voice Response** — The response is converted to speech using Microsoft's edge-tts (British male voice, en-GB-RyanNeural) and played through pygame

---

## Tech Stack

| Component | Technology | Why This Choice |
|-----------|-----------|-----------------|
| **Language** | Python 3.11 | Stable, huge ecosystem, compatible with all libraries |
| **AI Brain** | [Groq API](https://console.groq.com) — llama-3.3-70b-versatile | Free tier, blazing fast inference, 70B parameter model |
| **Voice Input** | SpeechRecognition + PyAudio + Google Speech API | Free, accurate, no API key required |
| **Voice Output** | [edge-tts](https://pypi.org/project/edge-tts/) + pygame | Free Microsoft neural TTS, natural-sounding British voice |
| **App Control** | subprocess + webbrowser (built-in Python) | Zero dependencies, works on Windows |
| **Intent Engine** | Zero-shot LLM classification via Groq | No training data needed, handles natural language variations |

**Total monthly cost: $0**

---

## Features

### Currently Working (Phase 1-3)
- Wake word activation ("Jarvis")
- Natural British male voice (en-GB-RyanNeural)
- AI-powered conversations (remembers full session context)
- Open any app by voice (Chrome, VS Code, Spotify, Notepad, etc.)
- Open any website by voice (YouTube, Gmail, GitHub, LinkedIn, etc.)
- Play music by voice (searches and plays YouTube directly)
- Google search by voice
- Tell time and date
- Schedule tasks ("at 5:30 AM open Chrome", "in 30 minutes remind me")
- Intelligent intent classification (no brittle keyword matching)
- Session memory (remembers conversation within each run)

### Planned Features
- **Phase 4:** Google Calendar integration (read/create events by voice)
- **Phase 5:** Browser automation with Playwright (fill forms, complete web tasks)
- **Phase 6:** WhatsApp messages, email summaries, reminders, file creation
- **Phase 7:** Full agent mode — multi-step autonomous tasks (apply to jobs, send emails, post on LinkedIn)

---

## Setup Instructions

### Prerequisites
- **Windows 10/11**
- **Python 3.11** installed ([download here](https://www.python.org/downloads/release/python-3110/))
- **A microphone** (built-in or external)
- **A Groq API key** (free — [get one here](https://console.groq.com))

### Step 1: Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/jarvis-ai-assistant.git
cd jarvis-ai-assistant
```

### Step 2: Create a Virtual Environment
```bash
py -3.11 -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

> **Note:** If PyAudio fails to install, download the `.whl` file from [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio) and install manually:
> ```bash
> pip install PyAudio‑0.2.14‑cp311‑cp311‑win_amd64.whl
> ```

### Step 4: Set Up Your API Key
Create a `.env` file in the project root:
```bash
GROQ_API_KEY=your_groq_api_key_here
```
> Get your free key at [console.groq.com](https://console.groq.com)

### Step 5: Run JARVIS
```bash
python jarvis.py
```

JARVIS will greet you and start listening. Say **"Jarvis"** to wake it up.

---

## Example Use Cases

```
You: "Jarvis"
JARVIS: "Yes, Mr. Stark?"

You: "Open YouTube"
JARVIS: "Opening YouTube, Mr. Stark."

You: "Play Bohemian Rhapsody"
JARVIS: "Playing Bohemian Rhapsody now, Mr. Stark."

You: "What time is it?"
JARVIS: "It's 03:45 PM, Mr. Stark."

You: "Search for Python machine learning tutorials"
JARVIS: "Here are the results for Python machine learning tutorials."

You: "At 6:00 PM open Gmail"
JARVIS: "Got it, Mr. Stark. I'll open Gmail at 06:00 PM."

You: "What is the difference between CrewAI and AutoGen?"
JARVIS: "CrewAI focuses on role-based agent orchestration..."

You: "Jarvis shutdown"
JARVIS: "Shutting down. Good luck, Mr. Stark."
```

---

## Project Structure

```
jarvis-ai-assistant/
├── jarvis.py           # Main application — voice loop, AI brain, command handler
├── requirements.txt    # Python dependencies
├── .env.example        # Template for API key configuration
├── .gitignore          # Files excluded from git (venv, .env, __pycache__)
├── notes.md            # Development notes, architecture decisions, lessons learned
├── LICENSE             # MIT License
└── README.md           # This file
```

---

## Customization

### Add Your Own Apps
Edit the `APPS` dictionary in `jarvis.py`:
```python
APPS = {
    "my app": r"C:\Path\To\YourApp.exe",
    # ...
}
```

### Add Your Own Websites
Edit the `WEBSITES` dictionary:
```python
WEBSITES = {
    "my site": "https://example.com",
    # ...
}
```

### Change the Voice
Replace the `VOICE` variable with any [edge-tts voice](https://github.com/rany2/edge-tts):
```python
VOICE = "en-US-GuyNeural"      # American male
VOICE = "en-GB-SoniaNeural"    # British female
VOICE = "en-AU-WilliamNeural"  # Australian male
```

### Personalize the Memory
Edit the `PERMANENT_MEMORY` string to add your own identity, goals, and context.

---

## Future Improvements

- [ ] **Google Calendar** — Read, create, and manage calendar events by voice
- [ ] **Browser Automation** — Use Playwright to complete web tasks autonomously
- [ ] **WhatsApp Integration** — Send messages via web automation
- [ ] **Email Summaries** — Read and summarize Gmail inbox
- [ ] **Persistent Memory** — Remember conversations across sessions (SQLite or JSON)
- [ ] **Multi-Agent Mode** — Use CrewAI for complex, multi-step autonomous tasks
- [ ] **Cross-Platform** — Support for macOS and Linux
- [ ] **GUI Dashboard** — Visual interface showing conversation history and status

---

## Technical Notes

- **Python 3.11 only** — Python 3.14 breaks PyAudio and other C-extension libraries
- **Groq model:** `llama-3.3-70b-versatile` (llama3-8b-8192 is retired)
- **Never use pyttsx3** — It fails on long responses. edge-tts + pygame is reliable
- **Intent classification uses a separate, minimal Groq call** (max_tokens=30) to keep it fast
- **Session memory is capped at 20 messages** to prevent token overflow

---

## Contributing

Contributions are welcome! If you'd like to improve JARVIS:

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Commit (`git commit -m "Add: your feature description"`)
5. Push (`git push origin feature/your-feature`)
6. Open a Pull Request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

**Built with passion by Dev** — turning raw ideas into working AI systems, one project at a time.
