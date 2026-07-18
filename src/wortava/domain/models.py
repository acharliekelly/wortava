from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

type EvidenceValue = str | int | float | bool | None


class Status(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    UNKNOWN = "UNKNOWN"


class Subsystem(StrEnum):
    SYSTEM = "system"
    OBS = "obs"
    MIXER = "mixer"
    AUDIO = "audio"


@dataclass(frozen=True, slots=True)
class Evidence:
    key: str
    value: EvidenceValue


@dataclass(frozen=True, slots=True)
class CheckResult:
    check_id: str
    subsystem: Subsystem
    status: Status
    summary: str
    evidence: tuple[Evidence, ...]
    remediation: str | None
    duration_ms: int
    checked_at: datetime
    error_category: str | None


@dataclass(frozen=True, slots=True)
class ValidationReport:
    schema_version: str
    run_id: str
    started_at: datetime
    results: tuple[CheckResult, ...]

    @property
    def exit_code(self) -> int:
        return 1 if any(item.status is Status.FAIL for item in self.results) else 0
