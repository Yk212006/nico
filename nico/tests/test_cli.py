import tempfile
from pathlib import Path

from nico.cli import build_parser


def test_cli_parser_supports_run_and_chat_modes() -> None:
    parser = build_parser()
    args = parser.parse_args(["run", "--provider", "claude"])

    assert args.command == "run"
    assert args.provider == "claude"


def test_cli_parser_chat_with_image_flag() -> None:
    parser = build_parser()
    args = parser.parse_args(["chat", "describe this", "--image", "/tmp/photo.jpg"])

    assert args.command == "chat"
    assert args.message == "describe this"
    assert args.image == "/tmp/photo.jpg"


def test_cli_parser_analyze_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["analyze", "/tmp/photo.jpg", "--prompt", "what is this?"])

    assert args.command == "analyze"
    assert args.image == "/tmp/photo.jpg"
    assert args.prompt == "what is this?"


def test_cli_parser_analyze_default_prompt() -> None:
    parser = build_parser()
    args = parser.parse_args(["analyze", "img.png"])

    assert args.command == "analyze"
    assert args.image == "img.png"
    assert args.prompt == "Describe this image in detail"


def test_cli_analyze_reports_missing_file() -> None:
    from nico.cli import main

    exit_code = main(["analyze", "/nonexistent/image.jpg"])
    assert exit_code == 1


def test_cli_chat_image_reports_missing_file() -> None:
    from nico.cli import main

    exit_code = main(["chat", "describe", "--image", "/nonexistent/image.jpg"])
    assert exit_code == 1
