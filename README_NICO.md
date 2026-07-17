# NICO

NICO — A modular AI assistant for desktop and Raspberry Pi.

## Architecture

```
nico/
├── app.py              # Application container — wires all subsystems together
├── cli.py              # CLI entry point (run REPL, one-shot chat, image analysis)
├── main.py             # Standalone REPL launcher
├── brain/              # AI provider layer
│   ├── provider.py     # BaseProvider ABC (chat, vision, speech, tools)
│   ├── router.py       # ProviderRouter — fallback across OpenAI/Claude/Gemini
│   ├── openai_provider.py
│   ├── claude_provider.py
│   └── gemini_provider.py
├── memory/             # Memory subsystem
│   ├── manager.py      # MemoryManager — orchestrates conversation + long-term
│   ├── conversation.py # ConversationMemory — auto-summarizing transcript
│   ├── long_term.py    # LongTermMemory — preferences, facts, semantic search
│   ├── embeddings.py   # EmbeddingProvider + cosine similarity + cache
│   └── persistence.py  # MemoryStore protocol + FileMemoryStore
├── audio/              # Voice pipeline
│   ├── voice_pipeline.py   # VAD loop with silence detection
│   ├── text_to_speech.py   # Base + OpenAI TTS (streaming)
│   ├── audio_output.py     # Base + DefaultAudioOutput (PyAudio)
│   ├── microphone.py       # Base + DefaultMicrophone
│   ├── speech_to_text.py   # Base + DefaultSpeechToText
│   └── wakeword.py         # Base + DefaultWakeWordDetector
├── tools/              # Tool system
│   ├── manager.py      # ToolManager — register, execute, schema export
│   ├── registry.py     # ToolRegistry — optional auto-discovery
│   ├── vision/describe_image.py    # AI vision analysis
│   ├── weather/weather.py
│   ├── news/news.py
│   ├── files/files.py
│   ├── email/email_tool.py
│   ├── calendar/calendar_tool.py
│   ├── camera/camera.py
│   ├── google_home/google_home.py
│   ├── gpio/gpio.py
│   └── system/system_info.py
├── integrations/       # Google service dispatcher
│   └── google/dispatcher.py  # Routes to Calendar/Gmail/Home/Tasks/Drive
├── orchestrator.py     # IntentOrchestrator — NL routing to tools/integrations
├── events.py           # Typed event bus (publish/subscribe)
├── plugin.py           # Plugin base class + discovery
├── plugin_manager.py   # PluginManager — lifecycle management
├── notifications.py    # NotificationService (desktop, voice, TTS)
├── scheduler.py        # TaskScheduler (APScheduler wrapper)
├── context.py          # ConversationContext — topic tracking
├── registry.py         # ServiceRegistry — DI container
├── bootstrap.py        # AppBootstrap — factory for NicoApp
├── lifecycle.py        # AppLifecycle — managed start/stop
├── hardware/           # Raspberry Pi hardware controllers
├── utils/sanitize.py   # Input sanitization + injection detection
└── pi_runtime.py       # Pi detection + settings
```

## Installation

### Raspberry Pi (.deb package — recommended)

```bash
# Download the latest .deb from releases
wget https://github.com/Yk212006/nico/releases/latest/download/nico_0.2.0_arm64.deb

# Install
sudo dpkg -i nico_0.2.0_arm64.deb
sudo apt install -f   # install any missing dependencies

# Configure and start
sudo nano /etc/nico/.env             # add your API keys
sudo systemctl start nico
sudo journalctl -u nico -f           # watch logs
```

### From source (any platform)

```bash
# Clone and enter the project
git clone https://github.com/Yk212006/nico.git
cd nico

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# Install core (chat, tools, memory, all providers)
pip install -e .

# Install optional groups as needed:
pip install -e .[pi]         # Raspberry Pi hardware (GPIO, OLED, DHT)
pip install -e .[voice]      # Voice pipeline (microphone, TTS, wake word)
pip install -e .[google]     # Google integrations (Calendar, Gmail, Drive)
pip install -e .[assistant]  # Google Assistant SDK for smart-home control
pip install -e .[full]       # Scheduler, RSS, desktop notifications
pip install -e .[dev]        # Testing

# All together:
pip install -e .[pi,voice,google,full]
```

> **Raspberry Pi users**: See "Platform Notes: Raspberry Pi" below for system packages.

## Quick Start

