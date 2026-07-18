from pathlib import Path

import pytest

from wortava.adapters.simulated import SimulatedProbes


@pytest.mark.asyncio
async def test_all_pass_fixture_implements_every_probe_contract() -> None:
    probes = SimulatedProbes.from_path(Path("tests/fixtures/scenarios/all-pass.json"))
    assert (await probes.inspect_processes())[0].running is True
    assert (await probes.inspect_obs()).virtual_camera_active is True
    assert (await probes.inspect_mixer()).reachable is True
    assert len(await probes.inspect_audio()) == 2
