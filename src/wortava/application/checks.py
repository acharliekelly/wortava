from wortava.application.runner import Check, CheckOperation, Evaluation, ValidationRun
from wortava.config.models import ProcessExpectation, Settings
from wortava.domain.models import Evidence, Status, Subsystem
from wortava.ports.probes import (
    AudioEndpoint,
    AudioProbe,
    MixerObservation,
    MixerProbe,
    ObsObservation,
    ObsProbe,
    ProcessObservation,
    ProcessProbe,
)

_DEFAULT_TIMEOUT_SECONDS = 2.0


def evaluate_process(
    values: tuple[ProcessObservation, ...], expectation: ProcessExpectation
) -> Evaluation:
    expected_name = expectation.name.casefold()
    expected_executable = expectation.executable.casefold() if expectation.executable else None
    matching = next((value for value in values if value.name.casefold() == expected_name), None)
    evidence = (
        Evidence("expected_name", expectation.name),
        Evidence("expected_executable", expectation.executable),
        Evidence("running", matching.running if matching else False),
        Evidence("pid", matching.pid if matching else None),
        Evidence("version", matching.version if matching else None),
    )
    if matching is None:
        return Status.FAIL, f"Expected process {expectation.name} was not found", evidence
    if not matching.running:
        return Status.FAIL, f"Expected process {expectation.name} is not running", evidence
    if expected_executable is not None and (
        matching.executable is None or matching.executable.casefold() != expected_executable
    ):
        return (
            Status.FAIL,
            f"Expected process {expectation.name} has a different executable",
            evidence,
        )
    return Status.PASS, f"Expected process {expectation.name} is running", evidence


def evaluate_obs_connection(value: ObsObservation) -> Evaluation:
    evidence = (Evidence("connected", value.connected),)
    if not value.connected:
        return Status.FAIL, "OBS connection failed", evidence
    return Status.PASS, "OBS connection succeeded", evidence


def evaluate_obs_scene(value: ObsObservation, expected_scene: str | None) -> Evaluation:
    evidence = (
        Evidence("expected_scene", expected_scene),
        Evidence("current_scene", value.current_scene),
    )
    if expected_scene is None:
        return Status.UNKNOWN, "Expected OBS scene is not configured", evidence
    if value.current_scene != expected_scene:
        return Status.FAIL, "Current OBS scene does not match the expected scene", evidence
    return Status.PASS, "Current OBS scene matches the expected scene", evidence


def evaluate_virtual_camera(value: ObsObservation) -> Evaluation:
    evidence = (Evidence("active", value.virtual_camera_active),)
    if value.virtual_camera_active is None:
        return Status.UNKNOWN, "OBS virtual-camera state could not be determined", evidence
    if not value.virtual_camera_active:
        return Status.FAIL, "OBS virtual camera is not active", evidence
    return Status.PASS, "OBS virtual camera is active", evidence


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


def evaluate_audio_endpoint(
    values: tuple[AudioEndpoint, ...], expected_endpoint: str | None, direction: str
) -> Evaluation:
    matching = next(
        (
            value
            for value in values
            if value.direction == direction
            and expected_endpoint is not None
            and expected_endpoint.casefold()
            in {value.endpoint_id.casefold(), value.name.casefold()}
        ),
        None,
    )
    evidence = (
        Evidence("direction", direction),
        Evidence("expected_endpoint", expected_endpoint),
        Evidence("endpoint_id", matching.endpoint_id if matching else None),
        Evidence("active", matching.active if matching else None),
    )
    if expected_endpoint is None:
        return Status.UNKNOWN, f"Expected {direction} endpoint is not configured", evidence
    if matching is None:
        return Status.FAIL, f"Expected {direction} endpoint was not found", evidence
    if not matching.active:
        return Status.FAIL, f"Expected {direction} endpoint is not active", evidence
    return Status.PASS, f"Expected {direction} endpoint is active", evidence


def _process_operation(probe: ProcessProbe, expectation: ProcessExpectation) -> CheckOperation:
    async def operation(run: ValidationRun) -> Evaluation:
        return evaluate_process(await run.processes(probe), expectation)

    return operation


def _obs_connection_operation(probe: ObsProbe) -> CheckOperation:
    async def operation(run: ValidationRun) -> Evaluation:
        return evaluate_obs_connection(await run.obs(probe))

    return operation


def _obs_scene_operation(probe: ObsProbe, expected_scene: str | None) -> CheckOperation:
    async def operation(run: ValidationRun) -> Evaluation:
        return evaluate_obs_scene(await run.obs(probe), expected_scene)

    return operation


def _virtual_camera_operation(probe: ObsProbe) -> CheckOperation:
    async def operation(run: ValidationRun) -> Evaluation:
        return evaluate_virtual_camera(await run.obs(probe))

    return operation


def _mixer_operation(probe: MixerProbe) -> CheckOperation:
    async def operation(run: ValidationRun) -> Evaluation:
        return evaluate_mixer(await run.mixer(probe))

    return operation


def _audio_operation(
    probe: AudioProbe, expected_endpoint: str | None, direction: str
) -> CheckOperation:
    async def operation(run: ValidationRun) -> Evaluation:
        return evaluate_audio_endpoint(await run.audio(probe), expected_endpoint, direction)

    return operation


def build_checks(
    settings: Settings,
    process_probe: ProcessProbe,
    obs_probe: ObsProbe,
    mixer_probe: MixerProbe,
    audio_probe: AudioProbe,
) -> tuple[Check, ...]:

    checks = [
        Check(
            f"system.process.{index}.{expectation.name}",
            Subsystem.SYSTEM,
            _DEFAULT_TIMEOUT_SECONDS,
            _process_operation(process_probe, expectation),
        )
        for index, expectation in enumerate(settings.processes)
    ]
    checks.extend(
        (
            Check(
                "obs.connection",
                Subsystem.OBS,
                settings.obs.timeout_seconds,
                _obs_connection_operation(obs_probe),
            ),
            Check(
                "obs.scene",
                Subsystem.OBS,
                settings.obs.timeout_seconds,
                _obs_scene_operation(obs_probe, settings.obs.expected_scene),
            ),
            Check(
                "obs.virtual_camera",
                Subsystem.OBS,
                settings.obs.timeout_seconds,
                _virtual_camera_operation(obs_probe),
            ),
            Check(
                "mixer.connection",
                Subsystem.MIXER,
                settings.mixer.timeout_seconds,
                _mixer_operation(mixer_probe),
            ),
            Check(
                "audio.render",
                Subsystem.AUDIO,
                _DEFAULT_TIMEOUT_SECONDS,
                _audio_operation(
                    audio_probe,
                    settings.audio.expected_render_endpoint,
                    "render",
                ),
            ),
            Check(
                "audio.capture",
                Subsystem.AUDIO,
                _DEFAULT_TIMEOUT_SECONDS,
                _audio_operation(
                    audio_probe,
                    settings.audio.expected_capture_endpoint,
                    "capture",
                ),
            ),
        )
    )
    return tuple(checks)
