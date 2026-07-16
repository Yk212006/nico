import asyncio

import pytest

from nico.brain.claude_provider import ClaudeProvider
from nico.brain.gemini_provider import GeminiProvider
from nico.brain.openai_provider import OpenAIProvider
from nico.brain.provider import BaseProvider, ProviderCapabilities, detect_capabilities


class _StubOnlyProvider(BaseProvider):
    """A provider that only implements the required abstract methods."""

    name = "stub"

    async def chat(self, prompt, *, history=None):
        return f"stub: {prompt}"

    async def vision(self, prompt, image_bytes):
        return "stub vision"

    async def speech(self, text):
        return text.encode("utf-8")


@pytest.mark.parametrize("provider_cls", [ClaudeProvider, OpenAIProvider, GeminiProvider])
def test_concrete_providers_report_full_capabilities(provider_cls) -> None:
    provider = provider_cls(api_key="fake-key")
    caps = provider.capabilities

    assert isinstance(caps, ProviderCapabilities)
    assert caps.chat is True
    assert caps.streaming is True
    assert caps.vision is True
    assert caps.tool_calling is True
    assert caps.structured_output is True


def test_minimal_provider_reports_only_chat_and_vision() -> None:
    caps = detect_capabilities(_StubOnlyProvider())

    assert caps.chat is True
    assert caps.vision is True
    assert caps.streaming is False
    assert caps.tool_calling is False
    assert caps.structured_output is False


def test_minimal_provider_stream_chat_falls_back_to_chat() -> None:
    async def _collect():
        provider = _StubOnlyProvider()
        chunks = [chunk async for chunk in provider.stream_chat("hi")]
        return chunks

    chunks = asyncio.run(_collect())
    assert chunks == ["stub: hi"]


class MockStreamResponse:
    def __init__(self) -> None:
        self._lines = [
            'data: {"choices": [{"delta": {"content": "Hel"}}]}',
            'data: {"choices": [{"delta": {"content": "lo"}}]}',
            "data: [DONE]",
        ]

    def raise_for_status(self) -> None:
        return None

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class MockStreamContext:
    async def __aenter__(self) -> MockStreamResponse:
        return MockStreamResponse()

    async def __aexit__(self, *args: object) -> None:
        pass


class MockAsyncStreamClient:
    async def __aenter__(self) -> "MockAsyncStreamClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    def stream(self, method: str, url: str, *, headers: dict | None = None, json: dict | None = None, timeout: float | None = None) -> MockStreamContext:  # noqa: ARG002
        assert method == "POST"
        return MockStreamContext()


def test_openai_stream_chat_yields_sse_deltas(monkeypatch) -> None:
    def fake_async_client(*args: object, **kwargs: object) -> MockAsyncStreamClient:
        return MockAsyncStreamClient()

    monkeypatch.setattr("nico.brain.openai_provider.httpx.AsyncClient", fake_async_client)

    async def _collect():
        provider = OpenAIProvider(api_key="test-key")
        return [chunk async for chunk in provider.stream_chat("hi")]

    chunks = asyncio.run(_collect())
    assert "".join(chunks) == "Hello"


class MockToolResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "content": [
                {"type": "text", "text": "Let me check that."},
                {"type": "tool_use", "id": "call_1", "name": "get_weather", "input": {"city": "Boston"}},
            ]
        }


class MockAsyncToolClient:
    async def __aenter__(self) -> "MockAsyncToolClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def post(self, url: str, *, headers: dict | None = None, json: dict | None = None, timeout: float | None = None) -> MockToolResponse:  # noqa: ARG002
        assert json is not None and "tools" in json
        return MockToolResponse()


def test_claude_chat_with_tools_parses_tool_use_blocks(monkeypatch) -> None:
    def fake_async_client(*args: object, **kwargs: object) -> MockAsyncToolClient:
        return MockAsyncToolClient()

    monkeypatch.setattr("nico.brain.claude_provider.httpx.AsyncClient", fake_async_client)

    provider = ClaudeProvider(api_key="claude-key")
    result = asyncio.run(
        provider.chat_with_tools(
            "what's the weather",
            tools=[{"name": "get_weather", "input_schema": {"type": "object"}}],
        )
    )

    assert result["content"] == "Let me check that."
    assert result["tool_calls"] == [{"id": "call_1", "name": "get_weather", "input": {"city": "Boston"}}]


def test_chat_with_tools_without_tools_falls_back_to_plain_chat() -> None:
    provider = OpenAIProvider(api_key=None)  # no key -> stub path
    result = asyncio.run(provider.chat_with_tools("hi", tools=None))

    assert result == {"content": "OpenAI response to: hi", "tool_calls": []}
