from collections import Counter
from typing import cast

from rich.console import Console
from rich.table import Table

from wortava.domain.models import Status, Subsystem, ValidationReport


def report_to_dict(report: ValidationReport) -> dict[str, object]:
    summary = Counter(result.status.value for result in report.results)
    return {
        "schema_version": report.schema_version,
        "run_id": report.run_id,
        "started_at": report.started_at.isoformat(),
        "exit_code": report.exit_code,
        "summary": {status.value: summary[status.value] for status in Status},
        "results": [
            {
                "check_id": result.check_id,
                "subsystem": result.subsystem.value,
                "status": result.status.value,
                "summary": result.summary,
                "evidence": {item.key: item.value for item in result.evidence},
                "remediation": result.remediation,
                "duration_ms": result.duration_ms,
                "checked_at": result.checked_at.isoformat(),
                "error_category": result.error_category,
            }
            for result in report.results
        ],
    }


def render_terminal(report: ValidationReport, console: Console) -> None:
    for subsystem in Subsystem:
        results = tuple(item for item in report.results if item.subsystem is subsystem)
        if not results:
            continue
        table = Table(title=subsystem.value.upper())
        table.add_column("Status")
        table.add_column("Check")
        table.add_column("Summary")
        table.add_column("Duration", justify="right")
        for result in results:
            table.add_row(
                result.status.value,
                result.check_id,
                result.summary,
                f"{result.duration_ms} ms",
            )
        console.print(table)

    values = cast(dict[str, int], report_to_dict(report)["summary"])
    console.print(
        "Summary: " + ", ".join(f"{status.value}={values[status.value]}" for status in Status)
    )
