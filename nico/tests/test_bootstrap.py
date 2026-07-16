from nico.bootstrap import AppBootstrap


class FakeService:
    def __init__(self, name: str) -> None:
        self.name = name


def test_bootstrap_registers_services_from_config() -> None:
    bootstrap = AppBootstrap({"demo": FakeService("demo")})

    assert bootstrap.registry.resolve("demo").name == "demo"
