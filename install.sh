#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────
# NICO — Raspberry Pi Installer
# ──────────────────────────────────────────────

NICO_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$NICO_DIR/.venv"

cd "$NICO_DIR"

echo "=== NICO Installer ==="
echo ""

# ── 1. System packages ───────────────────────
echo "[1/6] Installing system packages..."

sudo apt update

# Essential build tools
sudo apt install -y python3-dev build-essential cmake

# I2C & SPI (for OLED, sensors)
sudo apt install -y python3-smbus i2c-tools

# GPIO
sudo apt install -y python3-rpi.gpio python3-gpiozero || true

# luma.oled dependencies
sudo apt install -y libopenjp2-7 libtiff5 libfreetype6 || true

# Audio (optional — won't fail if missing)
sudo apt install -y portaudio19-dev espeak-ng libespeak-ng-dev libportaudio2 || true

# libgpiod (for adafruit-circuitpython-dht) — may not exist on older Pi OS
sudo apt install -y libgpiod2 libgpiod-dev python3-libgpiod || true

# Camera (Pi OS Bullseye+)
sudo apt install -y python3-picamera2 || true

echo ""

# ── 2. Create virtual environment ────────────
echo "[2/6] Creating virtual environment..."

if [ -d "$VENV_DIR" ]; then
    echo "Removing old venv..."
    rm -rf "$VENV_DIR"
fi

python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip wheel setuptools

echo ""

# ── 3. Install Python packages ───────────────
echo "[3/6] Installing Python packages..."

# Core + hardware
pip install -e "$NICO_DIR"[pi]

# GPIO might fail in venv if kernel headers missing — install system version instead
if ! python -c "import RPi.GPIO" 2>/dev/null; then
    echo "RPi.GPIO pip install failed — using system package"
    cp /usr/lib/python3/dist-packages/RPi* "$VENV_DIR/lib/python*/site-packages/" 2>/dev/null || true
fi

# DHT sensor — try both libraries, one usually works
if ! python -c "import Adafruit_DHT" 2>/dev/null; then
    if ! python -c "import adafruit_dht" 2>/dev/null; then
        echo "Installing DHT sensor library..."
        pip install adafruit-circuitpython-dht 2>/dev/null || {
            echo "adafruit-circuitpython-dht failed — trying Adafruit-DHT with --force-pi"
            pip install Adafruit-DHT --force-pi 2>/dev/null || {
                echo "WARNING: No DHT sensor library installed."
                echo "  Sensors will use simulated readings."
                echo "  To fix later: sudo apt install libgpiod2 && pip install adafruit-circuitpython-dht"
            }
        }
    fi
fi

# Voice (optional)
pip install gTTS openai 2>/dev/null || true

echo ""

# ── 4. Google integrations (choose one) ──────
echo "[4/6] Google integration setup..."
echo ""
echo "Choose your Google integration (or skip):"
echo "  1 — Google APIs (Calendar, Gmail, Drive)"
echo "  2 — Assistant SDK (smart-home control)"
echo "  3 — None (skip)"
echo ""

# Determine which to use based on .env if it exists
INSTALL_ASSISTANT=false
INSTALL_GOOGLE_API=false

if [ -f "$NICO_DIR/.env" ]; then
    if grep -q "GOOGLE_ASSISTANT_DEVICE_MODEL_ID" "$NICO_DIR/.env" 2>/dev/null; then
        INSTALL_ASSISTANT=true
    fi
    if grep -q "GOOGLE_CREDENTIALS_FILE" "$NICO_DIR/.env" 2>/dev/null; then
        INSTALL_GOOGLE_API=true
    fi
else
    echo "No .env found — run setup after install."
fi

if $INSTALL_ASSISTANT && ! $INSTALL_GOOGLE_API; then
    MODE="assistant"
elif $INSTALL_GOOGLE_API && ! $INSTALL_ASSISTANT; then
    MODE="google"
elif $INSTALL_ASSISTANT && $INSTALL_GOOGLE_API; then
    MODE="assistant"  # prefer assistant by default
else
    MODE="none"
fi

if [ "$MODE" = "assistant" ]; then
    echo "Installing Google Assistant SDK..."
    pip install google-assistant-grpc grpcio 'protobuf>=3.20,<4.0'
elif [ "$MODE" = "google" ]; then
    echo "Installing Google API client..."
    pip install google-api-python-client google-auth-oauthlib
fi

echo ""

# ── 5. Environment setup ─────────────────────
echo "[5/6] Setting up environment..."

if [ ! -f "$NICO_DIR/.env" ]; then
    cp "$NICO_DIR/.env.example" "$NICO_DIR/.env"
    echo "Created .env from .env.example — edit it with your API keys:"
    echo "  nano $NICO_DIR/.env"
    echo ""
fi

# Create files root
mkdir -p "$NICO_DIR/nico_files"

echo ""

# ── 6. Test installation ─────────────────────
echo "[6/6] Testing installation..."

python -c "
import nico
from nico.hardware.sensors import SensorMonitor
s = SensorMonitor()
import asyncio
r = asyncio.run(s.read_temperature())
print(f'CPU temperature: {r}')
"

echo ""
echo "=== Install complete! ==="
echo ""
echo "To start NICO:"
echo "  cd $NICO_DIR"
echo "  source .venv/bin/activate"
echo "  python main.py"
echo ""
echo "Or autostart on boot:"
echo "  sudo systemctl enable $NICO_DIR/nico.service"
echo "  sudo systemctl start nico"
echo ""
