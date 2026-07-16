import asyncio

from nico.cli import main


def test_cli_chat_invokes_app_runtime(capsys) -> None:
    exit_code = main(["chat", "hello", "--profile-file", "profiles/default.json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "status=ready" in captured.out
    assert "provider=openai" in captured.out
