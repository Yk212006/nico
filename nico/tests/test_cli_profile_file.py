from nico.cli import build_parser, main


def test_cli_accepts_profile_file_path(capsys) -> None:
    parser = build_parser()
    args = parser.parse_args(["chat", "hello", "--profile-file", "profiles/default.json"])

    assert args.profile_file == "profiles/default.json"
