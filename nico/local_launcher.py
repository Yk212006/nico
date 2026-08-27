from __future__ import annotations

import argparse
import os
import socket
import subprocess
import time


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def _start_ollama_if_needed() -> None:
    if _port_open("127.0.0.1", 11434):
        return

    ollama = os.environ.get("OLLAMA_CMD") or "ollama"
    try:
        subprocess.Popen(
            [ollama, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError:
        return

    for _ in range(20):
        if _port_open("127.0.0.1", 11434):
            return
        time.sleep(0.25)


def main() -> None:
    parser = argparse.ArgumentParser(description="NICO local launcher")
    parser.add_argument("--lan", action="store_true", help="Allow other devices on the local network to connect")
    parser.add_argument("--local-only", action="store_true", help="Bind only to localhost (default)")
    parser.add_argument("--port", type=int, default=int(os.getenv("NICO_WEB_PORT", "8080")), help="Web UI port")
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "qwen2.5:3b"), help="Ollama model name")
    args = parser.parse_args()

    os.environ.setdefault("NICO_PROFILE", "local")
    os.environ.setdefault("NICO_DEFAULT_PROVIDER", "ollama")
    os.environ.setdefault("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    os.environ["OLLAMA_MODEL"] = args.model
    os.environ["NICO_WEB_PORT"] = str(args.port)
    if args.local_only:
        os.environ["NICO_BIND_HOST"] = "127.0.0.1"
    elif args.lan:
        os.environ["NICO_BIND_HOST"] = "0.0.0.0"
    else:
        os.environ["NICO_BIND_HOST"] = "127.0.0.1"

    _start_ollama_if_needed()

    from nico.webui import main as web_main

    web_main()


if __name__ == "__main__":
    main()
