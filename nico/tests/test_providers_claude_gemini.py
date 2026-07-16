import asyncio

from nico.brain.claude_provider import ClaudeProvider
from nico.brain.gemini_provider import GeminiProvider


class DummyResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("request failed")

    def json(self) -> dict:
        return self._payload


class MockAsyncClient:
    def __init__(self, response: DummyResponse) -> None:
        self._response = response
        self.captured: dict[str, object] = {}

    async def __aenter__(self) -> "MockAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def post(self, url: str, *, headers: dict[str, str] | None = None, json: dict | None = None, timeout: float = 10.0) -> DummyResponse:  # noqa: ARG002
        self.captured["url"] = url
        self.captured["headers"] = headers
        self.captured["json"] = json
        return self._response


def test_claude_provider_uses_api_response(monkeypatch) -> None:
    mock_client = MockAsyncClient(
        DummyResponse({"content": [{"text": "Hello from Claude"}]})
    )

    def fake_async_client(*args: object, **kwargs: object) -> MockAsyncClient:
        return mock_client

    monkeypatch.setattr("nico.brain.claude_provider.httpx.AsyncClient", fake_async_client)

    provider = ClaudeProvider(api_key="claude-key")
    response = asyncio.run(provider.chat("hi"))

    assert response == "Hello from Claude"
    assert mock_client.captured["headers"]["x-api-key"] == "claude-key"


def test_gemini_provider_uses_api_response(monkeypatch) -> None:
    mock_client = MockAsyncClient(
        DummyResponse({"candidates": [{"content": {"parts": [{"text": "Hello from Gemini"}]}}]})
    )

    def fake_async_client(*args: object, **kwargs: object) -> MockAsyncClient:
        return mock_client

    monkeypatch.setattr("nico.brain.gemini_provider.httpx.AsyncClient", fake_async_client)

    provider = GeminiProvider(api_key="gemini-key")
    response = asyncio.run(provider.chat("hi"))

    assert response == "Hello from Gemini"
    headers = mock_client.captured.get("headers", {})
    assert headers.get("X-Goog-Api-Key") == "gemini-key"
