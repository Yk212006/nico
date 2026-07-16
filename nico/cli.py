from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Sequence

from nico.app import NicoApp
from nico.config.settings import Settings
from nico.config_profiles import load_profile, load_profile_from_file, validate_profile


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI command parser for NICO modes."""

    parser = argparse.ArgumentParser(prog="nico", description="NICO Assistant Command Line Interface")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Start the assistant in interactive shell/REPL mode")
    run_parser.add_argument("--provider", default=None, help="Force default AI provider to use")
    run_parser.add_argument("--profile", default="default", help="Preset profile configuration profile to load")
    run_parser.add_argument("--profile-file", default=None, help="Path to a custom JSON profile file")
    run_parser.add_argument("--no-tools", action="store_true", help="Disable tool execution")

    chat_parser = subparsers.add_parser("chat", help="Send a one-shot query message and print response")
    chat_parser.add_argument("message", help="Query message string to process")
    chat_parser.add_argument("--provider", default=None, help="Force default AI provider to use")
    chat_parser.add_argument("--profile", default="default", help="Preset profile configuration profile to load")
    chat_parser.add_argument("--profile-file", default=None, help="Path to a custom JSON profile file")
    chat_parser.add_argument("--image", default=None, help="Path to an image file for vision analysis")

    analyze_parser = subparsers.add_parser("analyze", help="Analyze an image using AI vision")
    analyze_parser.add_argument("image", help="Path to the image file")
    analyze_parser.add_argument("--prompt", default="Describe this image in detail", help="Analysis prompt")
    analyze_parser.add_argument("--provider", default=None, help="Force default AI provider to use")
    analyze_parser.add_argument("--profile", default="default", help="Preset profile configuration")
    analyze_parser.add_argument("--profile-file", default=None, help="Path to a custom JSON profile file")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if not args.command:
        parser.print_help()
        return 0

    # 1. Load active profile
    try:
        if args.profile_file:
            profile = validate_profile(load_profile_from_file(args.profile_file))
        else:
            profile = validate_profile(load_profile(args.profile))
    except (KeyError, ValueError, FileNotFoundError) as exc:
        parser.error(f"invalid profile: {exc}")
        return 1

    # Overrides
    provider = args.provider or profile["provider"]
    enable_tools = False if getattr(args, "no_tools", False) else profile["enable_tools"]
    enable_memory = profile["enable_memory"]

    settings = Settings(
        default_provider=provider,
        enable_tools=enable_tools,
        enable_memory=enable_memory,
    )
    app = NicoApp(settings=settings)

    # 2. Analyze image command
    if args.command == "analyze":
        image_path = Path(args.image)
        if not image_path.exists():
            print(f"Error: image not found at '{args.image}'")
            return 1
        image_bytes = image_path.read_bytes()
        response = asyncio.run(app.analyze_image(image_bytes, prompt=args.prompt))
        print(response)
        return 0

    # 3. One-shot chat command (optionally with image)
    if args.command == "chat":
        if args.image:
            image_path = Path(args.image)
            if not image_path.exists():
                print(f"Error: image not found at '{args.image}'")
                return 1
            image_bytes = image_path.read_bytes()
            response = asyncio.run(
                app.router.vision(args.message, image_bytes)
            )
        else:
            response = asyncio.run(app.chat(args.message))
        print(
            f"chat:{args.message}:{provider}:{enable_tools}:status=ready:provider={provider}:response={response}"
        )
        return 0

    # 4. Interactive run REPL command
    if args.command == "run":
        import sys
        # Run startup lifecycle
        asyncio.run(app.lifecycle.start())

        if not sys.stdin.isatty():
            # Support automated test environments / non-interactive shells
            response = asyncio.run(app.chat("hello from run"))
            print(
                f"run:{profile['provider']}:{profile['enable_tools']}:{args.no_tools}:status=ready:provider={profile['provider']}:response={response}"
            )
            asyncio.run(app.lifecycle.stop())
            return 0

        print(f"Starting {settings.assistant_name} (default_provider={provider}, tools={enable_tools})...")
        print("Type 'exit' or 'quit' to close the assistant. Switch providers with 'Use Claude' or 'Use Gemini'.")

        try:
            while True:
                try:
                    message = input("\nYou: ").strip()
                except (KeyboardInterrupt, EOFError):
                    break

                if not message:
                    continue

                if message.lower() in ("exit", "quit"):
                    break

                response = asyncio.run(app.chat(message))
                print(f"{settings.assistant_name}: {response}")
        finally:
            # Run shutdown lifecycle
            asyncio.run(app.lifecycle.stop())
        return 0

    parser.print_help()
    return 0
