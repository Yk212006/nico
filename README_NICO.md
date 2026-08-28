# NICO

Offline browser chatbot powered by Ollama.

## Start

```bash
git pull
chmod +x start-local.sh
./start-local.sh
```

For LAN access on other devices:

```bash
./start-local.sh --lan
```

## Default

- Provider: `ollama`
- Model: `qwen2.5:3b`
- Mode: browser UI

## Change model

```bash
export OLLAMA_MODEL=gemma2:2b
./start-desktop.sh
```
