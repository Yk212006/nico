import pytest

from nico.tools.email.email_tool import EmailTool


@pytest.mark.asyncio
async def test_email_list_offline() -> None:
    tool = EmailTool()
    result = await tool.execute(action="list")
    assert "status" in result
    assert result["status"] == "unavailable"


@pytest.mark.asyncio
async def test_email_send_requires_confirmation() -> None:
    tool = EmailTool()
    result = await tool.execute(action="send", subject="test", body="body")
    assert result["status"] == "requires_confirmation"


@pytest.mark.asyncio
async def test_email_send_missing_recipient() -> None:
    tool = EmailTool()
    result = await tool.execute(action="send", subject="test", body="body", confirmed=True)
    assert "error" in result


@pytest.mark.asyncio
async def test_email_unknown_action() -> None:
    tool = EmailTool()
    result = await tool.execute(action="unknown")
    assert "error" in result
