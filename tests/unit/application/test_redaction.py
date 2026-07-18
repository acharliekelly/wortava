import json
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
