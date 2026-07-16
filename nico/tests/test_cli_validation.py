import pytest

from nico.cli import build_parser, main


def test_cli_rejects_invalid_profile(capsys) -> None:
    with pytest.raises(SystemExit):
        main(["run", "--profile", "invalid"])

    captured = capsys.readouterr()
    assert "invalid profile" in captured.err.lower()
