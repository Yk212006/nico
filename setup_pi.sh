#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────────────────
# NICO Smart Speaker — Raspberry Pi Setup
# Run this ONCE on Raspberry Pi OS (Desktop, 64-bit)
# ──────────────────────────────────────────────────────────

PI_USER="${SUDO_USER:-pi}"
PI_HOME="/home/${PI_USER}"
NICO_DIR="${PI_HOME}/nico"

echo "=== 1. System packages ==="
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
  python3-pip python3-venv python3-full \
  portaudio19-dev pulseaudio pulseaudio-module-bluetooth \
  bluez bluez-tools pi-bluetooth libbluetooth-dev \
  libatlas-base-dev

echo "=== 2. Add user to bluetooth group ==="
sudo usermod -a -G bluetooth "${PI_USER}"

echo "=== 3. Clone NICO (if not already cloned) ==="
if [ ! -d "${NICO_DIR}" ]; then
  # Replace with your repo URL
  echo "Clone your repository to ${NICO_DIR} first, then re-run."
  echo "Example: git clone <your-repo> ${NICO_DIR}"
  exit 1
fi

echo "=== 4. Python virtual environment ==="
cd "${NICO_DIR}"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel setuptools
pip install -e ".[pi]"

echo "=== 5. Install Picovoice Porcupine (wake word) ==="
pip install pvporcupine

echo "=== 6. Create .env file ==="
if [ ! -f "${NICO_DIR}/.env" ]; then
  cat > "${NICO_DIR}/.env" << 'ENVEOF'
NICO_DEFAULT_PROVIDER=google_assistant
GOOGLE_CREDENTIALS_FILE=/home/pi/nico/credentials.json
GOOGLE_ASSISTANT_DEVICE_MODEL_ID=your-model-id
GOOGLE_ASSISTANT_DEVICE_ID=your-device-id
GOOGLE_ASSISTANT_LANGUAGE_CODE=en-IN

STT_PROVIDER=whisper_openai
OPENAI_API_KEY=sk-...       # <-- fill me
TTS_PROVIDER=gtts
OPENWEATHERMAP_API_KEY=...  # <-- fill me

NICO_ENABLE_VOICE=true
PICOVOICE_ACCESS_KEY=       # <-- fill me (free at console.picovoice.ai)
WAKE_WORD=hey nico
NICO_ASSISTANT_NAME=NICO
NICO_LOG_LEVEL=INFO
NICO_ENABLE_MEMORY=false
NICO_ENABLE_TOOLS=true
NICO_ALLOW_SYSTEM_CONTROL=false
ENVEOF
  echo ".env created — edit it to add your API keys"
else
  echo ".env already exists"
fi

echo ""
echo "=== DONE ==="
echo ""
echo "Next steps:"
echo "  1. Edit ${NICO_DIR}/.env — add your API keys"
echo "  2. Copy credentials.json to ${NICO_DIR}/"
echo "  3. Run the Google Assistant OAuth setup:"
echo "     cd ${NICO_DIR}"
echo "     python setup_assistant.py"
echo "     python get_assistant_token.py"
echo "  4. Connect bluetooth speaker:"
echo "     bluetoothctl"
echo "     Then: power on → scan on → pair <MAC> → trust <MAC> → connect <MAC>"
echo "     Then exit bluetoothctl"
echo "  5. Set bluetooth speaker as default audio OUTPUT:"
echo "     pactl set-card-profile bluez_card.XX_XX_XX_XX_XX_XX a2dp_sink"
echo "     pactl set-default-sink bluez_sink.XX_XX_XX_XX_XX_XX.a2dp_sink"
echo "  6. Verify USB mic is your default INPUT:"
echo "     pactl set-default-source \"alsa_input.usb-...\""
echo "     pactl list sources short   # should show your USB mic"
echo "  7. Test audio:"
echo "     arecord -d 3 test.wav && aplay test.wav    # mic → speaker"
echo "  8. Run NICO:"
echo "     cd ${NICO_DIR} && source .venv/bin/activate && python main.py"
echo ""
echo "  9. (Optional) Enable auto-start:"
echo "     sudo cp nico.service /etc/systemd/system/"
echo "     sudo systemctl enable nico && sudo systemctl start nico"
