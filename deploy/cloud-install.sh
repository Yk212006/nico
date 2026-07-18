#!/usr/bin/env bash
# NICO Cloud Server — one-command install for Ubuntu/Debian
# Usage: curl -fsSL https://raw.githubusercontent.com/Yk212006/nico/main/deploy/cloud-install.sh | bash

set -euo pipefail

NICO_DIR="${NICO_DIR:-$HOME/nico}"
NICO_PORT="${NICO_PORT:-8080}"

echo "==> Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq git python3 python3-venv python3-pip portaudio19-dev

echo "==> Cloning NICO..."
if [ ! -d "$NICO_DIR" ]; then
    git clone https://github.com/Yk212006/nico.git "$NICO_DIR"
else
    echo "NICO already exists at $NICO_DIR, pulling latest..."
    cd "$NICO_DIR" && git pull
fi

cd "$NICO_DIR"

echo "==> Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "==> Installing NICO with web + google support..."
pip install --quiet -e .[web,google]

echo "==> Setting up .env..."
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
    else
        cat > .env << 'EOF'
OPENAI_API_KEY=
NICO_DEFAULT_PROVIDER=openai
NICO_PORT=8080
NICO_HOST=0.0.0.0
EOF
    fi
    echo ">>> Edit $NICO_DIR/.env with your API keys, then run:"
else
    echo ".env already exists"
fi

cat <<WELCOME

╔══════════════════════════════════════════════════════════╗
║  NICO Cloud Server installed!                           ║
║                                                        ║
║  1. Edit your .env file:                                ║
║       nano $NICO_DIR/.env                              ║
║                                                        ║
║  2. Activate and start:                                 ║
║       cd $NICO_DIR                                      ║
║       source .venv/bin/activate                         ║
║       python -m nico.web_api                            ║
║                                                        ║
║  3. Open in browser:                                    ║
║       http://$(curl -s ifconfig.me):$NICO_PORT           ║
║                                                        ║
║  For HTTPS with Caddy:                                  ║
║       sudo apt install -y caddy                         ║
║       sudo caddy reverse-proxy --to localhost:$NICO_PORT  ║
╚══════════════════════════════════════════════════════════╝
WELCOME
