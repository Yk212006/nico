# NICO on Pi — Web Interface + Public Access Guide

Access NICO from any device (phone, laptop, anywhere) without a cloud VM.
Your Pi runs a lightweight web server — no GUI, no heavy load.

## Architecture

```
Your Phone / Laptop / Anywhere
        │
        ▼  https://nico-abc123.lhr.life
┌───────────────────┐
│ Cloudflare Tunnel  │  ← Free tunnel to the internet
│ (or localhost.run) │
└─────────┬─────────┘
          │
          ▼  localhost:8080
┌───────────────────┐
│ Raspberry Pi 3B    │
│ nico.web_api       │  ← FastAPI web server (no GUI)
│ (AI, Google, etc)  │
└───────────────────┘
```

---

## Step 1: Pull latest code

```bash
cd ~/nico
git pull
source .venv/bin/activate
```

## Step 2: Install web dependencies

```bash
pip install -e .[web,google,assistant]
```

This installs `fastapi` and `uvicorn` alongside your Google/Assistant deps.

## Step 3: Set up environment

Make sure your `.env` has the required keys:

```bash
nano ~/nico/.env
```

Minimal:
```
OPENAI_API_KEY=sk-...
```

With Google:
```
GOOGLE_CREDENTIALS_FILE=/home/yatin/nico/credentials.json
```

Save: `Ctrl+O`, `Enter`, `Ctrl+X`.

## Step 4: Start NICO web server

```bash
source ~/nico/.venv/bin/activate
export GOOGLE_CREDENTIALS_FILE=/home/yatin/nico/credentials.json
python -m nico.web_api
```

You'll see:
```
  ╔══════════════════════════════════════╗
  ║     NICO Cloud Server                ║
  ║                                      ║
  ║  Listening on 0.0.0.0:8080           ║
  ║  Open http://localhost:8080           ║
  ╚══════════════════════════════════════╝
```

Test it on your local network: open `http://<pi-ip>:8080` from your phone or laptop.

To find your Pi's IP:
```bash
hostname -I
```

Leave this terminal running. Open a **second terminal** for the tunnel.

---

## Step 5: Expose to the internet

Pick one of these two options:

### Option A: Cloudflare Tunnel (recommended)

```bash
# Download cloudflared (one-time)
cd ~
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm -o cloudflared
chmod +x cloudflared
sudo mv cloudflared /usr/local/bin/

# Start tunnel (in the second terminal):
cloudflared tunnel --url http://localhost:8080
```

After a few seconds it prints:
```
2025/01/01 12:00:00 https://potato-falcon-9a2b.trycloudflare.com
```

That's your **public URL**. Open it from any device anywhere.

### Option B: localhost.run (simpler, no install)

```bash
ssh -R 80:localhost:8080 nokey@localhost.run
```

Prints:
```
https://nico-abc123.lhr.life
```

That's your public URL.

---

## Step 6: Make it permanent (auto-start on boot)

### 6a. Auto-start NICO web server

```bash
sudo nano /etc/systemd/system/nico-web.service
```

Paste:
```ini
[Unit]
Description=NICO Web Server
After=network.target

[Service]
Type=simple
User=yatin
WorkingDirectory=/home/yatin/nico
EnvironmentFile=/home/yatin/nico/.env
ExecStart=/home/yatin/nico/.venv/bin/python -m nico.web_api
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now nico-web
sudo systemctl status nico-web
```

### 6b. Auto-start tunnel

```bash
sudo nano /etc/systemd/system/nico-tunnel.service
```

Paste:
```ini
[Unit]
Description=NICO Cloudflare Tunnel
After=network.target nico-web.service
Requires=network.target

[Service]
Type=simple
User=yatin
ExecStart=/usr/local/bin/cloudflared tunnel --url http://localhost:8080
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now nico-tunnel
```

### 6c. Check both are running

```bash
sudo journalctl -u nico-web -n 20 --no-pager
sudo journalctl -u nico-tunnel -n 20 --no-pager
```

To find your tunnel URL:
```bash
sudo journalctl -u nico-tunnel --no-pager | grep -o 'https://[^ ]*\.trycloudflare\.com' | tail -1
```

---

## Step 7: Using NICO from anywhere

Open your public URL in any browser:

```
https://potato-falcon-9a2b.trycloudflare.com   ← (your URL will be different)
```

You'll see the NICO chat interface. Type messages, get AI responses, control Google Calendar, smart home, etc.

### No more Tkinter GUI

The GUI used to slow your Pi to a crawl. Now:
- **nicoweb_api** runs headless — no screen, no heavy rendering
- **Tunnel** exposes it to the internet
- **Browser** does the rendering work (on your phone/laptop, not the Pi)

---

## Step 8: GPIO & Sensors (optional)

If you want the Pi to control GPIO pins or read DHT sensors while running as a web server, create a simple script that runs alongside:

```bash
nano ~/nico/local_gpio.py
```

Paste:
```python
"""Simple GPIO control for local use with NICO web server."""
import RPi.GPIO as GPIO
import board
import adafruit_dht

GPIO.setmode(GPIO.BCM)
dht = adafruit_dht.DHT22(board.D4)

def read_temp():
    try:
        return {"temp": dht.temperature, "humidity": dht.humidity}
    except:
        return {"error": "sensor not found"}

def gpio_write(pin, value):
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, value)
    return f"Pin {pin} set to {value}"

def gpio_read(pin):
    GPIO.setup(pin, GPIO.IN)
    return GPIO.input(pin)
```

You can import and use this from the web API or call it from a separate script.

---

## Troubleshooting

### "Address already in use" when starting web server
```bash
sudo lsof -i :8080   # find what's using port 8080
# Kill it or change port:
export NICO_PORT=8090
python -m nico.web_api
```

### Tunnel won't connect
```bash
ping google.com   # check internet
cloudflared tunnel --url http://localhost:8080   # retry with verbose output
```

### Web server starts but browser shows nothing
```bash
curl http://localhost:8080/api/health   # test locally first
# Should return {"status": "ok", "initialized": true}
```

### Slow responses
First request may take 5-10 seconds as AI models initialize. Subsequent requests are faster. If consistently slow, switch to a faster model like `gpt-4o-mini` or `gemini-1.5-flash`.

---

## How it compares

| Setup | Pi Load | Access from anywhere | Cost |
|-------|---------|---------------------|------|
| Old: Tkinter GUI | Heavy (GUI rendering) | No | $0 |
| **This: Web API + Tunnel** | **Light (no GUI)** | **Yes** | **$0** |
| Cloud VM | Minimal (thin client) | Yes | $0-5/mo |

This gives you off-device access with zero extra cost and much better Pi performance.
