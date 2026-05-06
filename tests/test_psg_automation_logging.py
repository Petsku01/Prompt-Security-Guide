"""Tests for psg.automation.logging_config — Task 6.2."""

from __future__ import annotations

import logging
from pathlib import Path

from psg.automation.logging_config import setup_logging


# ── Task 6.2: 3 tests ────────────────────────────────────────────────────


def test_setup_logging_returns_logger() -> None:
    """setup_logging() must return a logging.Logger instance with at least
    one handler (console) and level set to INFO."""
    # Use a unique name so the module-level default logger isn't affected.
    name = "test_returns_logger_unique"
    # Remove any leftover logger from a previous test run in this process.
    logging.getLogger(name).handlers.clear()

    result = setup_logging(name=name)

    assert isinstance(result, logging.Logger)
    assert result.level == logging.INFO
    # At minimum the console handler is always added.
    assert len(result.handlers) >= 1
    # Cleanup so subsequent calls with same name don't hit idempotent guard.
    result.handlers.clear()
    logging.getLogger(name).handlers.clear()


def test_setup_logging_with_file_handler(tmp_path: Path) -> None:
    """When log_dir is provided, a FileHandler must be added alongside the
    console handler, and the log file must be created on first log message."""
    name = "test_file_handler_unique"
    logging.getLogger(name).handlers.clear()

    log_dir = tmp_path / "logs"
    result = setup_logging(log_dir=log_dir, name=name)

    # Expect 2 handlers: console + file
    handler_types = [type(h).__name__ for h in result.handlers]
    assert "FileHandler" in handler_types, f"Got handlers: {handler_types}"

    # Verify log directory was created
    assert log_dir.is_dir(), f"{log_dir} was not created"

    # Write a message and confirm the log file receives it
    result.info("hello from test")
    # Flush file handlers so content is written
    for h in result.handlers:
        h.flush()

    log_file = log_dir / f"{name}.log"
    assert log_file.exists(), f"Log file {log_file} was not created"
    content = log_file.read_text()
    assert "hello from test" in content

    # Cleanup
    for h in list(result.handlers):
        h.close()
    result.handlers.clear()
    logging.getLogger(name).handlers.clear()


def test_setup_logging_idempotent() -> None:
    """Calling setup_logging() twice with the same name must return the same
    Logger and must NOT add duplicate handlers."""
    name = "test_idempotent_unique"
    logging.getLogger(name).handlers.clear()

    first = setup_logging(name=name)
    handler_count_after_first = len(first.handlers)
    assert handler_count_after_first >= 1

    second = setup_logging(name=name)

    # Same logger object (identity check)
    assert first is second
    # No new handlers added by the second call
    assert len(second.handlers) == handler_count_after_first

    # Cleanup
    for h in list(second.handlers):
        h.close()
    second.handlers.clear()
    logging.getLogger(name).handlers.clear()