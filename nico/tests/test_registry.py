from nico.registry import ServiceRegistry


class DummyService:
    def __init__(self, name: str) -> None:
        self.name = name


def test_service_registry_registers_and_resolves_services() -> None:
    registry = ServiceRegistry()
    registry.register("demo", DummyService("demo"))

    assert registry.resolve("demo").name == "demo"
