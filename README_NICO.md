# NICO Offline Local Assistant

NICO is now configured as a **local offline assistant** powered by Ollama.

## What it does

- Answers questions locally
- Writes and explains code
- Runs in a browser on the same device
- Does not require cloud APIs by default

## Start

```bash
git pull
chmod +x start-local.sh
./start-local.sh
```

## Model

Default model: `qwen2.5:3b`

Change it with:

```bash
export OLLAMA_MODEL=gemma2:2b
./start-local.sh
```

## Notes

- `NICO_PROFILE=local`
- `NICO_DEFAULT_PROVIDER=ollama`
- Tools and cloud integrations are disabled by default
