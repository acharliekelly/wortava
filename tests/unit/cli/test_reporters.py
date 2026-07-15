import json
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console

from wortava.cli.reporters import render_terminal, report_to_dict
from wortava.domain.models import CheckResult, Evidence, Status, Subsystem, ValidationReport


def fixed_report() -> ValidationReport:
    return ValidationReport(
        schema_version="1.0",
        run_id="run-fixed",
        started_at=datetime(2026, 7, 15, 12, 0, tzinfo=UTC),
        results=(
            CheckResult(
                check_id="obs.connection",
                subsystem=Subsystem.OBS,
                status=Status.PASS,
                summary="OBS connection succeeded",
                evidence=(Evidence("connected", True),),
                remediation=None,
                duration_ms=4,
                checked_at=datetime(2026, 7, 15, 12, 0, 1, tzinfo=UTC),
                error_category=None,
            ),
        ),
    )


def test_report_to_dict_matches_versioned_golden_contract() -> None:
    golden = json.loads(
        Path("tests/fixtures/golden/all-pass-report.json").read_text(encoding="utf-8")
    )

    assert report_to_dict(fixed_report()) == golden


def test_terminal_report_groups_results_by_subsystem() -> None:
    console = Console(record=True, width=100)

    render_terminal(fixed_report(), console)

    output = console.export_text()
    assert "OBS" in output
    assert "obs.connection" in output
    assert "PASS" in output
