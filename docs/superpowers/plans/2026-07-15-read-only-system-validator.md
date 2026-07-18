# Read-Only System Validator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI that safely validates the observable state of a Windows church A/V system and remains fully testable with simulations away from the equipment.

**Architecture:** A portable domain and application core owns read-only probe protocols. Windows, OBS WebSocket, X Air OSC, Windows Core Audio, and fixture-backed simulated adapters implement those protocols; a concurrent runner turns observations into complete reports rendered for terminals or versioned JSON.

**Tech Stack:** Python 3.12, uv, Typer, Rich, Pydantic 2/pydantic-settings, psutil, obsws-python, python-osc, Pycaw, pytest, pytest-cov, Ruff, mypy, PyInstaller, GitHub Actions.

## Global Constraints

- Target the church's Windows A/V computer while keeping the portable core runnable on Windows, Linux, and macOS.
- Milestone one is strictly read-only: do not expose or call OBS setters, Core Audio setters, mixer setters, or GUI automation.
- Missing optional configuration returns `UNKNOWN`; a configured expectation that is positively violated returns `FAIL`.
- Every external operation has a bounded timeout; one failed check never stops the remaining checks.
- Never emit credentials in terminal output, JSON, exception text, or logs.
- Use `PASS`, `FAIL`, `WARN`, and `UNKNOWN`; exit `0` for no failures, `1` for any failure, and `2` for invalid installation or configuration.
- Python version is exactly 3.12 for development and build jobs.
- The shipped church artifact is a standalone Windows executable.

---

## Planned File Map

```text
pyproject.toml                         package, dependencies, tools, CLI entry point
uv.lock                               reproducible dependency lock
.python-version                       Python 3.12 pin
.gitignore                            local environments, secrets, reports, companion files
src/wortava/domain/models.py           immutable observations, results, reports, status rules
src/wortava/config/models.py           validated TOML profile and redacted secrets
src/wortava/config/loader.py           default/profile/environment merge
src/wortava/ports/probes.py            read-only Protocol interfaces
src/wortava/adapters/simulated.py      fixture-backed portable probes
src/wortava/adapters/windows/process.py psutil process/software discovery
src/wortava/adapters/windows/audio.py  Pycaw endpoint inventory
src/wortava/adapters/obs/client.py      OBS WebSocket read-only queries
src/wortava/adapters/xair/client.py     X Air OSC /info query
src/wortava/application/checks.py      observation-to-result policies
src/wortava/application/runner.py      concurrent execution and timeout isolation
src/wortava/observability/logging.py   rotating run-correlated sanitized logs
src/wortava/cli/reporters.py            terminal and JSON presenters
src/wortava/cli/app.py                  Typer commands and composition root
src/wortava/__main__.py                 `python -m wortava` entry point
config/defaults.toml                    safe defaults and timeouts
config/site.example.toml                documented church profile template
tests/...                               unit, contract, integration, acceptance, fixtures
docs/architecture/result-schema.md      stable JSON/status contract
docs/field-guides/church-discovery.md   first on-site inventory procedure
.github/workflows/ci.yml                portable and Windows quality gates
wortava.spec                             PyInstaller build definition
```

### Task 1: Bootstrap the Reproducible Package and Quality Gates

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `.gitignore`
- Create: `src/wortava/__init__.py`
- Create: `tests/unit/test_package.py`
- Create: `uv.lock`

**Interfaces:**
- Produces: importable package `wortava`; console entry point `wortava = wortava.cli.app:main` (implemented in Task 6).

- [ ] **Step 1: Write the package smoke test**

```python
# tests/unit/test_package.py
import wortava


def test_package_exposes_version() -> None:
    assert wortava.__version__ == "0.1.0"
```

- [ ] **Step 2: Run the test and verify the package does not exist**

Run: `uv run pytest tests/unit/test_package.py -q`

Expected: FAIL because `pyproject.toml` and `wortava` do not exist.

- [ ] **Step 3: Add project metadata and the minimal package**

```toml
# pyproject.toml
[project]
name = "wortava"
version = "0.1.0"
requires-python = "==3.12.*"
dependencies = [
  "obsws-python>=1.8,<2",
  "psutil>=7,<8",
  "pydantic>=2.11,<3",
  "pydantic-settings>=2.10,<3",
  "python-osc>=1.9,<2",
  "rich>=14,<15",
  "typer>=0.16,<1",
]

[project.optional-dependencies]
windows = ["pycaw>=20240210"]
dev = [
  "mypy>=1.17,<2",
  "pyinstaller>=6.14,<7",
  "pytest>=8.4,<9",
  "pytest-cov>=6.2,<7",
  "ruff>=0.12,<1",
]

[project.scripts]
wortava = "wortava.cli.app:main"

[build-system]
requires = ["hatchling>=1.27,<2"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--strict-markers --strict-config"

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "RUF"]

[tool.mypy]
python_version = "3.12"
strict = true
packages = ["wortava"]
```

```text
# .python-version
3.12
```

```gitignore
# .gitignore
.venv/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
build/
dist/
*.spec.local
.superpowers/
config/site.toml
config/secrets.toml
reports/
logs/
```

