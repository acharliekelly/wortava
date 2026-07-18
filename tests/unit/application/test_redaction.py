import json
import logging
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from wortava.application.runner import Check, Evaluation, run_validation
from wortava.cli.reporters import render_terminal, report_to_dict
from wortava.domain.models import Subsystem
from wortava.observability.logging import configure_logging


@pytest.mark.asyncio
async def test_obs_failure_password_is_absent_from_reports_and_log(tmp_path: Path) -> None:
    password = "super-secret"

    async def broken_obs(_: object) -> Evaluation:
        raise RuntimeError(f"OBS rejected password {password}")

    logger = configure_logging(tmp_path, "obs-redaction", (password,))
    try:
        report = await run_validation(
            (Check("obs.connection", Subsystem.OBS, 1, broken_obs),),
            "obs-redaction",
            logger,
        )
    finally:
        for handler in tuple(logger.handlers):
            handler.close()
            logger.removeHandler(handler)

    console = Console(record=True, color_system=None)
    render_terminal(report, console)
    terminal = console.export_text()
    rendered_json = json.dumps(report_to_dict(report))
    captured_log = (tmp_path / "wortava-obs-redaction.jsonl").read_text(encoding="utf-8")

    assert password not in terminal
    assert password not in rendered_json
    assert password not in captured_log
    assert "**********" in captured_log
    events = [json.loads(line) for line in captured_log.splitlines()]
    assert [event["event"] for event in events] == [
        "check_started",
        "check_exception",
        "check_finished",
    ]
    assert events[-1]["error_category"] == "unexpected"
    assert events[1]["exception_class"] == "RuntimeError"


@pytest.mark.asyncio
async def test_missing_logger_never_propagates_unexpected_secret_to_root() -> None:
    password = "super-secret"

    async def broken(_: object) -> Evaluation:
        raise RuntimeError(password)

    stream = StringIO()
    root_handler = logging.StreamHandler(stream)
    root = logging.getLogger()
    root.addHandler(root_handler)
    try:
        report = await run_validation(
            (Check("obs.connection", Subsystem.OBS, 1, broken),),
            "no-logger",
            None,
        )
    finally:
        root.removeHandler(root_handler)
        root_handler.close()

    assert report.results[0].error_category == "unexpected"
    assert stream.getvalue() == ""


@pytest.mark.asyncio
async def test_hostile_exception_cannot_interrupt_report_or_logging(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    class HostileError(RuntimeError):
        def __str__(self) -> str:
            raise RuntimeError("str failed")

        def __repr__(self) -> str:
            raise RuntimeError("repr failed")

    async def broken(_: object) -> Evaluation:
        raise HostileError("super-secret")

    logger = configure_logging(tmp_path, "hostile-error", ("super-secret",))
    try:
        report = await run_validation(
            (Check("obs.connection", Subsystem.OBS, 1, broken),),
            "hostile-error",
            logger,
        )
    finally:
        for handler in tuple(logger.handlers):
            handler.close()
            logger.removeHandler(handler)

    assert report.results[0].error_category == "unexpected"
    assert report.results[0].status.value == "UNKNOWN"
    assert capsys.readouterr().err == ""
    contents = (tmp_path / "wortava-hostile-error.jsonl").read_text(encoding="utf-8")
    assert "super-secret" not in contents
    events = [json.loads(line) for line in contents.splitlines()]
    assert [event["event"] for event in events] == [
        "check_started",
        "check_exception",
        "check_finished",
    ]
    assert events[1]["message"] == "Unrenderable log message"


@pytest.mark.asyncio
async def test_hostile_exception_completes_without_configured_logger() -> None:
    class HostileError(RuntimeError):
        def __str__(self) -> str:
            raise RuntimeError("str failed")

        def __repr__(self) -> str:
            raise RuntimeError("repr failed")

    async def broken(_: object) -> Evaluation:
        raise HostileError("super-secret")

    report = await run_validation(
        (Check("obs.connection", Subsystem.OBS, 1, broken),),
        "hostile-no-logger",
        None,
    )

    assert report.results[0].error_category == "unexpected"
    assert report.results[0].status.value == "UNKNOWN"
