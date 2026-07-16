from pathlib import Path

from nico.config_profiles import load_profile_from_file


def test_load_profile_from_file_reads_json(tmp_path: Path) -> None:
    profile_file = tmp_path / "profile.json"
    profile_file.write_text('{"provider": "claude", "enable_tools": false, "enable_memory": true}', encoding="utf-8")

    profile = load_profile_from_file(profile_file)

    assert profile["provider"] == "claude"
    assert profile["enable_tools"] is False
