import json
import logging
import traceback
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

REDACTION = "**********"


def log_file_path(log_dir: Path, run_id: str) -> Path:
    return log_dir / f"wortava-{run_id}.jsonl"


class RedactingFilter(logging.Filter):
    """Replace configured exact secret values before a record reaches a handler."""

    def __init__(self, secret_values: Iterable[str]) -> None:
        super().__init__()
        self._secrets = tuple(
            sorted({value for value in secret_values if value}, key=len, reverse=True)
        )

    def _redact(self, value: str) -> str:
        for secret in self._secrets:
            value = value.replace(secret, REDACTION)
        return value

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._redact(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(
                self._redact(value) if isinstance(value, str) else value for value in record.args
            )
        elif isinstance(record.args, Mapping):
            record.args = {
                key: self._redact(value) if isinstance(value, str) else value
                for key, value in record.args.items()
            }
        if record.exc_info is not None:
            rendered = "".join(traceback.format_exception(*record.exc_info))
            record.exc_text = self._redact(rendered)
            record.exc_info = None
        elif record.exc_text is not None:
            record.exc_text = self._redact(record.exc_text)
        return True


class JsonLinesFormatter(logging.Formatter):
    def __init__(self, run_id: str) -> None:
        super().__init__()
        self._run_id = run_id

    def format(self, record: logging.LogRecord) -> str:
        document: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC)
            .isoformat()
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "run_id": self._run_id,
            "check_id": getattr(record, "check_id", None),
            "event": getattr(record, "event", None),
            "duration_ms": getattr(record, "duration_ms", None),
            "error_category": getattr(record, "error_category", None),
            "message": record.getMessage(),
        }
        exception_class = getattr(record, "exception_class", None)
        if exception_class is not None:
            document["exception_class"] = exception_class
        if record.exc_text:
            document["exception"] = record.exc_text
        return json.dumps(document, ensure_ascii=False)


def configure_logging(log_dir: Path, run_id: str, secrets: Iterable[str]) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"wortava.run.{run_id}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for existing in tuple(logger.handlers):
        existing.close()
        logger.removeHandler(existing)

    handler = RotatingFileHandler(
        log_file_path(log_dir, run_id),
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    handler.addFilter(RedactingFilter(secrets))
    handler.setFormatter(JsonLinesFormatter(run_id))
    logger.addHandler(handler)
    return logger
