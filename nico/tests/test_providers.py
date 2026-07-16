import asyncio

from nico.brain.openai_provider import OpenAIProvider


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


def test_openai_provider_uses_api_response(monkeypatch) -> None:
    mock_client = MockAsyncClient(
        DummyResponse({"choices": [{"message": {"content": "Hello from API"}}]})
    )

    def fake_async_client(*args: object, **kwargs: object) -> MockAsyncClient:
        return mock_client

    monkeypatch.setattr("nico.brain.openai_provider.httpx.AsyncClient", fake_async_client)

    provider = OpenAIProvider(api_key="test-key")
    response = asyncio.run(provider.chat("hi"))

    assert response == "Hello from API"
    assert mock_client.captured["headers"]["Authorization"] == "Bearer test-key"
