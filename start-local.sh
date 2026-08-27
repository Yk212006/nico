#!/usr/bin/env bash
set -euo pipefail

export NICO_PROFILE="${NICO_PROFILE:-local}"
export NICO_DEFAULT_PROVIDER="${NICO_DEFAULT_PROVIDER:-ollama}"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5:3b}"
python -m nico.local_launcher "$@"
