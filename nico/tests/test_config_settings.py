from nico.config.settings import Settings


def test_settings_default_name() -> None:
    settings = Settings()
    assert settings.assistant_name == "NICO"


def test_settings_default_provider() -> None:
    settings = Settings()
    assert settings.default_provider == "openai"


def test_settings_default_log_level() -> None:
    settings = Settings()
    assert settings.log_level == "INFO"


def test_settings_tools_enabled_by_default() -> None:
    settings = Settings()
    assert settings.enable_tools is True


def test_settings_from_env() -> None:
    settings = Settings.from_env()
    assert isinstance(settings, Settings)
    assert settings.assistant_name == "NICO"
