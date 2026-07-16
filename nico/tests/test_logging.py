import logging

from nico.utils.logging import get_logger, log_event


def test_logger_emits_structured_message(caplog) -> None:
    logger = get_logger("test")
    caplog.set_level(logging.INFO, logger="test")
    log_event(logger, "provider_selected", provider="openai")

    assert "provider_selected" in caplog.text
    assert "openai" in caplog.text
