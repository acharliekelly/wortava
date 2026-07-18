import asyncio
from dataclasses import dataclass

import pytest

from wortava.adapters.obs.client import ObsAdapterError
from wortava.adapters.simulated import SimulatedProbes
from wortava.adapters.xair.client import MixerProtocolError, MixerUnavailable
from wortava.application.checks import (
    build_checks,
    evaluate_audio_endpoint,
    evaluate_mixer,
    evaluate_obs_connection,
    evaluate_obs_scene,
    evaluate_process,
    evaluate_virtual_camera,
)
from wortava.application.runner import run_validation
from wortava.config.models import (
    AudioSettings,
    MixerSettings,
    ObsSettings,
    ProcessExpectation,
    Settings,
)
from wortava.domain.models import Status
from wortava.ports.probes import AudioEndpoint, MixerObservation, ObsObservation, ProcessObservation


def test_unconfigured_mixer_is_unknown() -> None:
    status, _, _ = evaluate_mixer(MixerObservation(False, None, None, None))
    assert status is Status.UNKNOWN


def test_unreachable_configured_mixer_fails() -> None:
    status, _, _ = evaluate_mixer(MixerObservation(True, False, None, "10.0.0.2"))
    assert status is Status.FAIL


def test_configured_absent_process_fails() -> None:
    status, _, _ = evaluate_process((), ProcessExpectation(name="obs64.exe"))
    assert status is Status.FAIL


def test_configured_executable_known_missing_fails_with_installation_evidence() -> None:
    observation = ProcessObservation("obs64.exe", False, False, None, "C:/OBS/obs64.exe", None)
    status, summary, evidence = evaluate_process(
        (observation,), ProcessExpectation(name="obs64.exe", executable="C:/OBS/obs64.exe")
    )
    assert status is Status.FAIL
    assert "not installed" in summary
    assert next(item.value for item in evidence if item.key == "installed") is False


def test_unobservable_installation_is_not_claimed_as_verified() -> None:
    observation = ProcessObservation("obs64.exe", None, True, 4, None, None)
    status, summary, evidence = evaluate_process(
        (observation,), ProcessExpectation(name="obs64.exe")
    )
    assert status is Status.UNKNOWN
    assert "installation could not be verified" in summary
    assert next(item.value for item in evidence if item.key == "installed") is None


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


def test_endpoint_default_role_mismatch_fails() -> None:
    endpoint = AudioEndpoint("1", "Speakers", "render", True, False, True)
    status, summary, evidence = evaluate_audio_endpoint(
        (endpoint,), "Speakers", "render", expected_default_multimedia=True
    )
    assert status is Status.FAIL
    assert "multimedia" in summary
    assert next(item.value for item in evidence if item.key == "default_multimedia") is False


def test_build_checks_uses_unique_names_and_configured_timeouts() -> None:
    settings = Settings(
        processes=(ProcessExpectation(name="obs64.exe"),),
        obs=ObsSettings(timeout_seconds=1.25, expected_scene="Worship"),
        mixer=MixerSettings(host="10.0.0.2", timeout_seconds=3.5),
        audio=AudioSettings(expected_render_endpoint="X-AIR"),
    )
    probes = SimulatedProbes({})

    checks = build_checks(settings, probes, probes, probes, probes)

    assert len({check.name for check in checks}) == len(checks)
    assert {check.timeout_seconds for check in checks if check.subsystem.value == "obs"} == {1.25}
    assert (
        next(check for check in checks if check.name == "mixer.connection").timeout_seconds == 3.5
    )


