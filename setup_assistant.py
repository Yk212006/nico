"""One-time setup script for Google Assistant integration.

Run this to:
1. Register device model and device in Google Assistant
2. Generate OAuth token for the assistant-sdk-prototype scope

Usage:
    python setup_assistant.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ID = "optimum-legacy-502917-s8"
MODEL_ID = "nico-assistant-v1"
DEVICE_ID = "nico-device-1"
SCOPE = "https://www.googleapis.com/auth/assistant-sdk-prototype"


def step(msg: str) -> None:
    print(f"\n=== {msg} ===")


def main() -> None:
    print("Google Assistant Setup for Nico")
    print("================================")

    # Step 1: Register device model
    step("Registering device model")
    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "googlesamples.assistant.devicetool",
                "--project-id", PROJECT_ID,
                "register-model",
                "--model", MODEL_ID,
                "--type", "LIGHT",
                "--trait", "action.devices.traits.OnOff",
                "--manufacturer", "Nico",
                "--product-name", "Nico Assistant",
                "--description", "Nico AI assistant device control",
            ],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            print(f"  Device model '{MODEL_ID}' registered successfully.")
        else:
            if "already exists" in result.stderr:
                print(f"  Device model '{MODEL_ID}' already exists (OK).")
            else:
                print(f"  Warning: {result.stderr.strip()}")
    except FileNotFoundError:
        print("  Skipped - devicetool not available. Register manually at:")
        print(f"  https://console.home.google.com/projects/{PROJECT_ID}")
    except Exception as exc:
        print(f"  Skipped - {exc}")

    # Step 2: Register device instance
    step("Registering device instance")
    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "googlesamples.assistant.devicetool",
                "--project-id", PROJECT_ID,
                "register-device",
                "--device", DEVICE_ID,
                "--model", MODEL_ID,
                "--nickname", "Nico",
            ],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            print(f"  Device '{DEVICE_ID}' registered successfully.")
        else:
            if "already exists" in result.stderr:
                print(f"  Device '{DEVICE_ID}' already exists (OK).")
            else:
                print(f"  Warning: {result.stderr.strip()}")
    except Exception as exc:
        print(f"  Skipped - {exc}")

    # Step 3: Generate OAuth token
    step("Generating OAuth token")
    token_path = os.path.expanduser("~/.nico/assistant_token.json")
    creds_file = "credentials.json"

    if not os.path.exists(creds_file):
        print(f"  Error: {creds_file} not found in current directory.")
        print("  Make sure credentials.json is in the project root.")
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow

        os.makedirs(os.path.dirname(token_path), exist_ok=True)

        flow = InstalledAppFlow.from_client_secrets_file(creds_file, [SCOPE])
        creds = flow.run_local_server(port=0, open_browser=True)

        with open(token_path, "w") as f:
            f.write(creds.to_json())

        print(f"  Token saved to: {token_path}")
        print(f"  Access token: {creds.token[:50]}...")
    except ImportError:
        print("  google-auth-oauthlib not installed. Run:")
        print("  pip install google-auth-oauthlib")
    except Exception as exc:
        print(f"  OAuth flow failed: {exc}")

    # Step 4: Print environment setup
    step("Environment setup")
    print("Add these to your .env file:")
    print()
    print(f"GOOGLE_CREDENTIALS_FILE=credentials.json")
    print(f"GOOGLE_ASSISTANT_DEVICE_MODEL_ID={MODEL_ID}")
    print(f"GOOGLE_ASSISTANT_DEVICE_ID={DEVICE_ID}")
    print()
    print("Or set them in your shell:")
    print(f"  $env:GOOGLE_CREDENTIALS_FILE='credentials.json'")
    print(f"  $env:GOOGLE_ASSISTANT_DEVICE_MODEL_ID='{MODEL_ID}'")
    print(f"  $env:GOOGLE_ASSISTANT_DEVICE_ID='{DEVICE_ID}'")
    print()
    print("Done! Run 'python main.py' and try: 'turn on the living room light'")


if __name__ == "__main__":
    main()
