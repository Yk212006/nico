# NICO Cloud Deployment — Complete Guide

## Overview

Move NICO's AI processing off the Raspberry Pi to a free cloud server.
The Pi runs only a lightweight client for sensors and GPIO.

```
Browser (phone/laptop)
       │
       ▼  http://cloud-ip:8080
┌──────────────────────┐
│  Cloud Server         │  ← Oracle Cloud (always free)
│  (AI, Google, Tools)  │    4 ARM cores, 24GB RAM
│  FastAPI Web Server   │
└──────────┬───────────┘
           │  REST API
           ▼
┌──────────────────────┐
│  Raspberry Pi         │  ← Your Pi 3B
│  cloud_client.py      │
│  (sensors, GPIO)      │
└──────────────────────┘
```

---

## Step 1: Push Code to GitHub

On your **laptop** (where you have the code):

```bash
cd ~/nico                  # or wherever the code is
git add -A
git commit -m "Add cloud deployment: web API, Pi client, Dockerfile"
git push
```

> **Important**: Make sure `credentials.json` is in `.gitignore`. It contains Google OAuth secrets and should NOT be committed.

---

## Step 2: Set Up Oracle Cloud Free Tier

Oracle Cloud gives you an **Always Free** ARM instance — no time limit.

### 2.1 Sign up

