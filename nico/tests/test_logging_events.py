import logging

from nico.utils.logging import get_logger, log_event


def test_logger_emits_event_context_payload(caplog) -> None:
    logger = get_logger("test.events")
    caplog.set_level(logging.INFO, logger="test.events")

    log_event(logger, "tool_executed", tool_name="weather", result="ok")

    assert "event=tool_executed" in caplog.text
    assert "tool_name=weather" in caplog.text
    assert "result=ok" in caplog.text