@dataclass
class CountingProbes:
    process_calls: int = 0
    obs_calls: int = 0
    mixer_calls: int = 0
    audio_calls: int = 0
    fail_obs: bool = False
    expected_obs_failure: bool = False
    mixer_error: str | None = None

    async def inspect_processes(self) -> tuple[ProcessObservation, ...]:
        self.process_calls += 1
        return (
            ProcessObservation("one", True, True, 1, None, None),
            ProcessObservation("two", True, True, 2, None, None),
        )

    async def inspect_obs(self) -> ObsObservation:
        self.obs_calls += 1
        await asyncio.sleep(0)
        if self.fail_obs:
            raise RuntimeError("token=vendor-secret")
        if self.expected_obs_failure:
            raise ObsAdapterError("sanitized")
        return ObsObservation(True, "Expected", True)

    async def inspect_mixer(self) -> MixerObservation:
        self.mixer_calls += 1
        if self.mixer_error == "unavailable":
            raise MixerUnavailable("sanitized")
        if self.mixer_error == "protocol":
            raise MixerProtocolError("sanitized")
        return MixerObservation(False, None, None, None)

    async def inspect_audio(self) -> tuple[AudioEndpoint, ...]:
        self.audio_calls += 1
        return ()


@pytest.mark.asyncio
async def test_built_checks_share_each_snapshot_once_per_run() -> None:
    probes = CountingProbes()
    settings = Settings(
        processes=(ProcessExpectation(name="one"), ProcessExpectation(name="two")),
        obs=ObsSettings(expected_scene="Expected"),
    )
    checks = build_checks(settings, probes, probes, probes, probes)

    first = await run_validation(checks, "first")
    second = await run_validation(checks, "second")

    assert all(item.error_category is None for item in first.results)
    assert all(item.error_category is None for item in second.results)
    assert (probes.process_calls, probes.obs_calls, probes.mixer_calls, probes.audio_calls) == (
        2,
        2,
        2,
        2,
    )


@pytest.mark.asyncio
async def test_shared_snapshot_failure_is_sanitized_for_dependents() -> None:
    probes = CountingProbes(fail_obs=True)
    checks = build_checks(Settings(), probes, probes, probes, probes)

    report = await run_validation(checks, "failure")

    obs_results = [item for item in report.results if item.subsystem.value == "obs"]
    assert probes.obs_calls == 1
    assert len(obs_results) == 3
    assert all(item.status is Status.UNKNOWN for item in obs_results)
    assert all(item.error_category == "unexpected" for item in obs_results)
    assert all("secret" not in repr(item) for item in obs_results)
    unrelated = [item for item in report.results if item.subsystem.value != "obs"]
    assert unrelated
    assert all(item.error_category is None for item in unrelated)


@pytest.mark.asyncio
async def test_expected_obs_adapter_failure_is_a_definite_failure() -> None:
    probes = CountingProbes(expected_obs_failure=True)
    report = await run_validation(build_checks(Settings(), probes, probes, probes, probes), "obs")
    obs = [item for item in report.results if item.subsystem.value == "obs"]
    assert obs
    assert all(item.status is Status.FAIL for item in obs)
    assert all(item.error_category == "obs_unavailable" for item in obs)


@pytest.mark.asyncio
async def test_configured_mixer_nonresponse_fails_but_malformed_is_unknown() -> None:
    unavailable = CountingProbes(mixer_error="unavailable")
    malformed = CountingProbes(mixer_error="protocol")
    settings = Settings(mixer=MixerSettings(host="10.0.0.2"))
    unavailable_report = await run_validation(
        build_checks(settings, unavailable, unavailable, unavailable, unavailable), "timeout"
    )
    malformed_report = await run_validation(
        build_checks(settings, malformed, malformed, malformed, malformed), "malformed"
    )
    unavailable_result = next(
        x for x in unavailable_report.results if x.check_id == "mixer.connection"
    )
    malformed_result = next(
        x for x in malformed_report.results if x.check_id == "mixer.connection"
    )
    assert (unavailable_result.status, unavailable_result.error_category) == (
        Status.FAIL,
        "mixer_unavailable",
    )
    assert (malformed_result.status, malformed_result.error_category) == (
        Status.UNKNOWN,
        "mixer_protocol",
    )
