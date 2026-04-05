# JARVIS — Development Notes

## Architecture & Thinking

### Why This Stack?
The entire goal was: **build a fully functional voice AI assistant for $0/month.**

| Component | Choice | Why |
|-----------|--------|-----|
| AI Brain | Groq API (llama-3.3-70b-versatile) | Free tier, fast inference, 70B parameter model |
| Voice Input | SpeechRecognition + Google Speech API | Free, reliable, no API key needed |
| Voice Output | edge-tts + pygame | Free Microsoft TTS, natural British voice |
| App Control | subprocess + webbrowser | Built-in Python, no extra dependencies |
| Intent Classification | Second Groq call (zero-shot) | No training data needed, handles edge cases |

### Why NOT These Alternatives?
- **pyttsx3** — Breaks on long responses, robotic voice. edge-tts is far superior.
- **OpenAI Whisper** — Great but slower, needs GPU for real-time. Google Speech API is instant.
- **llama3-8b-8192** — Retired on Groq. Use llama-3.3-70b-versatile.
- **Python 3.14** — Breaks PyAudio and other C-extension libraries. Stick with 3.11.

### How Intent Classification Works
Instead of brittle `if "open" in text` keyword matching, JARVIS uses a two-step AI approach:

1. **classify_intent()** — Sends the voice input to Groq with a classification prompt. Returns structured `INTENT: <type>` and `QUERY: <data>`.
2. **execute_action()** — Routes the classified intent to the right handler (play music, open app, search web, etc.)

This means JARVIS understands natural variations:
- "put on some Eminem" → `play_music: Eminem`
- "fire up Chrome" → `open_app: chrome`
- "what's the weather like" → `conversation`

### Wake Word System
JARVIS uses a passive/active listening model:
1. **Passive mode** — Always listening (no timeout), waiting for "Jarvis"
2. **Active mode** — After wake word detected, listens with 10s timeout for the full command
3. **One-breath mode** — If user says "Jarvis open Chrome" in one sentence, skips the "Yes, Mr. Stark?" prompt

### Session Memory
- Last 20 messages are kept in context (prevents token overflow)
- System prompt with permanent memory is prepended to every request
- No database needed yet — conversation resets on restart

## Phase History

### Phase 1 — Voice + AI Brain
- Set up venv with Python 3.11
- Connected Groq API
- Added SpeechRecognition for voice input
- Added edge-tts + pygame for voice output
- Basic listen → think → speak loop

### Phase 2 — Permanent Memory
- Injected full identity into system prompt
- Time-based greetings
- Session conversation memory

### Phase 3 — Computer Control + Intent Classification
- App launcher (Chrome, VS Code, Spotify, etc.)
- Website opener (YouTube, Gmail, GitHub, etc.)
- YouTube music search and direct play
- AI-powered intent classification (replaced keyword matching)
- Task scheduler (in X minutes / at X:XX AM)
- Web search via Google

## Planned Phases

### Phase 4 — Google Calendar Integration
- Read/create/manage calendar events by voice
- OAuth 2.0 with Google Calendar API

### Phase 5 — Browser Automation
- Playwright-based browser control
- Search, fill forms, complete web tasks

### Phase 6 — Expanded Capabilities
- Reminders & alarms
- WhatsApp messages via web automation
- Email reading & summarization
- File creation by voice

### Phase 7 — Full Agent Mode
- Multi-step autonomous task completion
- CrewAI for multi-agent reasoning
- Job applications, follow-up emails, LinkedIn posts

## Key Lessons Learned
1. Always activate venv before running: `venv\Scripts\activate`
2. Command handler must run BEFORE AI brain in main loop
3. edge-tts requires async — use `asyncio.run()` wrapper
4. PyAudio needs specific Python version (3.11) — check compatibility
5. Groq free tier has rate limits — keep classify_intent calls minimal (max_tokens=30)
