import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from wortava.domain.models import CheckResult, Evidence, Status, Subsystem, ValidationReport

type Evaluation = tuple[Status, str, tuple[Evidence, ...]]


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    subsystem: Subsystem
    timeout_seconds: float
    operation: Callable[[], Awaitable[object]]
    evaluate: Callable[[object], Evaluation]


async def _run_one(check: Check) -> CheckResult:
    started = time.perf_counter()
    checked_at = datetime.now(UTC)
    try:
        value = await asyncio.wait_for(check.operation(), check.timeout_seconds)
        status, summary, evidence = check.evaluate(value)
        category = None
    except TimeoutError:
        status, summary, evidence, category = Status.UNKNOWN, "Check timed out", (), "timeout"
    except Exception:
        status = Status.UNKNOWN
        summary = "Check could not determine state"
        evidence = ()
        category = "unexpected"
    return CheckResult(
        check_id=check.name,
        subsystem=check.subsystem,
        status=status,
        summary=summary,
        evidence=evidence,
        remediation=None,
        duration_ms=round((time.perf_counter() - started) * 1000),
        checked_at=checked_at,
        error_category=category,
    )


async def run_validation(checks: tuple[Check, ...], run_id: str) -> ValidationReport:
    started_at = datetime.now(UTC)
    results = await asyncio.gather(*(_run_one(check) for check in checks))
    return ValidationReport("1.0", run_id, started_at, tuple(results))
