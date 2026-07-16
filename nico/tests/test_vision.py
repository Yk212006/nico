import asyncio
import tempfile
from pathlib import Path

import pytest

from nico.app import NicoApp
from nico.brain.provider import BaseProvider
from nico.brain.router import ProviderRouter
from nico.config.settings import Settings
from nico.tools.vision.describe_image import DescribeImageTool


class FakeVisionProvider(BaseProvider):
    name = "test_vision"
    async def chat(self, prompt: str, **kwargs) -> str:
        return ""
    async def stream_chat(self, prompt: str, **kwargs):
        yield ""
    async def vision(self, prompt: str, image_bytes: bytes) -> str:
        return f"[Vision] {prompt}: {len(image_bytes)} bytes analyzed"
    async def speech(self, text: str) -> bytes:
        return b""
    async def chat_with_tools(self, prompt: str, **kwargs):
        return {"content": "", "tool_calls": []}


@pytest.fixture
def router():
    return ProviderRouter(
        providers={"test": FakeVisionProvider()},
        default_provider="test",
    )


def test_router_vision_returns_analysis(router):
    result = asyncio.run(router.vision("what is this?", b"fake_image_bytes"))
    assert "Vision" in result
    assert "bytes analyzed" in result


def test_router_vision_raises_on_empty_response():
    class EmptyVisionProvider(FakeVisionProvider):
        async def vision(self, prompt: str, image_bytes: bytes) -> str:
            return ""

    router = ProviderRouter(
        providers={"empty": EmptyVisionProvider()},
        default_provider="empty",
    )
    with pytest.raises(RuntimeError, match="All providers failed"):
        asyncio.run(router.vision("test", b"data"))


@pytest.mark.asyncio
async def test_describe_image_tool_analyzes_file(router):
    tool = DescribeImageTool(router=router)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(b"fake_image_data")
        tmp_path = f.name

    try:
        result = await tool.execute(image_path=tmp_path, prompt="describe")
        assert "Vision" in result
        assert "describe" in result
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_describe_image_tool_missing_file(router):
    tool = DescribeImageTool(router=router)
    result = await tool.execute(image_path="/nonexistent/path.jpg")
    assert "not found" in result


@pytest.mark.asyncio
async def test_describe_image_tool_no_router():
    tool = DescribeImageTool(router=None)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(b"data")
        tmp_path = f.name

    try:
        result = await tool.execute(image_path=tmp_path)
        assert "no AI provider configured" in result
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_describe_image_tool_read_error(router):
    tool = DescribeImageTool(router=router)
    result = await tool.execute(image_path="C:\\")
    assert "Error reading image" in result or "not a file" in result


@pytest.mark.asyncio
async def test_app_analyze_image():
    app = NicoApp(settings=Settings(default_provider="openai"))
    app.router = ProviderRouter(
        providers={"test": FakeVisionProvider()},
        default_provider="test",
    )
    result = await app.analyze_image(b"test_bytes", prompt="what?")
    assert "Vision" in result


def test_describe_image_tool_registered_in_manager():
    app = NicoApp(settings=Settings(default_provider="openai"))
    tool_names = [t.name for t in app.tool_manager.list_tools()]
    assert "describe_image" in tool_names


def test_orchestrator_routes_image_intent():
    from nico.orchestrator import IntentOrchestrator
    from nico.tools.manager import ToolManager

    orch = IntentOrchestrator(ToolManager())
    result = asyncio.run(orch.handle("describe this image at /tmp/photo.jpg"))
    assert result["intent"] == "tool"
    assert result["tool_name"] == "describe_image"
    assert result["tool_kwargs"]["image_path"] == "/tmp/photo.jpg"


def test_orchestrator_routes_photo_intent():
    from nico.orchestrator import IntentOrchestrator
    from nico.tools.manager import ToolManager

    orch = IntentOrchestrator(ToolManager())
    result = asyncio.run(orch.handle("what's in this photo"))
    assert result["intent"] == "tool"
    assert result["tool_name"] == "describe_image"


def test_orchestrator_does_not_route_unrelated():
    from nico.orchestrator import IntentOrchestrator
    from nico.tools.manager import ToolManager

    orch = IntentOrchestrator(ToolManager())
    result = asyncio.run(orch.handle("hello how are you"))
    assert result["intent"] != "tool"
