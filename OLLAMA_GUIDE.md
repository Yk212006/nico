# NICO + Ollama — Free Local AI, Accessible Anywhere

Run NICO entirely on your laptop with a local AI model (Ollama).
Access it from your phone, Pi, or any device via Cloudflare tunnel.

**Zero cost. No API keys. No quota. No internet needed for AI.**

---

## Step 1: Install Ollama

**Windows:** Download from https://ollama.com/download → install

**Mac/Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

## Step 2: Pull a model

Open a terminal:

```bash
ollama pull llama3.2
```

Other options: `gemma2:2b` (fast), `deepseek-r1:7b` (smart), `qwen2.5:7b`

## Step 3: Install NICO on your laptop

```bash
git clone https://github.com/Yk212006/nico.git
cd nico
python -m venv .venv
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate
pip install -e .[web]
```

## Step 4: Start everything

**Terminal 1 — Start Ollama:**
```bash
ollama serve
```
Leave this running.

**Terminal 2 — Start NICO:**
```bash
cd nico
source .venv/bin/activate
export NICO_DEFAULT_PROVIDER=ollama
python -m nico.web_api
```

Test locally: open `http://localhost:8080` in your browser.

## Step 5: Access from anywhere

**Terminal 3 — Cloudflare tunnel:**
```bash
cloudflared tunnel --url http://localhost:8080
```

Prints: `https://xxx.trycloudflare.com` — open on your phone, Pi, any device.

No Cloudflare? Use localhost.run:
```bash
ssh -R 80:localhost:8080 nokey@localhost.run
```

## Step 6: Change models anytime

In `.env` or set:
```bash
export OLLAMA_MODEL=deepseek-r1:7b
```

Restart NICO. Available models: `ollama list`

---

## Done

Your laptop runs the AI. Your phone/Pi access it through the tunnel.
No costs, no keys, no quotas. Ever.
