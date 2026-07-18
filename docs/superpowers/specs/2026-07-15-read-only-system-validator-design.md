# Read-Only System Validator Design

## Purpose

Wortava's first milestone is a read-only command-line validator for the church's Windows A/V computer. It replaces assumptions with observable evidence while creating stable architectural seams for later automation.

The validator must be fully developable away from the church. Real Windows, OBS, mixer, and audio integrations therefore share contracts with deterministic simulated adapters. Unknown equipment or missing configuration affects only the relevant checks and never prevents the rest of a validation run.

## Scope

The milestone verifies:

- Required software installation and running state for OBS Studio, Zoom, and X Air Edit.
- OBS WebSocket connectivity, current program scene, and virtual-camera state.
- Configured X Air mixer network connectivity and any discoverable identity evidence.
- Relevant Windows audio endpoints and observable default or communications roles.
- Missing dependencies, unavailable integrations, timeouts, and malformed responses.

It produces a human-readable terminal report, an optional versioned JSON report, and sanitized diagnostic logs.

The milestone does not change application, mixer, camera, or operating-system state. It excludes GUI automation, Zoom meeting control, a volunteer dashboard, a background service, live signal-level verification, per-application audio routing unless a dependable API is confirmed during field discovery, and automatic camera switching.

## Architectural Approach

Use a hexagonal Python architecture. The application core owns read-only probe protocols; external adapters implement them. The CLI invokes a check runner, and reporters translate the resulting domain objects into terminal or JSON output.

Dependency direction is inward:

```text
CLI -> Check Runner -> Probe Protocols <- Real and Simulated Adapters
              |
              +-> Terminal, JSON, and Log Reporters
```

The core never imports Windows, OBS, or OSC client implementations. Milestone-one protocols expose query operations only, so mutation is excluded structurally rather than merely discouraged.

## Components

### Domain

The domain defines check identifiers, subsystem identifiers, statuses, evidence, remediation, timestamps, durations, and complete validation reports. These values are independent of CLI and integration libraries.

Each result contains:

- A stable check ID and subsystem.
- `PASS`, `FAIL`, `WARN`, or `UNKNOWN` status.
- One concise operator-facing summary.
- Typed key/value evidence.
- Optional concrete remediation.
- Duration in milliseconds and an ISO 8601 UTC timestamp.
- A categorized internal error when applicable.

Status meanings are fixed:

- `PASS`: the expected state was positively verified.
- `FAIL`: the check completed and found a definite problem.
- `WARN`: the system is usable but degraded or differs from a non-critical expectation.
- `UNKNOWN`: state could not be determined because of missing configuration, unavailable hardware, unsupported behavior, timeout, insufficient permission, or an invalid response.

### Application Runner

The runner loads a registry of checks, executes independent checks concurrently with bounded timeouts, and aggregates every result. A failure or exception in one check cannot stop another check. Unexpected exceptions are converted to sanitized `UNKNOWN` results and retained in diagnostic logs.

Exit codes are:

- `0`: validation ran and no result is `FAIL`; `WARN` and `UNKNOWN` remain visible.
- `1`: validation ran and at least one result is `FAIL`.
- `2`: validation could not start because installation or configuration is invalid.

### Read-Only Probe Ports

The core owns focused protocols for:

- Windows process and software discovery.
- OBS state queries.
- Mixer connectivity and identity queries.
- Windows audio endpoint and role queries.

Probe observations remain integration-oriented. Checks translate those observations into operator-facing results, which prevents vendor or library data structures from leaking into the application layer.

### CLI and Reporters

The initial command surface is:

```text
wortava validate [--profile PATH] [--format terminal|json] [--output PATH]
wortava list-checks
wortava config validate --profile PATH
wortava simulate SCENARIO
```

Terminal output groups checks by subsystem and supports colorized and plain-text modes. JSON output has an explicit schema version. Both contain a unique run ID that correlates with local logs. Normal output never includes stack traces or secrets.

## Integration Boundaries

### Windows

The Windows adapter discovers configured executable installation, running processes, and versions when observable. Process names and executable paths are profile settings because the actual church installation is not yet documented.

### OBS

The OBS adapter uses OBS WebSocket to verify connectivity and query the active program scene and virtual-camera state. It must not invoke state-changing requests. Authentication is loaded from secrets and redacted from all outputs.

### X Air Mixer

The mixer adapter begins as an OSC/UDP connectivity and discovery integration. The actual mixer model is unknown. A profile may provide host and port. Absent settings produce `UNKNOWN`; a configured device that does not respond within the timeout produces `FAIL`. Any model or identity response is retained as evidence. Device-specific channel or routing checks require a later design after field discovery.

### Windows Audio

The audio adapter inventories active input and output endpoints and their observable default or communications roles. It compares them with configured expectations. An absent configured endpoint or incorrect configured role produces `FAIL`; absent expectations produce `UNKNOWN`. Per-application routing and live signal verification are not claimed without a dependable API and documented church topology and remain outside this milestone.

### Zoom

Zoom is limited to Windows installation and process detection. Joining a meeting, inspecting meeting state, or configuring Zoom is deferred until a supported control mechanism is confirmed. The validator does not use UI automation.

