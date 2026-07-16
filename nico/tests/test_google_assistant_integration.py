import os

import pytest

from nico.integrations.google_assistant.assistant import GoogleAssistantIntegration


@pytest.mark.asyncio
async def test_assistant_reports_unavailable_when_missing_deps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_CREDENTIALS_FILE", raising=False)
    monkeypatch.delenv("GOOGLE_ASSISTANT_DEVICE_MODEL_ID", raising=False)
    monkeypatch.delenv("GOOGLE_ASSISTANT_DEVICE_ID", raising=False)
    integration = GoogleAssistantIntegration(
        credentials_file=None,
        device_model_id=None,
        device_id=None,
    )
    result = await integration.send_command("turn on the light")

    assert result["status"] == "unavailable"
    assert isinstance(result["missing"], list)
    assert len(result["missing"]) > 0


@pytest.mark.asyncio
async def test_assistant_reports_unconfigured_when_no_creds() -> None:
    integration = GoogleAssistantIntegration(
        credentials_file="/nonexistent/creds.json",
        token_file="/tmp/test_token.json",
        device_model_id="test-model",
        device_id="test-device",
    )

    if integration.available:
        result = await integration.send_command("turn on the light")
        assert result["status"] in ("unconfigured", "unavailable")