```python
# src/wortava/__init__.py
__version__ = "0.1.0"
```

- [ ] **Step 4: Lock dependencies and run all bootstrap gates**

Run: `uv lock && uv sync --extra dev`

Expected: `uv.lock` is created and dependencies install successfully.

Run: `uv run pytest tests/unit/test_package.py -q && uv run ruff check . && uv run mypy src`

Expected: one passing test, Ruff success, and mypy success.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock .python-version .gitignore src/wortava/__init__.py tests/unit/test_package.py
git commit -m "build: bootstrap wortava Python package"
```

### Task 2: Define the Domain Result Contract

**Files:**
- Create: `src/wortava/domain/__init__.py`
- Create: `src/wortava/domain/models.py`
- Create: `tests/unit/domain/test_models.py`

**Interfaces:**
- Produces: `Status`, `Subsystem`, `Evidence`, `CheckResult`, `ValidationReport`, and `ValidationReport.exit_code`.

- [ ] **Step 1: Write failing status and report tests**

```python
# tests/unit/domain/test_models.py
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
```

- [ ] **Step 2: Verify the model import fails**

Run: `uv run pytest tests/unit/domain/test_models.py -q`

Expected: FAIL with `ModuleNotFoundError: wortava.domain`.

- [ ] **Step 3: Implement immutable domain models**

```python
# src/wortava/domain/models.py
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TypeAlias

EvidenceValue: TypeAlias = str | int | float | bool | None


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
```

Create empty `src/wortava/domain/__init__.py`.

- [ ] **Step 4: Run domain tests and quality gates**

Run: `uv run pytest tests/unit/domain/test_models.py -q && uv run ruff check src tests && uv run mypy src`

Expected: two passing tests and no quality errors.

- [ ] **Step 5: Commit**

```bash
git add src/wortava/domain tests/unit/domain
git commit -m "feat: define validation result contract"
```

### Task 3: Load Layered Configuration and Guarantee Redaction

**Files:**
- Create: `src/wortava/config/__init__.py`
- Create: `src/wortava/config/models.py`
- Create: `src/wortava/config/loader.py`
- Create: `config/defaults.toml`
- Create: `config/site.example.toml`
- Create: `tests/unit/config/test_loader.py`

**Interfaces:**
- Produces: `Settings`, `ObsSettings`, `MixerSettings`, `AudioSettings`, `ProcessExpectation`, `load_settings(defaults_path, profile_path) -> Settings`.

- [ ] **Step 1: Write failing merge, optional-hardware, and redaction tests**

```python
# tests/unit/config/test_loader.py
from pathlib import Path

import pytest

from wortava.config.loader import load_settings


def test_profile_overrides_defaults_and_environment_supplies_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    defaults = tmp_path / "defaults.toml"
    defaults.write_text('[obs]\nhost="127.0.0.1"\nport=4455\ntimeout_seconds=2.0\n')
    profile = tmp_path / "site.toml"
    profile.write_text('[obs]\nhost="10.0.0.5"\n')
    monkeypatch.setenv("WORTAVA_OBS_PASSWORD", "super-secret")

    settings = load_settings(defaults, profile)

    assert settings.obs.host == "10.0.0.5"
    assert settings.obs.port == 4455
    assert str(settings.obs.password) == "**********"
    assert "super-secret" not in repr(settings)


def test_mixer_may_be_unconfigured(tmp_path: Path) -> None:
    defaults = tmp_path / "defaults.toml"
    defaults.write_text('[obs]\nhost="127.0.0.1"\nport=4455\ntimeout_seconds=2.0\n')
    settings = load_settings(defaults, None)
    assert settings.mixer.host is None
```

- [ ] **Step 2: Run tests and verify missing config modules**

Run: `uv run pytest tests/unit/config/test_loader.py -q`

Expected: FAIL with `ModuleNotFoundError: wortava.config`.

- [ ] **Step 3: Implement settings and TOML merge**

```python
# src/wortava/config/models.py
from pydantic import BaseModel, Field, SecretStr


class ProcessExpectation(BaseModel):
    name: str
    executable: str | None = None
    required: bool = True


class ObsSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = Field(default=4455, ge=1, le=65535)
    password: SecretStr | None = None
    timeout_seconds: float = Field(default=2.0, gt=0, le=30)
    expected_scene: str | None = None


class MixerSettings(BaseModel):
    host: str | None = None
    port: int = Field(default=10024, ge=1, le=65535)
    timeout_seconds: float = Field(default=2.0, gt=0, le=30)


class AudioSettings(BaseModel):
    expected_render_endpoint: str | None = None
    expected_capture_endpoint: str | None = None


class Settings(BaseModel):
    adapter_mode: str = "real"
    processes: tuple[ProcessExpectation, ...] = ()
    obs: ObsSettings = ObsSettings()
    mixer: MixerSettings = MixerSettings()
    audio: AudioSettings = AudioSettings()
```

```python
# src/wortava/config/loader.py
import os
import tomllib
from pathlib import Path
from typing import Any