```bash
# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Interactive REPL
python main.py

# One-shot chat
python -m nico.cli chat "What's the weather in London?"

# Analyze an image
python -m nico.cli analyze /path/to/photo.jpg
python -m nico.cli analyze /path/to/photo.jpg --prompt "What objects do you see?"

# Chat with an image
python -m nico.cli chat "Describe this" --image /tmp/photo.jpg

# Run with a specific provider
python -m nico.cli run --provider claude
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `run` | Interactive REPL with tool execution |
| `chat <message>` | One-shot query, returns response |
| `analyze <image>` | Vision analysis of an image file |

### Options

- `--provider <name>` — override default AI provider (`openai`, `claude`, `gemini`)
- `--profile <name>` — load a preset profile (`default`, `voice`, `minimal`)
- `--profile-file <path>` — load a custom JSON profile
- `--no-tools` — disable tool execution (run mode only)
- `--image <path>` — attach an image for vision analysis (chat mode)
- `--prompt <text>` — custom analysis prompt (analyze mode)

## In-REPL Commands

Within `main.py` or `nico.cli run`:

- `exit` / `quit` — exit
- `use claude` / `switch to gpt` / `use gemini` — switch providers
- `analyze <path> [prompt]` — analyze an image

## Profiles

Three built-in profiles:

| Profile   | Provider | Tools | Memory |
|-----------|----------|-------|--------|
| `default` | OpenAI   | yes   | yes    |
| `voice`   | Claude   | yes   | yes    |
| `minimal` | Gemini   | no    | no     |

Custom profiles can be loaded from JSON files via `--profile-file`.

## AI Providers

All three providers support chat, streaming, vision (image analysis), and tool calling with automatic fallback:

- **OpenAI** — GPT-4o / GPT models
- **Claude** — Anthropic Claude models
- **Gemini** — Google Gemini models

## Memory System

- **ConversationMemory** — auto-summarizing transcript that prunes old turns when the buffer exceeds `max_chars`
- **LongTermMemory** — durable facts, user preferences, keyword + semantic search
- **MemoryManager** — unified API with automatic importance scoring and consolidation (extracts facts like names, locations, preferences from conversation)
- **Persistence** — `FileMemoryStore` (JSON on disk), explicit `save()` on all layers

## Voice / Audio

- **VoicePipeline** — VAD loop with configurable silence threshold/timeout/max-duration
- **STT** — speech-to-text via configurable provider
- **TTS** — text-to-speech with streaming support (OpenAI TTS)
- **Wake word** — configurable wake word detection
- **Interruption** — barge-in support during playback

## Vision

- **Router.vision()** — image analysis with cross-provider fallback
- **DescribeImageTool** — reads image files and analyzes them via the active provider
- **NicoApp.analyze_image()** — direct API for programmatic use
- Orchestrator routes "describe this image", "what's in this photo", etc. to the vision tool

## Plugin System

Create a plugin by subclassing `Plugin`:

```python
from nico.plugin import Plugin

class MyPlugin(Plugin):
    name = "my_plugin"
    description = "Adds custom tools"

    def get_tools(self):
        return [MyTool()]

    async def on_load(self, app):
        app.tool_manager.register(MyTool())
```

Load it via `PluginManager` or auto-discover from a directory.

## Security

- Input sanitization strips null bytes and control characters (max 32K chars)
- Prompt injection detection for common bypass patterns
- File operations sandboxed under `NICO_FILES_ROOT`
- Destructive operations (file delete, email send, GPIO write) require explicit confirmation
- API keys sent via headers, never in URLs

## Extending

- **New tool**: Create a class with `name`, `description`, `parameters`, and `async def execute()`. Register in `build_tool_manager()`.
- **New provider**: Subclass `BaseProvider` and inject into `ProviderRouter`.
- **New plugin**: Subclass `Plugin` and use `PluginManager.register()`.
- **Event hook**: Use `subscribe(EventType, handler)` from `nico.events`.

## Platform Notes: Raspberry Pi

- **WhatsApp tool** (`playwright`-based) is **not supported on Raspberry Pi** — Chromium automation for ARM is unavailable. This tool is safe to leave installed; it will report "unavailable" gracefully.
- **Google Assistant SDK** (`google-assistant-grpc`) requires `grpcio`. On **64-bit Pi OS (aarch64)** a pre-built wheel is available. On **32-bit Pi OS (armv7l)** you must compile `grpcio` from source (`pip install grpcio --no-binary=grpcio`), which needs build-essential and cmake.
- **Audio** (`pyaudio`): `sudo apt install portaudio19-dev python3-pyaudio`
- **TTS** (`pyttsx3`): `sudo apt install espeak libespeak1`
- **OLED display** (`luma.oled`): `sudo apt install libopenjp2-7 libtiff5 libfreetype6`
- **Camera** (`picamera2`): `sudo apt install python3-picamera2` (Raspberry Pi OS Bullseye+)
- **GPIO**: Install `RPi.GPIO` or `gpiozero` — optionally via `pip install nico[pi]`
- **Memory**: Disabled by default on Pi (`enable_memory=false` in `build_pi_settings()`) to save resources

## Dependencies

Core: `httpx`, `python-dotenv`
Optional groups: `full`, `voice`, `google`, `assistant`, `pi`, `whatsapp`, `dev`
Install with e.g. `pip install nico[pi,voice]` or `pip install nico[all]`