1. Go to https://signup.cloud.oracle.com
2. Enter email, choose region closest to you
3. Add payment method (required even for free tier — you won't be charged)
4. Verify phone number

### 2.2 Create a VM

1. Log in to https://cloud.oracle.com
2. Click ☰ menu → **Compute** → **Instances**
3. Click **Create instance**
4. Configure:
   - **Name**: `nico-server`
   - **Placement**: keep defaults
   - **Image**: **Ubuntu 22.04** (or **Canonical Ubuntu 22.04**)
   - **Shape**: Click **Change shape**
     - Select **ARM** tab
     - Choose **VM.Standard.A1.Flex**
     - **OCPUs**: 4, **Memory**: 24 GB
     - *(This is the always-free ARM shape)*
   - **Add SSH keys**: 
     - If you have an SSH key pair: click "Paste public keys" and paste `~/.ssh/id_rsa.pub`
     - If you don't: open a terminal and run `ssh-keygen -t ed25519`, then paste the `.pub` file
   - **Boot volume**: keep default (200 GB free)

5. Click **Create**

Wait 2-3 minutes for the instance to provision. Note the **Public IP address**.

### 2.3 Open Firewall Port

1. Go to ☰ menu → **Networking** → **Virtual Cloud Networks**
2. Click your VCN name
3. Click the subnet link
4. Click the **Security List** (default one)
5. Click **Add Ingress Rules**:
   - **Source CIDR**: `0.0.0.0/0`
   - **Destination Port Range**: `8080`
   - **Description**: `NICO web UI`
   - Click **Add Ingress Rules**

---

## Step 3: Deploy NICO on the Cloud

Open a terminal on your **laptop** and SSH into the cloud VM:

```bash
ssh ubuntu@<your-cloud-ip>
```

*(If you used Oracle Linux instead of Ubuntu, the user is `opc`)*

### 3.1 Run the install script

```bash
sudo apt update && sudo apt install -y git
git clone https://github.com/Yk212006/nico.git
cd nico
chmod +x deploy/cloud-install.sh
./deploy/cloud-install.sh
```

This installs Python, creates a virtual environment, and installs NICO with web + Google support.

### 3.2 Configure API keys

```bash
nano .env
```

Set at minimum:
```
OPENAI_API_KEY=sk-...your-key...
NICO_DEFAULT_PROVIDER=openai
NICO_PORT=8080
```

If using Google Calendar/Gmail, also add:
```
GOOGLE_CREDENTIALS_FILE=/home/ubuntu/nico/credentials.json
```

Save: `Ctrl+O`, `Enter`, `Ctrl+X`.

### 3.3 Add Google credentials

**Option A**: Upload from your laptop:
```bash
# On your laptop, in a new terminal:
scp ~/nico/credentials.json ubuntu@<cloud-ip>:~/nico/credentials.json
```

**Option B**: Create fresh from Google Cloud Console:
1. Go to https://console.cloud.google.com/apis/credentials
2. Create OAuth 2.0 Client ID → Desktop application
3. Download JSON, upload to cloud VM

### 3.4 Run the server

```bash
cd ~/nico
source .venv/bin/activate
python -m nico.web_api
```

You should see the startup banner. Open `http://<cloud-ip>:8080` in your browser.

### 3.5 (Optional) Run as a background service

```bash
sudo cp deploy/nico-cloud-server.service /etc/systemd/system/
sudo nano /etc/systemd/system/nico-cloud-server.service
```

Edit the `User` and `WorkingDirectory` paths for the cloud VM, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now nico-cloud-server
sudo systemctl status nico-cloud-server
```

---

## Step 4: Set Up HTTPS (Recommended)

Without HTTPS, your Google OAuth tokens could be intercepted.

### Using Caddy (easiest):

```bash
sudo apt install -y caddy
sudo nano /etc/caddy/Caddyfile
```

Replace contents with:
```
nico.your-domain.com {
    reverse_proxy localhost:8080
}
```

If you don't have a domain, use Caddy's DNS challenge or just use HTTP for now:

```bash
sudo caddy reverse-proxy --to localhost:8080
```

Then access via `http://<cloud-ip>:80`.

---

## Step 5: Set Up the Pi Client

On your **Raspberry Pi**, open a terminal.

### 5.1 Install NICO (minimal — no AI deps)

```bash
cd ~/nico
git pull
source .venv/bin/activate
pip install -e .[pi]   # Only GPIO + DHT sensor deps
```

### 5.2 Run the cloud client

```bash
export NICO_CLOUD_URL=http://<cloud-ip>:8080
python -m nico.cloud_client --server http://<cloud-ip>:8080 --device-id pi-3b
```

You should see:
```
NICO Cloud Client
Server:  http://<cloud-ip>:8080
Device:  pi-3b
```

The client will:
- Send DHT22 temperature/humidity every 30 seconds
- Poll for GPIO commands from the cloud
- Report CPU temperature

### 5.3 (Optional) Auto-start on boot

```bash
cp deploy/nico-cloud-client.service ~/.config/systemd/user/
systemctl --user enable --now nico-cloud-client
```

Or edit the file to set your cloud IP, then:
```bash
sudo cp deploy/nico-cloud-client.service /etc/systemd/system/
sudo systemctl enable --now nico-cloud-client
```

---

## Step 6: Send GPIO Commands from Cloud

While chatting with NICO via the web UI, you can say things like:

> "Turn on pin 17"  
> "Turn off pin 17"  
> "What's the temperature in my room?"  
> "What's the CPU temperature of the Pi?"

The cloud server will queue a command → Pi client polls and executes it → result reports back.

---

## Step 7: Access from Anywhere

- **Via browser**: `http://<cloud-ip>:8080`
- **Via API**: `POST http://<cloud-ip>:8080/api/chat` with `{"message": "hello"}`
- **Via WebSocket**: `ws://<cloud-ip>:8080/ws`

---

## Monitoring

### Check cloud server logs:
```bash
# If running as service:
sudo journalctl -u nico-cloud-server -f

# If running in terminal:
# (logs are in the terminal output)
```

### Check Pi client logs:
```bash
# If running as service:
sudo journalctl -u nico-cloud-client -f

# If running in terminal:
# (just watch the terminal)
```

### Check connected devices:
```bash
curl http://<cloud-ip>:8080/api/devices
# Returns: ["pi-3b"]
```

### Check latest sensor data:
```bash
curl http://<cloud-ip>:8080/api/devices/pi-3b/sensors
# Returns: {"temperature": 24.5, "humidity": 55.2, "cpu_temp": 48.3}
```

---

## Troubleshooting

### "Google Calendar is not configured"
Make sure `credentials.json` exists and is set in `.env`:
```bash
ls -la ~/nico/credentials.json
grep GOOGLE_CREDENTIALS_FILE ~/nico/.env
```

### Pi can't connect to cloud
```bash
curl http://<cloud-ip>:8080/api/health
```
Should return `{"status": "ok"}`. If not, check firewall (Step 2.3).

### Server won't start — port in use
```bash
sudo lsof -i :8080   # Find what's using port 8080
# Or change port:
export NICO_PORT=8090
python -m nico.web_api
```

### DHT sensor not working on Pi client
The client gracefully handles missing sensors. Run with `--debug` to see details:
```bash
python -m nico.cloud_client --server http://<cloud-ip>:8080 --debug
```

---

## What's Running Where

| Feature | Runs On |
|---------|---------|
| AI chat (OpenAI/Claude/Gemini) | Cloud VM |
| Google Calendar/Gmail | Cloud VM |
| Smart home control | Cloud VM |
| Web chat UI | Cloud VM (served to browser) |
| DHT22 temperature/humidity | Raspberry Pi |
| GPIO pin control | Raspberry Pi |
| Voice capture | *(optional — Pi or cloud)* |

**Result**: Your Pi 3B is no longer slow. It only runs the 200-line `cloud_client.py`.

---

## Estimated Costs

| Service | Cost |
|---------|------|
| Oracle Cloud ARM VM (4 OCPU, 24GB) | **$0/month** (always free) |
| OpenAI API | ~$2-5/month (pay-as-you-go) |
| Domain (optional) | ~$10/year |
| **Total** | **~$2-5/month** |

---

## Need Help?

- Open an issue at https://github.com/Yk212006/nico/issues
- Ask questions in the GitHub discussions
