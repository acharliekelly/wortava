import json
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from wortava.adapters.obs.client import ObsWebSocketProbe
from wortava.adapters.windows.process import WindowsProcessProbe
from wortava.adapters.xair.client import XAirOscProbe
from wortava.cli import app as cli_app
from wortava.cli.app import app
from wortava.ports.probes import MixerObservation, ObsObservation, ProcessObservation

runner = CliRunner()


def stub_threaded_real_probes(monkeypatch: Any) -> None:
    async def processes(probe: WindowsProcessProbe) -> tuple[ProcessObservation, ...]:
        return tuple(
            ProcessObservation(item.name, None, True, index, None, None)
            for index, item in enumerate(probe._expectations, start=1)
        )

    async def obs(_: ObsWebSocketProbe) -> ObsObservation:
        return ObsObservation(True, None, None)

    async def mixer(_: XAirOscProbe) -> MixerObservation:
        return MixerObservation(False, None, None, None)

    monkeypatch.setattr(WindowsProcessProbe, "inspect_processes", processes)
    monkeypatch.setattr(ObsWebSocketProbe, "inspect_obs", obs)
    monkeypatch.setattr(XAirOscProbe, "inspect_mixer", mixer)


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


def test_validate_composes_real_adapters_and_reports_unsupported_audio(
    monkeypatch: Any,
) -> None:
    stub_threaded_real_probes(monkeypatch)
    result = runner.invoke(app, ["validate", "--format", "json"])

    assert result.exit_code == 0
    document = json.loads(result.stdout)
    audio = [item for item in document["results"] if item["subsystem"] == "audio"]
    assert {item["status"] for item in audio} == {"UNKNOWN"}
    assert {item["error_category"] for item in audio} == {"unsupported_platform"}
    assert result.stderr == ""


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


def test_simulate_plain_terminal_has_no_ansi_sequences() -> None:
    result = runner.invoke(app, ["simulate", "all-pass", "--plain"])

    assert result.exit_code == 0
    assert "\x1b[" not in result.stdout
    assert "PASS" in result.stdout


def test_validate_accepts_plain_terminal_option(monkeypatch: Any) -> None:
    stub_threaded_real_probes(monkeypatch)
    result = runner.invoke(app, ["validate", "--plain"])

    assert result.exit_code == 0
    assert "\x1b[" not in result.stdout
    assert "UNKNOWN" in result.stdout


def test_packaged_scenario_is_read_directly_from_traversable(monkeypatch: Any) -> None:
    class MemoryResource:
        def read_text(self, encoding: str = "utf-8") -> str:
            assert encoding == "utf-8"
            return Path("tests/fixtures/scenarios/all-pass.json").read_text(encoding=encoding)

    monkeypatch.setattr(cli_app, "_scenario_resource", lambda _: MemoryResource())

    result = runner.invoke(app, ["simulate", "all-pass", "--format", "json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["summary"]["PASS"] == 7
