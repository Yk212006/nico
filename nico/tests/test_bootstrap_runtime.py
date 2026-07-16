from nico.bootstrap import AppBootstrap
from nico.app import NicoApp
from nico.config.settings import Settings


def test_bootstrap_can_initialize_app_instance() -> None:
    bootstrap = AppBootstrap()
    app = bootstrap.create_app(settings=Settings(default_provider="openai"))

    assert isinstance(app, NicoApp)
    assert app.settings.default_provider == "openai"
