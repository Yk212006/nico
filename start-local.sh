#!/usr/bin/env bash
set -euo pipefail

export NICO_PROFILE="${NICO_PROFILE:-local}"
export NICO_DEFAULT_PROVIDER="${NICO_DEFAULT_PROVIDER:-ollama}"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5:3b}"

if command -v ollama >/dev/null 2>&1; then
  if ! pgrep -x ollama >/dev/null 2>&1; then
    ollama serve >/dev/null 2>&1 &
    sleep 3
  fi
fi

python -m nico.webui
