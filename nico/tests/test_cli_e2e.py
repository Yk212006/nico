from nico.cli import main


def test_cli_e2e_with_profile_file(capsys) -> None:
    exit_code = main(["chat", "hello", "--profile-file", "profiles/default.json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "chat:hello:openai:True" in captured.out
