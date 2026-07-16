import pytest

from nico.tools.system.system_info import SystemInfoTool


@pytest.mark.asyncio
async def test_system_info_returns_basic_info() -> None:
    tool = SystemInfoTool()
    result = await tool.execute()
    assert "os" in result
    assert "machine" in result
    assert "python_version" in result
    assert "hostname" in result


@pytest.mark.asyncio
async def test_system_info_includes_hardware_by_default() -> None:
    tool = SystemInfoTool()
    result = await tool.execute()
    assert "cpu_count" in result


@pytest.mark.asyncio
async def test_system_info_honours_include_hardware_flag() -> None:
    tool = SystemInfoTool()
    result = await tool.execute(include_hardware=False)
    assert "cpu_count" not in result
