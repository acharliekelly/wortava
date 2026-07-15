import json
from pathlib import Path

from typer.testing import CliRunner

from wortava.cli.app import app

runner = CliRunner()


def test_simulate_all_pass_emits_json_and_zero_exit() -> None:
    result = runner.invoke(app, ["simulate", "all-pass", "--format", "json"])

    assert result.exit_code == 0
    document = json.loads(result.stdout)
    assert document["schema_version"] == "1.0"
    assert {item["status"] for item in document["results"]} == {"PASS"}
    assert result.stderr == ""


def test_simulate_unknown_hardware_emits_unknown_and_zero_exit() -> None:
    result = runner.invoke(app, ["simulate", "unknown-hardware", "--format", "json"])

    assert result.exit_code == 0
    document = json.loads(result.stdout)
    assert "UNKNOWN" in {item["status"] for item in document["results"]}
    assert result.stderr == ""


def test_unknown_simulation_name_is_rejected_without_path_traversal() -> None:
    result = runner.invoke(app, ["simulate", "../all-pass", "--format", "json"])

    assert result.exit_code == 2
    assert result.stdout == ""
    assert "Simulation error:" in result.stderr


def test_invalid_profile_exits_two() -> None:
    result = runner.invoke(app, ["config", "validate", "--profile", "missing.toml"])

    assert result.exit_code == 2
    assert result.stdout == ""
    assert "Configuration error:" in result.stderr


def test_config_validate_accepts_valid_profile() -> None:
    result = runner.invoke(
        app, ["config", "validate", "--profile", "config/site.example.toml"]
    )

    assert result.exit_code == 0
    assert "Configuration is valid" in result.stdout


def test_validate_reports_unavailable_real_adapters_on_stderr() -> None:
    result = runner.invoke(app, ["validate", "--format", "json"])

    assert result.exit_code == 2
    assert result.stdout == ""
    assert "Adapter error:" in result.stderr


def test_json_output_file_keeps_stdout_empty(tmp_path: Path) -> None:
    destination = tmp_path / "report.json"

    result = runner.invoke(
        app,
        ["simulate", "all-pass", "--format", "json", "--output", str(destination)],
    )

    assert result.exit_code == 0
    assert result.stdout == ""
    assert json.loads(destination.read_text(encoding="utf-8"))["schema_version"] == "1.0"


def test_list_checks_is_stable_and_includes_subsystems() -> None:
    first = runner.invoke(app, ["list-checks"])
    second = runner.invoke(app, ["list-checks"])

    assert first.exit_code == 0
    assert first.stdout == second.stdout
    assert "obs.connection" in first.stdout
    assert "audio.render" in first.stdout
    assert "system" in first.stdout
