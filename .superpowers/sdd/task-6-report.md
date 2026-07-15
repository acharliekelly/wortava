# Task 6 Report: Terminal and Versioned JSON CLI Flows

## Status

Complete. The CLI now exposes simulated validation, configuration validation,
real-validation startup handling, stable check listing, terminal reporting, and
schema-versioned JSON reporting. JSON mode writes JSON only to stdout; diagnostics
are written to stderr.

## RED evidence

Command:

```console
uv run pytest tests/unit/cli tests/acceptance -q
```

Result: collection failed with two `ModuleNotFoundError: No module named
'wortava.cli'` errors. This was the expected failure because the CLI package and
reporters did not exist.

## GREEN evidence

Focused command:

```console
uv run pytest tests/unit/cli tests/acceptance -q
```

Result: `10 passed in 0.11s`.

Public command smoke tests:

```console
uv run wortava simulate all-pass --format terminal
uv run wortava simulate unknown-hardware --format json
uv run wortava list-checks
```

Results: all-pass rendered seven grouped PASS results and exited 0;
unknown-hardware emitted valid schema 1.0 JSON with five UNKNOWN results and
exited 0; list-checks rendered stable default check IDs and subsystem names.

Fresh full verification:

```console
uv run pytest -q
uv run ruff check src tests
uv run mypy src
git diff --check
```

Results:

- `31 passed in 0.22s`
- `All checks passed!`
- `Success: no issues found in 18 source files`
- `git diff --check` exited 0 with no output

## Files

- Added `src/wortava/cli/__init__.py`
- Added `src/wortava/cli/app.py`
- Added `src/wortava/cli/reporters.py`
- Added `src/wortava/__main__.py`
- Added packaged scenarios under `src/wortava/scenarios/`
- Added CLI unit and acceptance tests
- Added `tests/fixtures/golden/all-pass-report.json`
- Added scenario-owned settings to development fixtures

## Commit

`feat: expose validator reports through CLI`

## Self-review

- Confirmed the JSON top-level contract and every required result field against a
  fixed golden fixture.
- Confirmed simulation names cannot escape the scenario directories.
- Confirmed configuration, simulation, output, and adapter startup failures exit 2
  with concise stderr diagnostics and no JSON stdout contamination.
- Confirmed terminal output groups results by subsystem.
- Confirmed the packaged scenarios mirror the development scenarios.
- Kept real adapter construction behind the `ProbeSuite` factory boundary without
  inventing vendor adapters or UI automation.

## Concerns

The real adapter factory intentionally raises a concise unavailable error and
`validate` exits 2. Tasks 7-9 must replace that factory behavior when their probe
implementations exist.

## Review fixes

Addressed the Task 6 review findings in a follow-up change:

- Added explicit `--plain` flags to `simulate` and `validate`; terminal and error
  consoles disable Rich colors when selected.
- Changed packaged scenario loading to return and read an
  `importlib.resources.abc.Traversable` directly. No packaged resource is converted
  to a path or string, and the existing safe scenario-name validation remains in
  place.
- Added an acceptance test using an in-memory, non-filesystem-style resource object
  that only supplies `read_text()`.
- Added an explicit schema 1.0 guard in `report_to_dict()` and rejection coverage
  for unsupported report versions.

### Review-fix RED evidence

```console
uv run pytest tests/unit/cli tests/acceptance -q
```

Result: `4 failed, 10 passed in 0.22s`. The four expected failures showed the
missing schema rejection, missing `simulate --plain`, missing `validate --plain`,
and missing Traversable resource seam.

### Review-fix GREEN evidence

Focused verification:

```console
uv run pytest tests/unit/cli tests/acceptance -q
```

Result: `14 passed in 0.12s`.

Fresh full verification:

```console
uv run pytest -q
uv run ruff check src tests
uv run mypy src
git diff --check
```

Exact results:

- `35 passed in 0.24s`
- `All checks passed!`
- `Success: no issues found in 18 source files`
- `git diff --check` exited 0 with no output

### Review-fix files

- `src/wortava/cli/app.py`
- `src/wortava/cli/reporters.py`
- `tests/acceptance/test_cli.py`
- `tests/unit/cli/test_reporters.py`
- `.superpowers/sdd/task-6-report.md`

### Review-fix self-review

- Confirmed both user-facing validation commands accept the explicit plain mode.
- Confirmed plain simulated terminal stdout and plain validation-error stderr contain
  no ANSI escape sequences.
- Confirmed packaged resources are read within the Traversable abstraction and the
  development fixture path remains supported.
- Confirmed the public runner still produces schema 1.0, while reporters fail fast
  on unsupported versions instead of publishing an accidental contract.

The only remaining concern is unchanged: Tasks 7-9 must wire the real probe suite
into the narrow adapter factory before `validate` can run against equipment.
