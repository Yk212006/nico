#!/usr/bin/env bash
# Launches NICO GUI without terminal window
cd "$(dirname "$0")"

# Activate venv
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
elif [ -f venv/bin/activate ]; then
    source venv/bin/activate
fi

python -m nico.gui
