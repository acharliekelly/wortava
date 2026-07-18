# Wortava

Wortava is a read-only command-line validator for a church Windows A/V workstation. It
queries expected processes, OBS, an X Air mixer, and Windows audio endpoints, then emits a
human-readable report or versioned JSON. Fixture-backed simulations let developers and
operators learn the workflow without church hardware.

## Safety boundary

Milestone one only observes state. It does not start or stop applications, change OBS scenes,
control the virtual camera, alter mixer parameters, change Windows audio routing, or join Zoom
meetings. Real validation contacts the configured OBS WebSocket and mixer and reads local
process/audio state; it never intentionally mutates them. Treat reports and logs as operational
data and review them before sharing.

## Prerequisites and installation

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Windows for real Core Audio inspection; simulations work on Windows, macOS, and Linux

Install the locked development environment from the repository root:

```console
$ uv sync --extra dev
```

On the church Windows workstation, include the Windows integration:

```console
$ uv sync --extra dev --extra windows
```

`uv` uses its normal user cache during ordinary installation and command execution.

## Quick start

Run the all-passing, hardware-free scenario and print schema `1.0` JSON:

<!-- smoke-test -->
```console
$ uv run wortava simulate all-pass --format json
```

The command prints JSON to standard output, the diagnostic-log path to standard error, and
returns `0`.

## Simulator scenarios

`all-pass` demonstrates configured, observable equipment with all checks passing.
`unknown-hardware` demonstrates missing or unsupported observations; it includes `UNKNOWN`
results but still returns `0` because no check fails.

<!-- smoke-test -->
```console
$ uv run wortava simulate unknown-hardware --plain
```

Use `--format terminal|json` (terminal is the default), `--plain` to suppress terminal color,
and `--output PATH` to write the selected report format to a file. Simulations are deterministic
fixture-backed probes, though each invocation creates a fresh run ID, timestamps, and local log.

## Create and validate a site profile

Copy `config/site.example.toml` to a site-owned path and replace only the facts confirmed during
[on-site discovery](docs/field-guides/church-discovery.md). Defaults already define the expected
OBS, Zoom, and X Air Edit process names and network timeouts. A profile overrides only its listed
sections. Do not commit OBS passwords or other credentials.

Validate profile syntax and values without contacting equipment:

<!-- smoke-test -->
```console
$ uv run wortava config validate --profile config/site.example.toml
```

## Commands

- `uv run wortava validate [--profile PATH] [--format terminal|json] [--output PATH] [--plain]`
  runs the real read-only adapters. Omit `--profile` to use `config/defaults.toml` alone.
- `uv run wortava simulate SCENARIO [...]` runs a bundled deterministic scenario.
- `uv run wortava config validate --profile PATH` validates configuration only.
- `uv run wortava list-checks` lists stable check IDs and subsystems.
- `uv run wortava --help` and each command's `--help` show the authoritative CLI syntax.

Real validation on the church workstation:

```console
$ uv run wortava validate --profile config/church.toml --format json --output report.json
```

The real command may return `1` when the workstation is not in its expected state; that is a
validation result, not a CLI crash.

## Statuses and exit codes

| Status | Meaning |
| --- | --- |
| `PASS` | The observed state matches the configured expectation. |
| `FAIL` | A configured, testable expectation was not met. |
| `WARN` | A non-fatal concern was observed. Schema `1.0` reserves this status even when current checks do not emit it. |
| `UNKNOWN` | The state could not be determined or the relevant expectation/hardware support is absent. |

| Exit | Meaning |
| ---: | --- |
| `0` | The run completed with no `FAIL` results; `WARN` and `UNKNOWN` do not make the run fail. |
| `1` | At least one result is `FAIL`. |
| `2` | Invocation, scenario, or configuration input is invalid or unreadable. |

See [the result schema contract](docs/architecture/result-schema.md) before consuming JSON.

## Logs

Every simulation or real validation creates `logs/wortava-<run_id>.jsonl`. The CLI prints the
exact `Diagnostic log:` path after the report (to stderr for JSON so stdout remains parseable).
Use the report's `run_id` to locate the matching log. Logs rotate at 1 MB with five backups and
contain sanitized lifecycle/error events, not a substitute for careful handling: inspect them
before sending them outside the site.

## Development gates

```console
$ uv run pytest
$ uv run ruff check .
$ uv run mypy src/wortava
```

The documentation smoke test runs only commands explicitly marked `<!-- smoke-test -->`; those
commands must remain deterministic, hardware-free, and successful.

## Windows build

Each successful GitHub Actions CI run publishes the onedir artifact `wortava-windows-x64` from
the `Windows package` job. Open the repository's Actions page, select the commit's completed CI
run, and download `wortava-windows-x64` from its Artifacts section. Extract the entire `wortava`
directory, keep its files together, and run `wortava/wortava.exe`; the executable depends on the
adjacent files in that directory. Verify it against the included `SHA256SUMS.txt` before use.

To build the same layout on Windows from a checkout:

```console
> uv sync --extra dev --extra windows
> uv run pyinstaller wortava.spec --clean
> uv run pytest tests/acceptance/test_packaged_cli.py --run-windows-package -q
```

The output executable is `dist/wortava/wortava.exe`. A normal `pytest` run skips the packaged
smoke test; the explicit flag requires the executable and reports how to build it when absent.

## Roadmap

- Download and field-test the CI-built artifact on the church workstation.
- Complete on-site discovery and replace example profile values with sanitized confirmed facts.
- Keep mutation and automation out of milestone one; consider later controls only through a
  separately reviewed, explicit safety design and supported vendor APIs.
