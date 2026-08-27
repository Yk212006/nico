# NICO

Offline local assistant powered by Ollama.

## Start

```bash
git pull
chmod +x start-local.sh
./start-local.sh
```

LAN hosting for other devices on your Wi-Fi:

```bash
./start-local.sh --lan
```

## Default

- Provider: `ollama`
- Model: `qwen2.5:3b`
- Mode: local browser UI
- Hosting: off by default, on with `--lan`

## Change model

```bash
export OLLAMA_MODEL=gemma2:2b
./start-local.sh
```
