<p align="center">
  <h1 align="center">🤖 ASTRO</h1>
  <p align="center"><strong>Your AI Voice Assistant</strong></p>
  <p align="center">Real-time voice conversations powered by Google Gemini</p>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#features">Features</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#docker">Docker</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/LiveKit-Agents-purple?style=flat-square" alt="LiveKit">
  <img src="https://img.shields.io/badge/Google-Gemini-orange?style=flat-square" alt="Gemini">
  <img src="https://img.shields.io/badge/License-Apache_2.0-green?style=flat-square" alt="License">
</p>

---

## What is ASTRO?

ASTRO is a voice-first AI assistant built on **LiveKit Agents** and **Google Gemini**. Talk naturally, and ASTRO responds with real-time speech — no typing required.

**Key capabilities:**
- 🎤 Natural voice conversations (speech-to-speech)
- 🧠 Remembers your preferences across sessions
- 🔧 Built-in tools: weather, web search, email, passwords
- 🔄 Smart API key rotation for extended usage

---

## Quick Start

### Prerequisites
- Python 3.10+
- [LiveKit Cloud account](https://livekit.io) (free)
- [Google API key](https://ai.google.dev)

### Setup

```bash
# Clone
git clone https://github.com/zohirben/ASTRO-Voice-AI.git
cd ASTRO-Voice-AI

# Environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API keys
```

### Run

```bash
python agent.py dev
```

Then open **[LiveKit Playground](https://agents-playground.livekit.io)** and start talking!

---

## Features

| Tool | What it does | Try saying |
|------|--------------|------------|
| 🌤️ Weather | Real-time weather data | "What's the weather in Tokyo?" |
| 🔍 Search | Web search via DuckDuckGo | "Search for latest AI news" |
| 📧 Email | Send emails via Gmail | "Email john@example.com about the meeting" |
| 🔐 Password | Generate secure passwords | "Generate a 16 character password" |
| 🌐 Network | Check connectivity | "Check network health" |
| 💤 Shutdown | Save memory & exit | "Shutdown yourself ASTRO" |

### Memory System

ASTRO remembers your conversations using **mem0 + ChromaDB**:
- Automatically extracts important information
- Persists across sessions
- Rotates through 5 API keys for extended quota

---

## Configuration

### Required Environment Variables

```bash
# LiveKit (get from livekit.io)
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_key
LIVEKIT_API_SECRET=your_secret

# Google Gemini (get from ai.google.dev)
GOOGLE_API_KEY=your_gemini_key
```

### Optional Configuration

```bash
# Memory API keys (for extended quota)
GOOGLE_API_MEMORY_KEY1=key1
GOOGLE_API_MEMORY_KEY2=key2
# ... up to 5 keys

# Email (for send_email tool)
GMAIL_USER=your@gmail.com
GMAIL_APP_PASSWORD=app_password

# Audio feedback
ENABLE_THINKING_AUDIO=true
```

---

## Docker

### Quick Start with Docker

```bash
# Build
docker build -t astro .

# Run
docker run --env-file .env -p 8080:8080 astro
```

### Docker Compose

```bash
docker-compose up
```

---

## Project Structure

```
ASTRO/
├── agent.py          # Main agent entry point
├── prompts.py        # Personality & instructions
├── tools/            # Function tools (weather, search, etc.)
├── memory/           # Memory management system
├── utils/            # Logging utilities
└── tests/            # Test suite
```

---

## Testing

```bash
pytest              # Run all tests
pytest -v           # Verbose output
pytest --cov        # With coverage
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection failed | Check LiveKit credentials in `.env` |
| Memory not saving | Say "shutdown yourself ASTRO" to persist |
| Email not working | Use Gmail app password, not regular password |
| Search timeout | Network issue — try "check network health" |

---

## License

Apache 2.0 — See [LICENSE](LICENSE)

---
probably am going to update this project later with more utilities and advanced technologies!
<p align="center">
  <strong>Built by <a href="https://github.com/zohirben">Zohir Ben-aissa</a></strong><br>
  Powered by LiveKit & Google Gemini
</p>
