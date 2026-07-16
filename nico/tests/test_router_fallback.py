import asyncio

import pytest

from nico.brain.router import ProviderRouter


class ScriptedProvider:
    """A fake provider whose chat() behavior is scripted per call."""

    def __init__(self, name: str, behaviors: list) -> None:
        self.name = name
        self._behaviors = list(behaviors)
        self.calls = 0

    async def chat(self, prompt, *, history=None):
        self.calls += 1
        behavior = self._behaviors.pop(0) if self._behaviors else "ok"
        if behavior == "fail":
            raise RuntimeError(f"{self.name} is down")
        if behavior == "empty":
            return ""
        return f"{self.name}: {prompt}"


def test_router_falls_back_to_next_provider_on_failure() -> None:
    primary = ScriptedProvider("openai", ["fail"])
    backup = ScriptedProvider("claude", ["ok"])
    router = ProviderRouter(
        {"openai": primary, "claude": backup},
        default_provider="openai",
        fallback_order=["openai", "claude"],
    )

    response = asyncio.run(router.chat("hello"))

    assert response == "claude: hello"
    assert router.health["openai"].consecutive_failures == 1
    assert router.health["claude"].healthy is True


def test_router_marks_provider_unhealthy_after_repeated_failures_and_prefers_healthy_ones() -> None:
    flaky = ScriptedProvider("openai", ["fail", "fail"])
    backup = ScriptedProvider("claude", ["ok", "ok"])
    router = ProviderRouter(
        {"openai": flaky, "claude": backup},
        default_provider="openai",
        fallback_order=["openai", "claude"],
        unhealthy_after=2,
    )

    asyncio.run(router.chat("first"))
    assert router.health["openai"].healthy is True  # only 1 failure so far

    asyncio.run(router.chat("second"))
    assert router.health["openai"].healthy is False  # 2 failures -> unhealthy

    # Once unhealthy, a fresh request should try the healthy provider first.
    third = asyncio.run(router.chat("third"))
    assert third.startswith("claude:")


def test_router_raises_when_all_providers_fail() -> None:
    a = ScriptedProvider("openai", ["fail"])
    b = ScriptedProvider("claude", ["fail"])
    router = ProviderRouter({"openai": a, "claude": b}, default_provider="openai")

    with pytest.raises(RuntimeError):
        asyncio.run(router.chat("hello"))


def test_router_health_check_reports_status_per_provider() -> None:
    a = ScriptedProvider("openai", ["ok"])
    b = ScriptedProvider("claude", ["fail"])
    router = ProviderRouter({"openai": a, "claude": b}, default_provider="openai")

    results = asyncio.run(router.health_check())

    assert results == {"openai": True, "claude": False}
    assert router.health["claude"].last_error == "claude is down"
