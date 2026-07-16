import os

from nico.pi_runtime import build_pi_settings, is_raspberry_pi


def test_build_pi_settings_uses_pi_defaults(monkeypatch) -> None:
    monkeypatch.delenv("NICO_ASSISTANT_NAME", raising=False)
    monkeypatch.setenv("NICO_ENABLE_TOOLS", "true")
    monkeypatch.setenv("NICO_ENABLE_MEMORY", "false")

    settings = build_pi_settings()

    assert settings.assistant_name == "NICO Pi"
    assert settings.enable_tools is True
    assert settings.enable_memory is False


def test_is_raspberry_pi_returns_false_on_non_pi_arm(monkeypatch) -> None:
    monkeypatch.setattr("nico.pi_runtime.platform.machine", lambda: "armv7l")
    monkeypatch.setattr("nico.pi_runtime._read_device_tree_model", lambda: "")
    monkeypatch.setattr("nico.pi_runtime.os.path.exists", lambda _: False)

    assert is_raspberry_pi() is False


def test_is_raspberry_pi_detects_device_tree_model(monkeypatch) -> None:
    monkeypatch.setattr("nico.pi_runtime.platform.machine", lambda: "aarch64")
    monkeypatch.setattr("nico.pi_runtime._read_device_tree_model", lambda: "raspberry pi 3 model b plus")

    assert is_raspberry_pi() is True


def test_is_raspberry_pi_detects_gpiomem_fallback(monkeypatch) -> None:
    monkeypatch.setattr("nico.pi_runtime.platform.machine", lambda: "armv7l")
    monkeypatch.setattr("nico.pi_runtime._read_device_tree_model", lambda: "")
    monkeypatch.setattr("nico.pi_runtime.os.path.exists", lambda p: p == "/dev/gpiomem")

    assert is_raspberry_pi() is True
