from datetime import UTC, datetime

from wortava.domain.models import CheckResult, Evidence, Status, Subsystem, ValidationReport


def result(status: Status) -> CheckResult:
    return CheckResult(
        check_id="obs.connection",
        subsystem=Subsystem.OBS,
        status=status,
        summary="OBS checked",
        evidence=(Evidence(key="host", value="127.0.0.1"),),
        remediation=None,
        duration_ms=12,
        checked_at=datetime(2026, 7, 15, tzinfo=UTC),
        error_category=None,
    )


def test_report_exit_code_is_one_when_any_check_fails() -> None:
    report = ValidationReport(
        schema_version="1.0",
        run_id="run-1",
        started_at=datetime(2026, 7, 15, tzinfo=UTC),
        results=(result(Status.PASS), result(Status.FAIL)),
    )
    assert report.exit_code == 1


def test_unknown_does_not_fail_report() -> None:
    report = ValidationReport(
        schema_version="1.0",
        run_id="run-2",
        started_at=datetime(2026, 7, 15, tzinfo=UTC),
        results=(result(Status.UNKNOWN),),
    )
    assert report.exit_code == 0
