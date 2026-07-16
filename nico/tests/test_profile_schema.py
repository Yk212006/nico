import pytest

from nico.config_profiles import load_profile_from_file, validate_profile


def test_validate_profile_rejects_unknown_provider(tmp_path) -> None:
    profile_file = tmp_path / "profile.json"
    profile_file.write_text('{"provider": "unknown", "enable_tools": true, "enable_memory": true}', encoding="utf-8")

    with pytest.raises(ValueError):
        validate_profile(load_profile_from_file(profile_file))