### Simulated Integrations

Every real probe protocol has a fixture-backed simulated implementation. Profiles can select real or simulated adapters per subsystem. Required scenarios include all-pass, definite failure, warning/degraded state, unknown hardware, timeout, and malformed response.

## Configuration and Secrets

Configuration uses versioned TOML with three layers:

1. Checked-in safe defaults define available checks and bounded timeouts.
2. A site profile defines expected processes, OBS settings, mixer address, and audio endpoint expectations.
3. Environment variables or an ignored local secrets file provide credentials.

The complete merged configuration is validated before checks run. Invalid syntax or invalid configured values produce exit code `2` with exact field errors. Optional unknown hardware fields may be absent and cause only relevant checks to return `UNKNOWN`.

Secret values use dedicated redacted representations. Tests must demonstrate that credentials cannot appear in terminal output, JSON reports, exception messages, or logs.

## Error Handling and Observability

All external operations have configurable short timeouts and no unbounded retries. Expected integration failures map to categorized observations; unexpected exceptions are sanitized at the application boundary.

Each run creates:

- A concise terminal report.
- Optional schema-versioned JSON output.
- Rotating local diagnostic logs with sanitized check lifecycle events and exception details.
- A shared run ID across every output.

Logs support diagnosis but do not alter result semantics. Network addresses and device names may be included as evidence; credentials and secret-bearing URLs may not.

## Repository Structure

```text
src/wortava/
  cli/                 command definitions and presentation
  domain/              statuses, results, evidence, and configuration types
  application/         check registry, runner, timeout, and exit-code policy
  ports/               read-only probe protocols
  adapters/
    windows/            process, installation, and audio probes
    obs/                OBS WebSocket implementation
    xair/               OSC/UDP discovery implementation
    simulated/          deterministic fixture-backed probes
  config/              TOML loading, layering, validation, and redaction
  observability/       structured sanitized logging

tests/
  unit/                 domain, runner, configuration, and reporter tests
  contract/             shared tests for real and simulated adapter contracts
  integration/          local fake servers and protocol fixtures
  acceptance/           subprocess tests of complete CLI scenarios
  fixtures/scenarios/   deterministic validation scenarios

docs/
  architecture/         boundaries, result schema, and decisions
  field-guides/         church discovery and troubleshooting procedures
```

## Technology and Delivery

- Python 3.12.
- Standard `pyproject.toml` package metadata with a `src/` layout.
- `uv` for development environments and dependency locking.
- Ruff for formatting and linting.
- Static type checking across the core and adapters.
- pytest for unit, contract, integration, and acceptance tests.
- A standalone Windows artifact as the milestone delivery target, with PyInstaller as the initial packaging candidate rather than an architectural dependency.

The exact third-party OBS, OSC, Windows process, Windows audio, CLI, validation, and type-checking libraries are selected in the implementation plan after checking current official documentation and Windows support. Library-specific types must remain inside adapters.

## Testing Strategy

- Unit tests drive domain rules, result aggregation, configuration, redaction, and reporters.
- Contract tests run shared behavioral assertions against every real and simulated adapter implementation.
- Local fake OBS and OSC endpoints exercise network behavior without church equipment.
- Golden JSON reports protect the versioned output schema.
- Subprocess acceptance tests verify commands, reports, and exit codes.
- Cross-platform CI tests the portable core; Windows CI tests Windows integrations and builds the executable.
- A Windows packaged-artifact smoke test invokes simulated validation without requiring church hardware.
- The first on-site session follows a written discovery checklist and captures sanitized protocol fixtures for regression tests.

## Completion Criteria

The milestone is complete when:

- A developer can clone the repository and run every simulated scenario away from church equipment.
- The real validator runs on Windows without changing system state.
- Unconfigured or failed integrations do not prevent a complete report.
- The validator checks required software, OBS connectivity/current scene/virtual-camera state, mixer connectivity, and the observable Windows audio configuration.
- Terminal, JSON, and diagnostic outputs follow the documented status and redaction rules.
- The project builds and smoke-tests a standalone Windows artifact.
- The field guide captures mixer model, addresses, software versions, audio endpoints, expected OBS scene, and unresolved API gaps.

## Roadmap Constraints

Later projects build on the stable application and adapter boundaries but require separate designs:

1. Setup orchestration adds command adapters and idempotent `ensure_*` workflows, validating state after each action.
2. A volunteer dashboard exposes the application layer through a local service and guided interface.
3. Service controls compose Prepare Worship, Start Service, End Service, and Shutdown with audit and recovery behavior.
4. Camera automation consumes mixer activity, applies hysteresis and cooldowns, preserves manual override, and controls camera presets. Computer vision remains outside the initial camera project.

Actual church-environment discovery is a prerequisite for specifying device-specific automation. GUI automation remains isolated and last-resort if a later project proves no supported API or protocol exists.

## References

- [uv project documentation](https://docs.astral.sh/uv/guides/projects/)
- [PyInstaller documentation](https://pyinstaller.org/en/stable/)
