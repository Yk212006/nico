# NICO Offline Local Model

Run NICO as a local assistant powered by Ollama.

## What this gives you

- Offline local AI
- Answers questions
- Generates program code
- Runs in a browser on your device or local network

## Recommended model

Use `qwen2.5:3b` on stronger phones/laptops.
If it is too slow, try `gemma2:2b`.

## Start

```bash
git pull
chmod +x start-local.sh
./start-local.sh
```

## If Ollama is not installed

Install Ollama first, then pull a model:

```bash
ollama pull qwen2.5:3b
```

## Open the UI

Open:

```text
http://127.0.0.1:8080
```

Or from another device on the same Wi-Fi, use the host IP.

## Notes

- `NICO_PROFILE=local` selects the offline profile.
- Tools that need the internet are disabled in local mode.
