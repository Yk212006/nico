import pytest

from nico.tools.gpio.gpio import GpioTool


@pytest.mark.asyncio
async def test_gpio_read_simulated() -> None:
    tool = GpioTool()
    result = await tool.execute(pin=17, action="read")
    assert result["status"] == "simulated"
    assert result["pin"] == 17


@pytest.mark.asyncio
async def test_gpio_write_requires_confirmation() -> None:
    tool = GpioTool()
    result = await tool.execute(pin=17, action="set_high")
    assert result["status"] == "requires_confirmation"


@pytest.mark.asyncio
async def test_gpio_write_with_confirmation() -> None:
    tool = GpioTool()
    result = await tool.execute(pin=17, action="set_high", confirmed=True)
    # On non-Pi, this will be simulated
    assert result["status"] in ("simulated", "executed")


@pytest.mark.asyncio
async def test_gpio_missing_pin() -> None:
    tool = GpioTool()
    result = await tool.execute(action="read")
    assert "error" in result
