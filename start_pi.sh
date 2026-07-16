#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# Activate virtual environment if present
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
elif [ -f venv/bin/activate ]; then
    source venv/bin/activate
fi

# Verify core dependency
python3 -c "import httpx" 2>/dev/null || {
    echo "NICO: Missing core dependencies. Run: pip install -e ."
    exit 1
}

exec python3 main.py
