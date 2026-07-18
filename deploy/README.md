# NICO Cloud Deployment

Deploy NICO to a cloud server so the Raspberry Pi runs as a thin client
(sensors + GPIO only) while the heavy AI processing happens in the cloud.

## Quick Start (any cloud VM)

```bash
# 1. SSH into your cloud VM (Ubuntu 22.04 / Debian 12 recommended)

# 2. Install dependencies
sudo apt update && sudo apt install -y git python3 python3-venv python3-pip portaudio19-dev

# 3. Clone NICO
git clone https://github.com/Yk212006/nico.git
cd nico

# 4. Create .env with your API keys
cp .env.example .env
nano .env
# At minimum set: OPENAI_API_KEY, GOOGLE_CREDENTIALS_FILE

# 5. Install with web support
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[web,google]

# 6. Copy your credentials.json (from Pi or download fresh)
#    Or create a new OAuth client ID at https://console.cloud.google.com/
#    and save as credentials.json

# 7. Run!
python -m nico.web_api
# Open http://your-cloud-ip:8080 in your browser
```

## Oracle Cloud Free Tier (recommended)

Oracle Cloud gives you an **Always Free** ARM instance:
- 4 OCPU (ARM Ampere), 24 GB RAM
- 200 GB storage
- 10 TB outbound data per month

### Setup

1. Sign up at https://signup.cloud.oracle.com
2. Create a VM instance:
   - Image: **Ubuntu 22.04** or **Oracle Linux 8**
   - Shape: **VM.Standard.A1.Flex** (ARM)
   - OCPUs: 4, Memory: 24 GB
   - Add your SSH public key
3. Open ports 8080 (and 443 if using HTTPS):
   - In your VCN, add ingress rules for TCP 8080
4. SSH in and run the Quick Start steps above

### With Docker (alternative)

```bash
# On your cloud VM:
docker build -t nico-cloud .
docker run -d \
  --name nico \
  -p 8080:8080 \
  -v $(pwd)/.env:/app/.env \
  -v $(pwd)/credentials.json:/app/credentials.json \
  nico-cloud
```

## Other Cloud Options

| Provider | Free Tier | Notes |
|----------|-----------|-------|
| **Oracle Cloud** | 4 ARM cores, 24GB RAM | Best for this use case |
| **Google Cloud Run** | 2M requests/month | Serverless, good for stateless |
| **Railway** | $5 credit | Simple deploy from GitHub |
| **Fly.io** | 3 shared VMs, 256MB | Tight on RAM for Python |
| **PythonAnywhere** | 512MB RAM | Limited but simple |

## Using HTTPS

For real use, add a reverse proxy with automatic SSL:

```bash
# Install Caddy
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy

# Create /etc/caddy/Caddyfile:
# nico.example.com {
#     reverse_proxy localhost:8080
# }

sudo systemctl restart caddy
```

---

## Raspberry Pi Client

On your Pi, run the thin client to send sensor data and receive GPIO commands:

```bash
# Install (minimal — no AI deps needed on Pi)
cd ~/nico
source .venv/bin/activate
pip install -e .[pi]

# Run client
export NICO_CLOUD_URL=http://your-cloud-ip:8080
export NICO_CLOUD_API_KEY=your-api-key
python -m nico.cloud_client
```

Or as a systemd service:

```ini
[Unit]
Description=NICO Cloud Client
After=network.target

[Service]
Type=simple
User=yatin
WorkingDirectory=/home/yatin/nico
Environment=NICO_CLOUD_URL=http://your-cloud-ip:8080
ExecStart=/home/yatin/nico/.venv/bin/python -m nico.cloud_client
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
