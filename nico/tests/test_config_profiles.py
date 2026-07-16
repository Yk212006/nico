from nico.config_profiles import load_profile


def test_load_profile_returns_expected_settings() -> None:
    profile = load_profile("default")

    assert profile["provider"] == "openai"
    assert profile["enable_tools"] is True