from wortava.config.models import Settings


def _read(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    with path.open("rb") as stream:
        return tomllib.load(stream)


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_settings(defaults_path: Path, profile_path: Path | None) -> Settings:
    values = _merge(_read(defaults_path), _read(profile_path))
    password = os.getenv("WORTAVA_OBS_PASSWORD")
    if password:
        values.setdefault("obs", {})["password"] = password
    return Settings.model_validate(values)
```

```toml
# config/defaults.toml
adapter_mode = "real"

[[processes]]
name = "obs64.exe"
required = true

[[processes]]
name = "Zoom.exe"
required = true

[[processes]]
name = "X-AIR-Edit.exe"
required = true

[obs]
host = "127.0.0.1"
port = 4455
timeout_seconds = 2.0

[mixer]
port = 10024
timeout_seconds = 2.0

[audio]
```

```toml
# config/site.example.toml
[obs]
expected_scene = "Worship Wide"

[mixer]
host = "192.168.1.1"

[audio]
expected_render_endpoint = "X-AIR"
expected_capture_endpoint = "X-AIR"
```

Create empty `src/wortava/config/__init__.py`.

- [ ] **Step 4: Verify configuration behavior**

Run: `uv run pytest tests/unit/config/test_loader.py -q && uv run ruff check src tests && uv run mypy src`

Expected: two passing tests and clean quality gates.

- [ ] **Step 5: Commit**

```bash
git add src/wortava/config config tests/unit/config
git commit -m "feat: load validated site configuration"
```

### Task 4: Establish Read-Only Ports and Simulated Adapters

**Files:**
- Create: `src/wortava/ports/__init__.py`
- Create: `src/wortava/ports/probes.py`
- Create: `src/wortava/adapters/__init__.py`
- Create: `src/wortava/adapters/simulated.py`
- Create: `tests/fixtures/scenarios/all-pass.json`
- Create: `tests/fixtures/scenarios/unknown-hardware.json`
- Create: `tests/contract/test_probe_contracts.py`

**Interfaces:**
- Produces: `ProcessObservation`, `ObsObservation`, `MixerObservation`, `AudioEndpoint`, and four async probe protocols.
- Produces: `SimulatedProbes.from_path(path) -> SimulatedProbes` implementing every protocol.

- [ ] **Step 1: Write a shared read-only contract test**

```python
# tests/contract/test_probe_contracts.py
from pathlib import Path

import pytest

from wortava.adapters.simulated import SimulatedProbes


@pytest.mark.asyncio
async def test_all_pass_fixture_implements_every_probe_contract() -> None:
    probes = SimulatedProbes.from_path(Path("tests/fixtures/scenarios/all-pass.json"))
    assert (await probes.inspect_processes())[0].running is True
    assert (await probes.inspect_obs()).virtual_camera_active is True
    assert (await probes.inspect_mixer()).reachable is True
    assert len(await probes.inspect_audio()) == 2
```

Add `pytest-asyncio>=1,<2` to the `dev` dependency group before locking.

- [ ] **Step 2: Run the contract test and verify failure**

Run: `uv lock && uv run pytest tests/contract/test_probe_contracts.py -q`

Expected: FAIL because ports and simulations do not exist.

- [ ] **Step 3: Define immutable observations and read-only protocols**

```python
# src/wortava/ports/probes.py
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ProcessObservation:
    name: str
    installed: bool | None
    running: bool
    pid: int | None
    executable: str | None
    version: str | None


@dataclass(frozen=True, slots=True)
class ObsObservation:
    connected: bool
    current_scene: str | None
    virtual_camera_active: bool | None


@dataclass(frozen=True, slots=True)
class MixerObservation:
    configured: bool
    reachable: bool | None
    model: str | None
    address: str | None


@dataclass(frozen=True, slots=True)
class AudioEndpoint:
    endpoint_id: str
    name: str
    direction: str
    active: bool
    default_multimedia: bool
    default_communications: bool


class ProcessProbe(Protocol):
    async def inspect_processes(self) -> tuple[ProcessObservation, ...]: ...


class ObsProbe(Protocol):
    async def inspect_obs(self) -> ObsObservation: ...


class MixerProbe(Protocol):
    async def inspect_mixer(self) -> MixerObservation: ...


class AudioProbe(Protocol):
    async def inspect_audio(self) -> tuple[AudioEndpoint, ...]: ...
```

- [ ] **Step 4: Implement fixture-backed simulated probes**

```python
# src/wortava/adapters/simulated.py
import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wortava.ports.probes import AudioEndpoint, MixerObservation, ObsObservation, ProcessObservation


@dataclass(slots=True)
class SimulatedProbes:
    data: dict[str, Any]

    @classmethod
    def from_path(cls, path: Path) -> "SimulatedProbes":
        return cls(json.loads(path.read_text(encoding="utf-8")))

    async def _delay(self, section: str) -> None:
        await asyncio.sleep(float(self.data.get(section, {}).get("delay_seconds", 0)))

    async def inspect_processes(self) -> tuple[ProcessObservation, ...]:
        await self._delay("processes")
        return tuple(ProcessObservation(**item) for item in self.data["processes"]["items"])

    async def inspect_obs(self) -> ObsObservation:
        await self._delay("obs")
        return ObsObservation(**self.data["obs"]["observation"])

    async def inspect_mixer(self) -> MixerObservation:
        await self._delay("mixer")
        return MixerObservation(**self.data["mixer"]["observation"])

    async def inspect_audio(self) -> tuple[AudioEndpoint, ...]:
        await self._delay("audio")
        return tuple(AudioEndpoint(**item) for item in self.data["audio"]["items"])
```

For `tests/fixtures/scenarios/all-pass.json`:

```json
{
  "processes": {"items": [{"name": "obs64.exe", "installed": true, "running": true, "pid": 100, "executable": "C:/Program Files/obs-studio/bin/64bit/obs64.exe", "version": "31.1"}]},
  "obs": {"observation": {"connected": true, "current_scene": "Worship Wide", "virtual_camera_active": true}},
  "mixer": {"observation": {"configured": true, "reachable": true, "model": "XR18", "address": "192.168.1.1:10024"}},
  "audio": {"items": [
    {"endpoint_id": "render-1", "name": "X-AIR", "direction": "render", "active": true, "default_multimedia": true, "default_communications": true},
    {"endpoint_id": "capture-1", "name": "X-AIR", "direction": "capture", "active": true, "default_multimedia": true, "default_communications": true}
  ]}
}
```

For `tests/fixtures/scenarios/unknown-hardware.json`:

```json
{
  "processes": {"items": []},
  "obs": {"observation": {"connected": false, "current_scene": null, "virtual_camera_active": null}},
  "mixer": {"observation": {"configured": false, "reachable": null, "model": null, "address": null}},
  "audio": {"items": []}
}
```

- [ ] **Step 5: Run the contract test and gates**

Run: `uv run pytest tests/contract/test_probe_contracts.py -q && uv run ruff check src tests && uv run mypy src`

Expected: one passing contract test and clean gates.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock src/wortava/ports src/wortava/adapters tests/contract tests/fixtures
git commit -m "feat: add read-only probe contracts and simulations"
```

### Task 5: Convert Observations into Complete Concurrent Validation Reports

**Files:**
- Create: `src/wortava/application/__init__.py`
- Create: `src/wortava/application/checks.py`
- Create: `src/wortava/application/runner.py`
- Create: `tests/unit/application/test_checks.py`
- Create: `tests/unit/application/test_runner.py`

**Interfaces:**
- Produces: `Check(name, subsystem, timeout_seconds, operation, evaluate)`.
- Produces: `build_checks(settings, probes) -> tuple[Check, ...]`.
- Produces: `run_validation(checks, run_id) -> ValidationReport`.

- [ ] **Step 1: Write failing policy and isolation tests**

```python
# tests/unit/application/test_runner.py
import asyncio

import pytest

from wortava.application.runner import Check, run_validation
from wortava.domain.models import Status, Subsystem


@pytest.mark.asyncio
async def test_timeout_becomes_unknown_and_other_checks_complete() -> None:
    async def slow() -> object:
        await asyncio.sleep(0.1)
        return object()

    async def fast() -> object:
        return object()

    checks = (
        Check("slow", Subsystem.OBS, 0.01, slow, lambda _: (Status.PASS, "ok", ())),
        Check("fast", Subsystem.SYSTEM, 1, fast, lambda _: (Status.PASS, "ok", ())),
    )
    report = await run_validation(checks, "run-1")
    assert [item.status for item in report.results] == [Status.UNKNOWN, Status.PASS]
    assert report.results[0].error_category == "timeout"
```

```python
# tests/unit/application/test_checks.py
from wortava.application.checks import evaluate_mixer
from wortava.domain.models import Status
from wortava.ports.probes import MixerObservation


def test_unconfigured_mixer_is_unknown() -> None:
    status, _, _ = evaluate_mixer(MixerObservation(False, None, None, None))
    assert status is Status.UNKNOWN


def test_unreachable_configured_mixer_fails() -> None:
    status, _, _ = evaluate_mixer(MixerObservation(True, False, None, "10.0.0.2"))
    assert status is Status.FAIL
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `uv run pytest tests/unit/application -q`

Expected: FAIL because the application modules do not exist.

- [ ] **Step 3: Implement check policy functions**

In `checks.py`, implement typed evaluators for processes, OBS connection, OBS expected scene, virtual-camera state, mixer, and audio endpoints. Each returns `tuple[Status, str, tuple[Evidence, ...]]`. Apply these exact policies:

```python
def evaluate_mixer(value: MixerObservation) -> Evaluation:
    evidence = (
        Evidence("configured", value.configured),
        Evidence("address", value.address),
        Evidence("model", value.model),
    )
    if not value.configured:
        return Status.UNKNOWN, "Mixer is not configured", evidence
    if value.reachable is False:
        return Status.FAIL, "Configured mixer did not respond", evidence
    if value.reachable is None:
        return Status.UNKNOWN, "Mixer state could not be determined", evidence
    return Status.PASS, "Mixer responded", evidence
```

For configured expected processes/endpoints/scenes, absence or mismatch is `FAIL`. For absent expectations, return `UNKNOWN`. OBS connection failure is `FAIL` because OBS host/port always have defaults. `build_checks()` binds configured expectations to evaluators and assigns unique IDs and per-adapter timeouts.

- [ ] **Step 4: Implement concurrent timeout-isolated execution**

```python
# core of src/wortava/application/runner.py
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
        status, summary, evidence, category = Status.UNKNOWN, "Check could not determine state", (), "unexpected"
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
```

Add imports and the `Evaluation` alias explicitly. Do not log raw exceptions yet; Task 10 adds sanitized logging.

- [ ] **Step 5: Verify policies, concurrency, and quality**

Run: `uv run pytest tests/unit/application -q && uv run ruff check src tests && uv run mypy src`

Expected: all application tests pass and quality gates are clean.

- [ ] **Step 6: Commit**

```bash
git add src/wortava/application tests/unit/application
git commit -m "feat: run complete timeout-isolated validations"
```

### Task 6: Deliver Terminal and Versioned JSON CLI Flows

**Files:**
- Create: `src/wortava/cli/__init__.py`
- Create: `src/wortava/cli/reporters.py`
- Create: `src/wortava/cli/app.py`
- Create: `src/wortava/__main__.py`
- Create: `tests/unit/cli/test_reporters.py`
- Create: `tests/acceptance/test_cli.py`
- Create: `tests/fixtures/golden/all-pass-report.json`

**Interfaces:**
- Produces: `report_to_dict(report) -> dict[str, object]`, `render_terminal(report, console)`, Typer `app`, and `main()`.
- Consumes: configuration loader, simulated probes, check builder, runner.

- [ ] **Step 1: Write failing JSON and subprocess acceptance tests**

```python
# tests/acceptance/test_cli.py
from typer.testing import CliRunner

from wortava.cli.app import app

runner = CliRunner()


def test_simulate_all_pass_emits_json_and_zero_exit() -> None:
    result = runner.invoke(app, ["simulate", "all-pass", "--format", "json"])
    assert result.exit_code == 0
    assert '"schema_version": "1.0"' in result.stdout
    assert '"status": "PASS"' in result.stdout


def test_invalid_profile_exits_two(tmp_path: object) -> None:
    result = runner.invoke(app, ["config", "validate", "--profile", "missing.toml"])
    assert result.exit_code == 2
```

- [ ] **Step 2: Run acceptance tests and verify missing CLI**

Run: `uv run pytest tests/acceptance/test_cli.py -q`

Expected: FAIL because `wortava.cli` does not exist.

- [ ] **Step 3: Implement reporters with a stable JSON shape**

`report_to_dict()` must emit this exact top-level contract:

```json
{
  "schema_version": "1.0",
  "run_id": "string",
  "started_at": "ISO-8601 UTC",
  "exit_code": 0,
  "summary": {"PASS": 0, "FAIL": 0, "WARN": 0, "UNKNOWN": 0},
  "results": []
}
```

Each result includes `check_id`, `subsystem`, `status`, `summary`, `evidence` as an object, `remediation`, `duration_ms`, `checked_at`, and `error_category`. Use `json.dumps(..., indent=2)` and Rich tables grouped by subsystem. Add a golden comparison unit test with timestamps and run IDs fixed by constructing a report directly.

- [ ] **Step 4: Implement the CLI composition root**

Create Typer commands matching the spec. `simulate` resolves only names under `tests/fixtures/scenarios` during development; also copy production simulation fixtures to `src/wortava/scenarios/` so packaged builds work. `validate` loads `config/defaults.toml` plus the given profile, selects real adapters, builds checks, runs with `asyncio.run`, renders, and exits with `report.exit_code`. Catch `OSError`, TOML errors, and Pydantic validation errors at the command boundary, print concise configuration errors, and exit `2`.

```python
# src/wortava/__main__.py
from wortava.cli.app import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Verify all public commands**

Run: `uv run wortava simulate all-pass --format terminal`

Expected: grouped PASS results and exit `0`.

Run: `uv run wortava simulate unknown-hardware --format json`

Expected: valid JSON containing `UNKNOWN` and exit `0`.

Run: `uv run wortava list-checks`

Expected: stable check IDs with subsystem names.

Run: `uv run pytest tests/unit/cli tests/acceptance -q && uv run ruff check src tests && uv run mypy src`

Expected: all tests and gates pass.

- [ ] **Step 6: Commit**

```bash
git add src/wortava/cli src/wortava/__main__.py src/wortava/scenarios tests/unit/cli tests/acceptance tests/fixtures/golden
git commit -m "feat: expose validator reports through CLI"
```

### Task 7: Add Windows Process and OBS Read-Only Adapters

**Files:**
- Create: `src/wortava/adapters/windows/__init__.py`
- Create: `src/wortava/adapters/windows/process.py`
- Create: `src/wortava/adapters/obs/__init__.py`
- Create: `src/wortava/adapters/obs/client.py`
- Create: `tests/unit/adapters/test_windows_process.py`
- Create: `tests/unit/adapters/test_obs_client.py`

**Interfaces:**
- Produces: `WindowsProcessProbe(expectations)` implementing `ProcessProbe`.
- Produces: `ObsWebSocketProbe(settings, client_factory)` implementing `ObsProbe`.

- [ ] **Step 1: Write adapter tests around injected vendor boundaries**

Test the process adapter with an injected `process_iter` returning fake objects and raising `psutil.AccessDenied` for one process. Assert matching is case-insensitive, inaccessible unrelated processes do not abort discovery, and configured executable existence distinguishes `installed=True`, `False`, and `None`.

Test OBS with an injected client factory whose fake client returns:

```python
SimpleNamespace(current_program_scene_name="Worship Wide")
SimpleNamespace(output_active=True)
```

Assert `ObsObservation(True, "Worship Wide", True)` and that only `get_current_program_scene()` and `get_virtual_cam_status()` are invoked. A connection exception must be translated to a typed adapter exception without including the password.

- [ ] **Step 2: Run adapter tests and verify failure**

Run: `uv run pytest tests/unit/adapters/test_windows_process.py tests/unit/adapters/test_obs_client.py -q`

Expected: FAIL because both adapters are missing.

- [ ] **Step 3: Implement process discovery**

Use `psutil.process_iter(["pid", "name", "exe"])`, normalize names with `casefold()`, and run the synchronous vendor call with `asyncio.to_thread`. Treat `NoSuchProcess`, `AccessDenied`, and `ZombieProcess` as skipped entries. Use `Path(expectation.executable).is_file()` only when an executable is configured. Return one observation per expectation in profile order.

- [ ] **Step 4: Implement OBS WebSocket queries**

Use `obsws_python.ReqClient(host, port, password.get_secret_value(), timeout)` inside `asyncio.to_thread`. Query exactly `get_current_program_scene()` and `get_virtual_cam_status()`, close/disconnect in `finally` if supported by the client, and map vendor response fields into `ObsObservation`. Never retain the raw client or password in the observation or exception.

- [ ] **Step 5: Verify adapters and the real composition path**

Run: `uv run pytest tests/unit/adapters/test_windows_process.py tests/unit/adapters/test_obs_client.py -q && uv run ruff check src tests && uv run mypy src`

Expected: adapter tests pass and gates are clean.

- [ ] **Step 6: Commit**

```bash
git add src/wortava/adapters/windows src/wortava/adapters/obs tests/unit/adapters
git commit -m "feat: inspect Windows processes and OBS state"
```

### Task 8: Add X Air OSC Discovery with a Local Fake Device

**Files:**
- Create: `src/wortava/adapters/xair/__init__.py`
- Create: `src/wortava/adapters/xair/client.py`
- Create: `tests/integration/adapters/test_xair_client.py`

**Interfaces:**
- Produces: `XAirOscProbe(settings, socket_factory)` implementing `MixerProbe`.
- Protocol behavior: send OSC `/info` to configured UDP port (default `10024`) and parse the documented `/info` response without changing mixer state.

- [ ] **Step 1: Write failing localhost UDP integration tests**

Use a short-lived local UDP test server that decodes `/info` with `pythonosc.osc_packet.OscPacket`, replies with an OSC `/info` message built by `OscMessageBuilder`, and returns fixture arguments containing model `XR18`. Assert reachable/model/address mapping. Add separate timeout and malformed-packet tests; timeout returns a typed `MixerUnavailable` error and malformed data returns `MixerProtocolError`.

- [ ] **Step 2: Run the integration tests and verify failure**

Run: `uv run pytest tests/integration/adapters/test_xair_client.py -q`

Expected: FAIL because the X Air adapter does not exist.

- [ ] **Step 3: Implement a bounded read-only OSC exchange**

If host is absent, return `MixerObservation(False, None, None, None)` without opening a socket. Otherwise build `/info`, use an injected UDP socket with `settimeout(settings.timeout_seconds)`, `sendto`, and `recvfrom`, parse the first `/info` response, and close in `finally`. Run blocking socket work in `asyncio.to_thread`. Do not implement `/xremote` or any channel/set address in this milestone.

- [ ] **Step 4: Verify live-protocol simulations and gates**

Run: `uv run pytest tests/integration/adapters/test_xair_client.py -q && uv run ruff check src tests && uv run mypy src`

Expected: response, timeout, and malformed-packet cases pass.

- [ ] **Step 5: Commit**

```bash
git add src/wortava/adapters/xair tests/integration/adapters/test_xair_client.py
git commit -m "feat: discover X Air mixer over read-only OSC"
```

### Task 9: Add Windows Core Audio Endpoint Inventory

**Files:**
- Create: `src/wortava/adapters/windows/audio.py`
- Create: `tests/unit/adapters/test_windows_audio.py`
- Modify: `src/wortava/cli/app.py`

**Interfaces:**
- Produces: `WindowsAudioProbe(audio_utilities)` implementing `AudioProbe`.
- Consumes: Pycaw only behind an injected boundary and only when running on Windows.

- [ ] **Step 1: Write failing mapping and platform-guard tests**

Inject fake Pycaw devices with IDs, friendly names, `eRender`/`eCapture` flow, active state, and fake default multimedia/communications IDs. Assert mapping into portable `AudioEndpoint` values. Patch `sys.platform` to a non-Windows value and assert the adapter raises `UnsupportedPlatform` without importing Pycaw.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest tests/unit/adapters/test_windows_audio.py -q`

Expected: FAIL because `audio.py` is missing.

- [ ] **Step 3: Implement read-only device inventory**

Import Pycaw lazily inside the default factory only after checking `sys.platform == "win32"`. Use `AudioUtilities.GetAllDevices()` and read device ID, friendly name, state, and data flow. Resolve default render/capture devices for multimedia and communications roles through Core Audio query APIs, never `SetDefaultDevice`. Run COM setup, reads, and cleanup in the same `asyncio.to_thread` worker.

- [ ] **Step 4: Wire Windows audio into real validation**

Update the composition root so `validate` constructs `WindowsAudioProbe` on Windows. On another OS, the check must return `UNKNOWN` with category `unsupported_platform`, while simulated flows stay cross-platform.

- [ ] **Step 5: Verify mapping and portable behavior**

Run: `uv run pytest tests/unit/adapters/test_windows_audio.py tests/acceptance/test_cli.py -q && uv run ruff check src tests && uv run mypy src`

Expected: tests pass on the development OS without requiring Pycaw to import.

- [ ] **Step 6: Commit**

```bash
git add src/wortava/adapters/windows/audio.py src/wortava/cli/app.py tests/unit/adapters/test_windows_audio.py
git commit -m "feat: inventory Windows audio endpoints"
```

### Task 10: Add Sanitized Run-Correlated Logging

**Files:**
- Create: `src/wortava/observability/__init__.py`
- Create: `src/wortava/observability/logging.py`
- Modify: `src/wortava/application/runner.py`
- Modify: `src/wortava/cli/app.py`
- Create: `tests/unit/observability/test_logging.py`
- Create: `tests/unit/application/test_redaction.py`

**Interfaces:**
- Produces: `configure_logging(log_dir, run_id, secrets) -> logging.Logger`.
- Produces: `RedactingFilter(secret_values)` replacing exact secret occurrences with `**********`.
- Changes: `run_validation(..., logger)` logs start/success/category/duration without changing results.

- [ ] **Step 1: Write failing end-to-end redaction tests**

Create a logger with secret `super-secret`, log that exact value directly and through a caught exception, then assert it is absent from the log file and replacement text is present. Invoke an OBS failure whose exception includes the password and assert the terminal, JSON, and captured log each exclude it.

- [ ] **Step 2: Run redaction tests and verify failure**

Run: `uv run pytest tests/unit/observability tests/unit/application/test_redaction.py -q`

Expected: FAIL because observability is missing.

- [ ] **Step 3: Implement rotation and exact-value redaction**

Use `logging.handlers.RotatingFileHandler(maxBytes=1_000_000, backupCount=5, encoding="utf-8")`. The filter rewrites both `record.msg` and string arguments, longest secrets first, and clears `exc_info` after rendering a sanitized exception string. Emit JSON Lines with UTC timestamp, level, run ID, check ID, event, duration, and error category.

- [ ] **Step 4: Instrument runner and CLI**

Log `check_started` and `check_finished`; for unexpected exceptions log exception class and sanitized text but never traceback locals. Configure a run logger before building checks, pass the same UUID run ID to logger and report, and print the log path once at report completion.

- [ ] **Step 5: Verify redaction and regression suite**

Run: `uv run pytest tests/unit/observability tests/unit/application/test_redaction.py -q`

Expected: all secret-leak tests pass.

Run: `uv run pytest -q && uv run ruff check . && uv run mypy src`

Expected: complete suite and gates pass.

- [ ] **Step 6: Commit**

```bash
git add src/wortava/observability src/wortava/application/runner.py src/wortava/cli/app.py tests/unit/observability tests/unit/application/test_redaction.py
git commit -m "feat: add sanitized validation diagnostics"
```

### Task 11: Document the Contract and On-Site Discovery Procedure

**Files:**
- Create: `README.md`
- Create: `docs/architecture/result-schema.md`
- Create: `docs/field-guides/church-discovery.md`
- Create: `tests/acceptance/test_documented_commands.py`

**Interfaces:**
- Documents: installation, simulation, real validation, statuses, exit codes, JSON schema, log lookup, and exact field data to capture.

- [ ] **Step 1: Add a failing test for documented commands**

Parse fenced `console` commands marked `<!-- smoke-test -->` in `README.md`, run them from the repository root, and assert exit `0`. The first required command is `uv run wortava simulate all-pass --format json`.

- [ ] **Step 2: Run the test and verify README is missing**

Run: `uv run pytest tests/acceptance/test_documented_commands.py -q`

Expected: FAIL because `README.md` does not exist.

- [ ] **Step 3: Write operator and developer documentation**

README sections: purpose, safety boundary, prerequisites, quick start, simulator scenarios, profile creation, commands, status/exit-code table, logs, development gates, Windows build, and roadmap.

`result-schema.md` must show one complete schema `1.0` JSON example and state additive fields are allowed within `1.x`, while removals/renames/status changes require `2.0`.

`church-discovery.md` must collect:

- Windows edition/build and account permission level.
- OBS version, WebSocket enabled/host/port/authentication, current scene collection, expected program scene, and virtual-camera behavior.
- Zoom version, install path, process name, account type, and any supported control API evidence.
- X Air model, firmware, X Air Edit version/path, mixer IP/port/network topology, `/info` response, and sanitized OSC capture.
- Every active render/capture endpoint ID/name, default multimedia/communications roles, application routing observations, and the physical test procedure.
- Required physical connections and expected pass/fail state before Sunday service.
- A sanitization checklist that excludes passwords, meeting credentials, personal data, and Wi-Fi secrets from fixtures.

- [ ] **Step 4: Verify every documented command**

Run: `uv run pytest tests/acceptance/test_documented_commands.py -q`

Expected: every smoke-marked command exits `0`.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/architecture docs/field-guides tests/acceptance/test_documented_commands.py
git commit -m "docs: add validator and field discovery guides"
```

### Task 12: Build and Verify the Standalone Windows Artifact

**Files:**
- Create: `wortava.spec`
- Create: `.github/workflows/ci.yml`
- Create: `tests/acceptance/test_packaged_cli.py`
- Modify: `README.md`

**Interfaces:**
- Produces: `dist/wortava/wortava.exe` containing production scenarios and defaults.
- CI artifact: `wortava-windows-x64` with SHA-256 checksum.

- [ ] **Step 1: Write a packaged executable smoke test**

```python
# tests/acceptance/test_packaged_cli.py
import json
import subprocess
from pathlib import Path


def test_packaged_cli_runs_without_python() -> None:
    executable = Path("dist/wortava/wortava.exe")
    completed = subprocess.run(
        [executable, "simulate", "all-pass", "--format", "json"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert json.loads(completed.stdout)["schema_version"] == "1.0"
```

Mark this test `windows_package` and register the marker so normal local runs skip it unless `--run-windows-package` is supplied.

- [ ] **Step 2: Add a PyInstaller spec with explicit data and hidden imports**

The spec must include `config/defaults.toml` and `src/wortava/scenarios/*.json`, Typer/Rich metadata, `obsws_python`, `pythonosc`, and Windows-only Pycaw/comtypes modules. Build an onedir artifact named `wortava`; prefer onedir over onefile so startup and antivirus behavior remain predictable.

- [ ] **Step 3: Add portable and Windows CI jobs**

Portable job matrix: `ubuntu-latest`, `macos-latest`, and `windows-latest`; install uv, pin Python 3.12, sync dev dependencies (`--extra windows` on Windows), then run Ruff, mypy, and pytest with coverage.

Windows package job: depend on tests, run `uv run pyinstaller wortava.spec --clean`, run the marked packaged test, generate `SHA256SUMS.txt` with PowerShell `Get-FileHash`, and upload the directory plus checksum as `wortava-windows-x64`.

- [ ] **Step 4: Build and smoke-test on Windows**

Run on Windows: `uv sync --extra dev --extra windows && uv run pyinstaller wortava.spec --clean`

Expected: `dist/wortava/wortava.exe` exists.

Run on Windows: `uv run pytest tests/acceptance/test_packaged_cli.py --run-windows-package -q`

Expected: one passing packaged-artifact test.

- [ ] **Step 5: Run final milestone verification**

Run: `uv run ruff check .`

Expected: success.

Run: `uv run mypy src`

Expected: success with no issues.

Run: `uv run pytest --cov=wortava --cov-branch --cov-report=term-missing -q`

Expected: all tests pass; application/domain branch coverage is at least 90%, with Windows vendor wrappers excluded only where Windows CI supplies direct coverage.

Run: `uv run wortava simulate all-pass --format terminal`

Expected: every configured check is `PASS`, exit `0`.

Run: `uv run wortava simulate unknown-hardware --format json`

Expected: complete schema `1.0` JSON, relevant checks `UNKNOWN`, exit `0`.

- [ ] **Step 6: Commit**

```bash
git add wortava.spec .github/workflows/ci.yml tests/acceptance/test_packaged_cli.py README.md pyproject.toml
git commit -m "build: package and verify Windows validator"
```

## Implementation References

- Approved design: `docs/superpowers/specs/2026-07-15-read-only-system-validator-design.md`
- OBS WebSocket official protocol: <https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md>
- OBS WebSocket inclusion and default port: <https://github.com/obsproject/obs-websocket>
- psutil process API: <https://psutil.readthedocs.io/en/latest/#processes>
- python-osc client/server API: <https://python-osc.readthedocs.io/en/stable/>
- Pycaw Windows Core Audio API: <https://andremiras.github.io/pycaw/>
- uv projects: <https://docs.astral.sh/uv/guides/projects/>
- PyInstaller usage: <https://pyinstaller.org/en/stable/>
