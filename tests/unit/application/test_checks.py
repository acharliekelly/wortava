from wortava.adapters.simulated import SimulatedProbes
from wortava.application.checks import (
    build_checks,
    evaluate_audio_endpoint,
    evaluate_mixer,
    evaluate_obs_connection,
    evaluate_obs_scene,
    evaluate_process,
    evaluate_virtual_camera,
)
from wortava.config.models import (
    AudioSettings,
    MixerSettings,
    ObsSettings,
    ProcessExpectation,
    Settings,
)
from wortava.domain.models import Status
from wortava.ports.probes import AudioEndpoint, MixerObservation, ObsObservation


def test_unconfigured_mixer_is_unknown() -> None:
    status, _, _ = evaluate_mixer(MixerObservation(False, None, None, None))
    assert status is Status.UNKNOWN


def test_unreachable_configured_mixer_fails() -> None:
    status, _, _ = evaluate_mixer(MixerObservation(True, False, None, "10.0.0.2"))
    assert status is Status.FAIL


def test_configured_absent_process_fails() -> None:
    status, _, _ = evaluate_process((), ProcessExpectation(name="obs64.exe"))
    assert status is Status.FAIL


def test_obs_connection_failure_fails() -> None:
    status, _, _ = evaluate_obs_connection(ObsObservation(False, None, None))
    assert status is Status.FAIL


def test_scene_mismatch_fails_and_absent_expectation_is_unknown() -> None:
    observation = ObsObservation(True, "Actual", True)
    assert evaluate_obs_scene(observation, "Expected")[0] is Status.FAIL
    assert evaluate_obs_scene(observation, None)[0] is Status.UNKNOWN


def test_unknown_virtual_camera_state_is_unknown() -> None:
    assert evaluate_virtual_camera(ObsObservation(True, None, None))[0] is Status.UNKNOWN


def test_endpoint_absence_fails_and_absent_expectation_is_unknown() -> None:
    endpoint = AudioEndpoint("1", "Speakers", "render", True, False, False)
    assert evaluate_audio_endpoint((endpoint,), "X-AIR", "render")[0] is Status.FAIL
    assert evaluate_audio_endpoint((endpoint,), None, "render")[0] is Status.UNKNOWN


def test_build_checks_uses_unique_names_and_configured_timeouts() -> None:
    settings = Settings(
        processes=(ProcessExpectation(name="obs64.exe"),),
        obs=ObsSettings(timeout_seconds=1.25, expected_scene="Worship"),
        mixer=MixerSettings(host="10.0.0.2", timeout_seconds=3.5),
        audio=AudioSettings(expected_render_endpoint="X-AIR"),
    )
    probes = SimulatedProbes({})

    checks = build_checks(settings, probes)

    assert len({check.name for check in checks}) == len(checks)
    assert {check.timeout_seconds for check in checks if check.subsystem.value == "obs"} == {1.25}
    assert (
        next(check for check in checks if check.name == "mixer.connection").timeout_seconds == 3.5
    )
