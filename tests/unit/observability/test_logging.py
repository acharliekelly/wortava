import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from wortava.observability.logging import RedactingFilter, configure_logging


def _close_logger(logger: logging.Logger) -> None:
    for handler in tuple(logger.handlers):
        handler.close()
        logger.removeHandler(handler)


def test_configure_logging_writes_rotating_utf8_json_lines(tmp_path: Path) -> None:
    logger = configure_logging(tmp_path, "run-fixed", ())
    handler = logger.handlers[0]
    assert isinstance(handler, RotatingFileHandler)
    assert handler.maxBytes == 1_000_000
    assert handler.backupCount == 5
    assert handler.encoding.lower().replace("-", "") == "utf8"
    try:
        logger.info("check lifecycle", extra={"event": "check_started", "check_id": "obs"})
    finally:
        _close_logger(logger)

    document = json.loads((tmp_path / "wortava-run-fixed.jsonl").read_text(encoding="utf-8"))
    assert document["run_id"] == "run-fixed"
    assert document["event"] == "check_started"
    assert document["check_id"] == "obs"
    assert document["level"] == "INFO"
    assert document["timestamp"].endswith("Z")


def test_redacting_filter_sanitizes_direct_args_and_exception(tmp_path: Path) -> None:
    secret = "super-secret"
    logger = configure_logging(tmp_path, "redaction", (secret, "super"))
    try:
        logger.info(f"direct {secret}")
        logger.info("argument %s", secret)
        try:
            raise RuntimeError(f"connection failed with {secret}")
        except RuntimeError:
            logger.exception("caught %s", secret)
    finally:
        _close_logger(logger)

    contents = (tmp_path / "wortava-redaction.jsonl").read_text(encoding="utf-8")
    assert secret not in contents
    assert "**********" in contents
    assert contents.count("**********-secret") == 0


def test_redacting_filter_clears_raw_exception_information() -> None:
    secret = "super-secret"
    redactor = RedactingFilter((secret,))
    try:
        raise RuntimeError(secret)
    except RuntimeError:
        record = logging.getLogger("test").makeRecord(
            "test", logging.ERROR, __file__, 1, "failed", (), __import__("sys").exc_info()
        )

    assert redactor.filter(record)
    assert record.exc_info is None
    assert record.exc_text is not None
    assert secret not in record.exc_text


def test_reconfiguring_run_logger_replaces_and_closes_handler(tmp_path: Path) -> None:
    first = configure_logging(tmp_path, "repeated", ())
    original_handler = first.handlers[0]

    second = configure_logging(tmp_path, "repeated", ())
    try:
        assert first is second
        assert len(second.handlers) == 1
        assert original_handler.stream is None
    finally:
        _close_logger(second)

    log_path = tmp_path / "wortava-repeated.jsonl"
    log_path.rename(tmp_path / "closed.jsonl")


def test_filter_preserves_numeric_formatting_and_redacts_mapping_values(tmp_path: Path) -> None:
    logger = configure_logging(tmp_path, "formatting", ("super-secret",))
    try:
        logger.info("count=%d ratio=%.2f", 7, 1.25)
        logger.info("token=%(token)s", {"token": "super-secret"})
    finally:
        _close_logger(logger)

    events = [
        json.loads(line)
        for line in (tmp_path / "wortava-formatting.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    assert events[0]["message"] == "count=7 ratio=1.25"
    assert events[1]["message"] == "token=**********"


def test_filter_resolves_non_string_arguments_before_formatter(tmp_path: Path) -> None:
    class SecretString:
        def __str__(self) -> str:
            return "super-secret"

    logger = configure_logging(tmp_path, "object", ("super-secret",))
    try:
        logger.info("value=%s", SecretString())
    finally:
        _close_logger(logger)

    event = json.loads((tmp_path / "wortava-object.jsonl").read_text(encoding="utf-8"))
    assert event["message"] == "value=**********"


def test_malformed_and_hostile_messages_emit_safe_json_without_stderr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    class Hostile:
        def __str__(self) -> str:
            raise RuntimeError("str failed")

        def __repr__(self) -> str:
            raise RuntimeError("repr failed")

    logger = configure_logging(tmp_path, "malformed", ("super-secret",))
    try:
        logger.info("hostile=%s", Hostile())
        logger.info("hostile=%r", Hostile())
        logger.info("missing=%s %s", "one")
        logger.info("extra=%s", "one", "two")
        logger.info("missing=%(token)s", {"different": "super-secret"})
    finally:
        _close_logger(logger)

    captured = capsys.readouterr()
    assert captured.err == ""
    lines = (tmp_path / "wortava-malformed.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5
    assert all(json.loads(line)["message"] == "Unrenderable log message" for line in lines)
    assert "super-secret" not in "\n".join(lines)


def test_exception_chain_is_redacted_and_never_retains_raw_exception(tmp_path: Path) -> None:
    logger = configure_logging(tmp_path, "chain", ("super-secret",))
    try:
        try:
            raise ValueError("inner super-secret")
        except ValueError as error:
            try:
                raise RuntimeError("outer super-secret") from error
            except RuntimeError:
                logger.exception("chained failure")
    finally:
        _close_logger(logger)

    contents = (tmp_path / "wortava-chain.jsonl").read_text(encoding="utf-8")
    assert "super-secret" not in contents
    event = json.loads(contents)
    assert event["exception"].count("**********") >= 2
