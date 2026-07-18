# Result schema contract

JSON output from `wortava simulate ... --format json` and `wortava validate --format json` uses
the following schema `1.0` contract. JSON is written to stdout unless `--output PATH` is supplied;
the diagnostic-log path is written separately to stderr.

## Complete schema 1.0 example

This example contains every top-level and result field. `evidence` is a check-specific object;
its values are strings, numbers, booleans, or null.

```json
{
  "schema_version": "1.0",
  "run_id": "7bb44ae7-a507-4724-bdbe-9f540e848f64",
  "started_at": "2026-07-15T12:00:00+00:00",
  "exit_code": 0,
  "summary": {
    "PASS": 1,
    "FAIL": 0,
    "WARN": 0,
    "UNKNOWN": 0
  },
  "results": [
    {
      "check_id": "obs.connection",
      "subsystem": "obs",
      "status": "PASS",
      "summary": "OBS connection succeeded",
      "evidence": {
        "connected": true
      },
      "remediation": null,
      "duration_ms": 4,
      "checked_at": "2026-07-15T12:00:01+00:00",
      "error_category": null
    }
  ]
}
```

## Fields

- `schema_version`: contract version, currently exactly `1.0`.
- `run_id`: unique run identifier; it also appears in the diagnostic log filename and events.
- `started_at`: timezone-aware ISO 8601 run start.
- `exit_code`: `1` if any result is `FAIL`, otherwise `0`.
- `summary`: counts for all four defined statuses: `PASS`, `FAIL`, `WARN`, and `UNKNOWN`.
- `results`: ordered check results. Each has a stable `check_id`, `subsystem`, status, concise
  `summary`, check-specific `evidence`, nullable `remediation`, non-negative elapsed
  `duration_ms`, timezone-aware `checked_at`, and nullable `error_category`.

Configuration or invocation errors exit `2` before a report is produced, so `2` is not a report
`exit_code` value.

## Status and compatibility rules

`PASS` means an observation matched its expectation. `FAIL` means a configured and observable
expectation was not met, including a configured mixer that does not respond. `WARN` is a
compatible non-failing degraded condition such as a missing optional process. `UNKNOWN` means
the check could not determine state or lacked a relevant expectation/platform capability; a
malformed mixer response is unknown rather than a definite configuration failure. Only `FAIL`
causes report exit code `1`.

Consumers must use `schema_version`, tolerate object fields they do not recognize, and avoid
depending on object key order. Additive fields are allowed within `1.x`: producers may add new
fields without a major-version change, and consumers of `1.x` must ignore them. Removing or
renaming an existing field, changing a field's meaning/type, or adding, removing, renaming, or
changing the semantics/exit behavior of a status requires schema `2.0`. A `2.0` report must not
be treated as compatible with a `1.x` parser without an explicit upgrade.
