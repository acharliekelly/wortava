import asyncio
import json
import tomllib
import uuid
from enum import StrEnum
from importlib.resources import files
from pathlib import Path
from typing import Annotated, NoReturn, Protocol

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from wortava.adapters.simulated import SimulatedProbes
from wortava.application.checks import build_checks
from wortava.application.runner import run_validation
from wortava.cli.reporters import render_terminal, report_to_dict
from wortava.config.loader import load_settings
from wortava.config.models import Settings
from wortava.domain.models import ValidationReport
from wortava.ports.probes import AudioProbe, MixerProbe, ObsProbe, ProcessProbe


class OutputFormat(StrEnum):
    TERMINAL = "terminal"
    JSON = "json"


class AdapterUnavailableError(RuntimeError):
    """Raised until the real, read-only adapter implementations are available."""


class ProbeSuite(ProcessProbe, ObsProbe, MixerProbe, AudioProbe, Protocol):
    """Probe bundle constructed by the CLI composition root."""


app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)
config_app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)
app.add_typer(config_app, name="config")


def _error(prefix: str, error: Exception) -> NoReturn:
    detail = str(error).splitlines()[0]
    Console(stderr=True).print(f"{prefix}: {detail}")
    raise typer.Exit(2)


def _default_settings_path() -> Path:
    return Path(__file__).resolve().parents[3] / "config" / "defaults.toml"


def _scenario_path(name: str) -> Path:
    if not name or Path(name).name != name or name.endswith(".json"):
        raise ValueError(f"unknown scenario {name!r}")
    development_path = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "scenarios"
    development_scenario = development_path / f"{name}.json"
    if development_scenario.is_file():
        return development_scenario
    resource = files("wortava.scenarios").joinpath(f"{name}.json")
    if not resource.is_file():
        raise ValueError(f"unknown scenario {name!r}")
    return Path(str(resource))


def _load_scenario(name: str) -> tuple[Settings, SimulatedProbes]:
    path = _scenario_path(name)
    data = json.loads(path.read_text(encoding="utf-8"))
    settings = Settings.model_validate(data.get("settings", {"adapter_mode": "simulated"}))
    return settings, SimulatedProbes(data)


def _real_probes(_: Settings) -> ProbeSuite:
    raise AdapterUnavailableError("real adapters are not available in this build")


def _run(settings: Settings, probes: ProbeSuite) -> ValidationReport:
    checks = build_checks(settings, probes, probes, probes, probes)
    return asyncio.run(run_validation(checks, str(uuid.uuid4())))


def _render(report: ValidationReport, output_format: OutputFormat, output: Path | None) -> None:
    if output_format is OutputFormat.JSON:
        rendered = json.dumps(report_to_dict(report), indent=2) + "\n"
        if output is not None:
            output.write_text(rendered, encoding="utf-8")
        else:
            typer.echo(rendered, nl=False)
        return
    if output is not None:
        with output.open("w", encoding="utf-8") as stream:
            render_terminal(report, Console(file=stream, color_system=None))
    else:
        render_terminal(report, Console())


@app.command()
def simulate(
    scenario: str,
    output_format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.TERMINAL,
    output: Annotated[Path | None, typer.Option("--output")] = None,
) -> None:
    """Run a deterministic, fixture-backed validation scenario."""
    try:
        settings, probes = _load_scenario(scenario)
        report = _run(settings, probes)
        _render(report, output_format, output)
    except (OSError, ValueError, json.JSONDecodeError, ValidationError) as error:
        _error("Simulation error", error)
    raise typer.Exit(report.exit_code)


@app.command("validate")
def validate_system(
    profile: Annotated[Path | None, typer.Option("--profile")] = None,
    output_format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.TERMINAL,
    output: Annotated[Path | None, typer.Option("--output")] = None,
) -> None:
    """Validate the configured system using real read-only adapters."""
    try:
        settings = load_settings(_default_settings_path(), profile)
        probes = _real_probes(settings)
        report = _run(settings, probes)
        _render(report, output_format, output)
    except (OSError, tomllib.TOMLDecodeError, ValidationError) as error:
        _error("Configuration error", error)
    except AdapterUnavailableError as error:
        _error("Adapter error", error)
    raise typer.Exit(report.exit_code)


@config_app.command("validate")
def validate_config(
    profile: Annotated[Path, typer.Option("--profile")],
) -> None:
    """Validate a site profile without contacting any equipment."""
    try:
        load_settings(_default_settings_path(), profile)
    except (OSError, tomllib.TOMLDecodeError, ValidationError) as error:
        _error("Configuration error", error)
    typer.echo("Configuration is valid")


@app.command("list-checks")
def list_checks() -> None:
    """List stable checks supplied by the default configuration."""
    try:
        settings = load_settings(_default_settings_path(), None)
    except (OSError, tomllib.TOMLDecodeError, ValidationError) as error:
        _error("Configuration error", error)
    probes = SimulatedProbes({})
    table = Table("Check ID", "Subsystem")
    for check in build_checks(settings, probes, probes, probes, probes):
        table.add_row(check.name, check.subsystem.value)
    Console().print(table)


def main() -> None:
    app()
