import pytest
import tempfile
from pathlib import Path

from nico.tools.files.files import FilesTool


@pytest.fixture
def sandbox() -> Path:
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.mark.asyncio
async def test_files_write_and_read(sandbox: Path) -> None:
    tool = FilesTool(files_root=str(sandbox))
    result = await tool.execute(action="write", path="test.txt", content="hello")
    assert result["status"] == "written"

    result = await tool.execute(action="read", path="test.txt")
    assert result["content"] == "hello"


@pytest.mark.asyncio
async def test_files_list(sandbox: Path) -> None:
    tool = FilesTool(files_root=str(sandbox))
    (sandbox / "a.txt").write_text("a")
    (sandbox / "b.txt").write_text("b")

    result = await tool.execute(action="list")
    assert len(result["entries"]) == 2
    names = [e["name"] for e in result["entries"]]
    assert "a.txt" in names
    assert "b.txt" in names


@pytest.mark.asyncio
async def test_files_exists(sandbox: Path) -> None:
    tool = FilesTool(files_root=str(sandbox))
    (sandbox / "exists.txt").write_text("here")

    result = await tool.execute(action="exists", path="exists.txt")
    assert result["exists"] is True

    result = await tool.execute(action="exists", path="missing.txt")
    assert result["exists"] is False


@pytest.mark.asyncio
async def test_files_delete_requires_confirmation(sandbox: Path) -> None:
    tool = FilesTool(files_root=str(sandbox))
    result = await tool.execute(action="delete", path="del.txt")
    assert result["status"] == "requires_confirmation"


@pytest.mark.asyncio
async def test_files_delete(sandbox: Path) -> None:
    tool = FilesTool(files_root=str(sandbox))
    (sandbox / "del.txt").write_text("bye")

    result = await tool.execute(action="delete", path="del.txt", confirmed=True)
    assert result["status"] == "deleted"


@pytest.mark.asyncio
async def test_files_path_traversal_rejected(sandbox: Path) -> None:
    tool = FilesTool(files_root=str(sandbox))
    result = await tool.execute(action="read", path="../etc/passwd")
    assert "error" in result
    assert "escape" in result["error"].lower()


@pytest.mark.asyncio
async def test_files_unknown_action(sandbox: Path) -> None:
    tool = FilesTool(files_root=str(sandbox))
    result = await tool.execute(action="unknown")
    assert "error" in result
