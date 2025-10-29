# 🤖 ASTRO - Advanced Voice AI Assistant

<div align="center">

![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)
![LiveKit](https://img.shields.io/badge/LiveKit-Agents-purple.svg)
![Google Gemini](https://img.shields.io/badge/Google-Gemini-orange.svg)
![Demo Version](https://img.shields.io/badge/version-Demo-orange.svg)

*An intelligent, voice-first AI assistant inspired by Iron Man's JARVIS*

**🚧 This is a DEMO version showcasing core capabilities. Far more advanced features are under active development in private repositories.**

[Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [Documentation](#-documentation)

</div>

---

## 🌟 Overview

**ASTRO** is a production-ready AI voice assistant built on the LiveKit Agents framework, featuring Google's Gemini Realtime Model for natural speech-to-speech interactions. With a sophisticated butler-like personality, intelligent memory management, and powerful tool capabilities, ASTRO delivers a seamless conversational AI experience.

### What Makes ASTRO Special?

- 🎤 **True Voice-First Design** - Real-time speech-to-speech using Gemini's state-of-the-art model
- 🧠 **Intelligent Memory System** - Persistent memory with automatic key rotation across multiple API quotas
- 🛠️ **Rich Tool Ecosystem** - Weather, web search, email, network diagnostics, secure password generation
- 🔄 **Smart API Key Rotation** - Automatically cycles through 5 API keys when quotas are exhausted
- 🎭 **Sophisticated Personality** - Professional butler persona with tasteful sarcasm
- 🔇 **Professional Audio Processing** - Built-in noise cancellation and background audio
- 🏗️ **Production Ready** - Comprehensive error handling, logging, and testing

---

## ✨ Features

### Core Capabilities

| Feature | Description |
|---------|-------------|
| **Voice Interaction** | End-to-end speech processing with Google Gemini Realtime Model |
| **Memory Management** | Session-based memory using mem0 + ChromaDB with intelligent persistence |
| **API Key Rotation** | Automatic rotation across 5 Google API keys for extended quota |
| **Weather Lookup** | Real-time weather information for any location worldwide |
| **Web Search** | DuckDuckGo integration with optimized 12s timeout (100% reliability) |
| **Email Sending** | SMTP-based email tool with comprehensive error handling |
| **Network Health** | Diagnostic tool to check connectivity and troubleshoot API issues |
| **Password Generator** | Cryptographically secure password generation with customizable options |
| **Noise Cancellation** | LiveKit BVC (Background Voice Cancellation) for crystal-clear audio |

### Advanced Features

- 🔑 **Multi-API Key Support** - Configure up to 5 Google API keys for memory operations
- 💾 **Persistent Memory** - Remembers context across sessions with intelligent batching
- 🎵 **Thinking Audio** - Configurable background audio during processing
- 📊 **Comprehensive Logging** - Detailed logging system for debugging and monitoring
- 🧪 **Extensive Testing** - 49+ passing tests covering all major functionality
- 🛡️ **Error Resilience** - Graceful degradation and user-friendly error messages

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10 or higher**
- **LiveKit Account** ([Sign up free](https://livekit.io))
- **Google API Key** (for Gemini Realtime Model)
- **Additional API Keys** (optional, for extended memory quota)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/zohirben/ASTRO-Livekit-Voice-Assistant.git
   cd ASTRO-Livekit-Voice-Assistant
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   
   # On Windows
   .venv\Scripts\activate
   
   # On Linux/Mac
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env with your credentials (use your favorite editor)
   # Required: LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, GOOGLE_API_KEY
   ```

5. **Run the agent**
   ```bash
   python agent.py dev
   ```

6. **Connect via LiveKit Playground**
   
   Open [https://agents-playground.livekit.io](https://agents-playground.livekit.io) and start talking!

### First Conversation

Try these commands to test ASTRO's capabilities:

```
🌤️  "What's the weather in Tokyo?"
🔍 "Search for the latest AI breakthroughs"
📧 "Send an email to john@example.com"
🔐 "Generate a secure password with 16 characters"
📡 "Check network health"
💤 "Shutdown yourself ASTRO" (saves memory and exits gracefully)
```

---

## 🏗️ Architecture

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | LiveKit Agents | Voice agent orchestration |
| **LLM/TTS/STT** | Google Gemini Realtime | Speech-to-speech processing |
| **Memory** | mem0ai + ChromaDB | Persistent conversational memory |
| **Vector Store** | ChromaDB | Local vector database with on-disk persistence |
| **Noise Cancellation** | LiveKit BVC | Background noise suppression |
| **Testing** | pytest | Comprehensive test coverage |

### Project Structure

```
ASTRO-Livekit-Voice-Assistant/
├── agent.py                    # Main entrypoint and AgentSession setup
├── prompts.py                  # Agent personality and instructions
├── mem0_config.py             # Memory system configuration (Gemini-only stack)
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── pytest.ini                # Test configuration
│
├── tools/                    # Function tools directory
│   ├── __init__.py
│   ├── weather.py           # Weather lookup tool (wttr.in API)
│   ├── search.py            # Web search tool (DuckDuckGo)
│   ├── send_email.py        # Email sending tool (SMTP)
│   ├── net_health.py        # Network health diagnostic
│   ├── shutdown.py          # Graceful shutdown with memory flush
│   └── generate_password.py # Secure password generation
│
├── memory/                   # Memory management system
│   ├── __init__.py
│   ├── config.py            # MemoryConfig dataclass
│   ├── manager.py           # MemoryManager (lifecycle & persistence)
│   ├── key_rotator.py       # Automatic API key rotation (up to 5 keys)
│   └── intelligent_updater.py # Smart memory extraction logic
│
├── utils/                    # Utility modules
│   ├── __init__.py
│   └── logging_config.py    # Centralized logging configuration
│
├── scripts/                  # Utility scripts
│   └── test_generate_password_ascii.py
│
└── tests/                    # Test suite
    ├── test_tools.py        # Tool functionality tests
    ├── test_agent.py        # Agent initialization tests
    └── test_memory.py       # Memory system tests
```

---

## 🧠 Memory System

ASTRO features an **intelligent memory system** that remembers context across conversations while efficiently managing API quotas.

### Key Features

- **Session-Based Memory** - Buffers messages during conversation, batch saves on shutdown
- **Automatic Key Rotation** - Cycles through up to 5 Google API keys when quotas are exhausted
- **Persistent Storage** - ChromaDB vector database with on-disk persistence
- **Intelligent Extraction** - Uses Gemini LLM to extract meaningful memories from conversations

### Memory Lifecycle

```
1. Startup
   └─> Load past memories from ChromaDB
   └─> Initialize key rotator with available API keys

2. During Session
   └─> Buffer messages in-memory (no redundant API calls)
   └─> Respond to queries using loaded context

3. Shutdown (triggered by "shutdown yourself ASTRO")
   └─> Batch save session to mem0
   └─> Auto-rotate to next key if quota exhausted
   └─> Flush and close ChromaDB connection
```

### API Key Rotation

Configure up to **5 Google API keys** for extended memory operations:

```bash
# .env configuration
GOOGLE_API_MEMORY_KEY1=your_first_key
GOOGLE_API_MEMORY_KEY2=your_second_key
GOOGLE_API_MEMORY_KEY3=your_third_key
GOOGLE_API_MEMORY_KEY4=your_fourth_key
GOOGLE_API_MEMORY_KEY5=your_fifth_key
```

When a key hits its quota (429 error), ASTRO automatically:
1. Advances to the next available key
2. Persists the current index to `memory_key_index.txt`
3. Continues operation seamlessly
4. Logs the rotation for monitoring

---

## 🛠️ Tools Reference

### 1. Weather Lookup 🌤️

**Trigger:** "What's the weather in [city]?"

**Implementation:** Uses wttr.in API for accurate worldwide weather data

**Example:**
```
User: "What's the weather in Paris?"
ASTRO: "In Paris, it's currently 15°C and partly cloudy."
```

---

### 2. Web Search 🔍

**Trigger:** "Search for [query]"

**Implementation:** DuckDuckGo search with optimized 12-second timeout for 100% reliability

**Example:**
```
User: "Search for recent AI breakthroughs"
ASTRO: "I found several recent developments, including..."
```

---

### 3. Email Sending 📧

**Trigger:** "Send an email to [address]"

**Implementation:** SMTP-based email with Gmail app password support

**Requirements:** Configure `GMAIL_USER` and `GMAIL_APP_PASSWORD` in `.env`

**Example:**
```
User: "Send an email to john@example.com about the meeting"
ASTRO: "Email sent successfully to john@example.com"
```

---

### 4. Network Health Check 📡

**Trigger:** "Check network health"

**Implementation:** Pings common services to diagnose connectivity issues

**Example:**
```
User: "Check network health"
ASTRO: "Network is healthy. All services responding normally."
```

---

### 5. Password Generator 🔐

**Trigger:** "Generate a password with [specifications]"

**Implementation:** Cryptographically secure password generation with customizable options

**Features:**
- Customizable length (8-128 characters)
- Character class control (upper, lower, digits, symbols)
- Named presets: "ascii", "all"
- Automatic saving to `generated_passwords.txt`

**Example:**
```
User: "Generate a secure password with 16 characters"
ASTRO: "Generated password: xK9$mP2@nQ7#vL4&"
```

---

### 6. Shutdown Agent 💤

**Trigger:** "Shutdown yourself ASTRO"

**Implementation:** Graceful shutdown with memory flush and session cleanup

**Example:**
```
User: "Shutdown yourself ASTRO"
ASTRO: "Flushing memory and shutting down. Goodbye."
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

#### Required Variables

```bash
# LiveKit Connection (Get from https://livekit.io)
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_api_key_here
LIVEKIT_API_SECRET=your_api_secret_here

# Google API Key (For Gemini Realtime Model)
GOOGLE_API_KEY=your_google_api_key_here
```

#### Memory System (Optional but Recommended)

```bash
# Primary Memory API Keys (for mem0 operations)
# Configure up to 5 keys for automatic rotation
GOOGLE_API_MEMORY_KEY1=your_first_memory_key
GOOGLE_API_MEMORY_KEY2=your_second_memory_key
GOOGLE_API_MEMORY_KEY3=your_third_memory_key
GOOGLE_API_MEMORY_KEY4=your_fourth_memory_key
GOOGLE_API_MEMORY_KEY5=your_fifth_memory_key

# Memory Configuration
ENABLE_MEMORY=true
CHROMA_PATH=./memory_db
MEMORY_USER_ID=astro_user
MEMORY_COLLECTION_NAME=jarvis_conversations
```

#### Email Tool (Optional)

```bash
# Gmail Configuration (for send_email tool)
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_gmail_app_password
```

#### Advanced Options

```bash
# Background Audio
ENABLE_THINKING_AUDIO=true
THINKING_VOLUME_1=0.3
THINKING_VOLUME_2=0.2

# Logging
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

---

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_tools.py -v

# Run with coverage report
pytest --cov=. --cov-report=html
```

### Test Coverage

- ✅ **Tool Functionality** - All tools tested with success and error cases
- ✅ **Error Handling** - Timeout, network failure, and API error scenarios
- ✅ **Agent Initialization** - Tool registration and LLM configuration
- ✅ **Memory System** - Persistence, retrieval, and key rotation logic

### Test Statistics

- **Total Tests:** 49+
- **Pass Rate:** 100%
- **Coverage:** 85%+

---

## 🎯 Usage Tips

### Best Practices

1. **Memory Management**
   - Always say "shutdown yourself ASTRO" to save session memory
   - Configure multiple API keys for extended usage
   - Monitor `memory_key_index.txt` to track current key

2. **API Quota Optimization**
   - Use 5 separate Google API keys for 5x memory quota
   - Keys automatically rotate on quota exhaustion
   - Check logs for rotation notifications

3. **Network Troubleshooting**
   - Use "check network health" before reporting tool failures
   - VPNs may cause connectivity issues with some services
   - Check logs with `LOG_LEVEL=DEBUG` for detailed diagnostics

4. **Email Configuration**
   - Use Gmail app passwords (not your regular password)
   - Enable "Less secure app access" if using older Gmail accounts
   - Test with "send email to yourself" first

---

## 🐛 Troubleshooting

### Common Issues

#### Issue: "ModuleNotFoundError"

**Solution:**
```bash
pip install -r requirements.txt
```

---

#### Issue: "LiveKit connection failed"

**Checklist:**
- ✅ Verify `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` in `.env`
- ✅ Check LiveKit account is active
- ✅ Test network connectivity
- ✅ Use "check network health" tool

---

#### Issue: "Memory not persisting"

**Solutions:**
1. Ensure `ENABLE_MEMORY=true` in `.env`
2. Configure at least one `GOOGLE_API_MEMORY_KEY*`
3. Always use "shutdown yourself ASTRO" to flush memory
4. Check `memory_db/` directory is writable
5. Review logs for quota exhaustion messages

---

#### Issue: "All API keys exhausted"

**Solutions:**
1. Wait for quota reset (usually 24 hours)
2. Add more API keys to `.env`
3. Manually reset key index: Delete `memory_key_index.txt`
4. Monitor usage in Google Cloud Console

---

#### Issue: "Email tool not working"

**Checklist:**
- ✅ Use Gmail app password (not regular password)
- ✅ Verify `GMAIL_USER` and `GMAIL_APP_PASSWORD` in `.env`
- ✅ Check SMTP port 587 not blocked by firewall
- ✅ Test with "send email to yourself" first

---

## 📚 Documentation

### Official Resources

- **LiveKit Agents:** [https://docs.livekit.io/agents/](https://docs.livekit.io/agents/)
- **Google Gemini:** [https://ai.google.dev/](https://ai.google.dev/)
- **mem0 Documentation:** [https://docs.mem0.ai/](https://docs.mem0.ai/)
- **ChromaDB:** [https://docs.trychroma.com/](https://docs.trychroma.com/)

### Code Documentation

All modules include comprehensive docstrings following Google style:
- Function-level documentation with parameter types
- Example usage in critical functions
- Citation links to official documentation

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

### Development Workflow

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes**
4. **Add tests** for new functionality
5. **Run the test suite** (`pytest`)
6. **Update documentation** (README, docstrings)
7. **Commit with clear messages** (`git commit -m 'feat: Add amazing feature'`)
8. **Push to your branch** (`git push origin feature/amazing-feature`)
9. **Open a Pull Request**

### Commit Conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation updates
- `test:` Test additions or modifications
- `refactor:` Code refactoring
- `style:` Code style changes (formatting, etc.)
- `chore:` Maintenance tasks

---

## 📝 License

This project is licensed under the **Apache 2.0 License** - see the [LICENSE](LICENSE) file for details.

Same license as LiveKit Agents for maximum compatibility.

---

## 🙏 Acknowledgments

- **LiveKit** - For the excellent Agents framework
- **Google** - For the powerful Gemini Realtime Model
- **mem0** - For the intelligent memory system
- **ChromaDB** - For the vector database
- **Community** - For feedback and contributions

---

## 📬 Support

### Getting Help

- 🐛 **Bug Reports:** [Open an issue](https://github.com/zohirben/ASTRO-Livekit-Voice-Assistant/issues)
- 💡 **Feature Requests:** [Start a discussion](https://github.com/zohirben/ASTRO-Livekit-Voice-Assistant/discussions)
- 📧 **Email:** zohirbenaissa00@gmail.com

### Issue Template

When reporting issues, please include:

1. Clear description of the problem
2. Steps to reproduce
3. Expected behavior vs actual behavior
4. Error logs (with `LOG_LEVEL=DEBUG`)
5. Environment details:
   - Python version
   - Operating system
   - Package versions (`pip list`)

---

## 🌟 Star History

If you find ASTRO useful, please consider giving it a star! ⭐

---

<div align="center">

**Built with ❤️ by [Zohirben](https://github.com/zohirben)**

*Powered by LiveKit Framework & Google Gemini*

</div>
