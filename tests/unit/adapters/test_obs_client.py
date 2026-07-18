from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import SecretStr

from wortava.adapters.obs.client import ObsAdapterError, ObsWebSocketProbe
from wortava.config.models import ObsSettings
from wortava.ports.probes import ObsObservation


class FakeObsClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def get_current_program_scene(self) -> SimpleNamespace:
        self.calls.append("get_current_program_scene")
        return SimpleNamespace(current_program_scene_name="Worship Wide")

    def get_virtual_cam_status(self) -> SimpleNamespace:
        self.calls.append("get_virtual_cam_status")
        return SimpleNamespace(output_active=True)

    def disconnect(self) -> None:
        self.calls.append("disconnect")


async def run_inline(operation: Any) -> Any:
    return operation()


@pytest.mark.asyncio
async def test_obs_probe_queries_only_read_only_status_methods() -> None:
    client = FakeObsClient()
    factory_calls: list[dict[str, Any]] = []

    def client_factory(**kwargs: Any) -> FakeObsClient:
        factory_calls.append(kwargs)
        return client

    settings = ObsSettings(
        host="obs.local", port=4455, password=SecretStr("do-not-leak"), timeout_seconds=3
    )
    probe = ObsWebSocketProbe(
        settings, client_factory=client_factory, run_sync=run_inline
    )

    observation = await probe.inspect_obs()

    assert observation == ObsObservation(True, "Worship Wide", True)
    assert factory_calls == [
        {"host": "obs.local", "port": 4455, "password": "do-not-leak", "timeout": 3.0}
    ]
    assert client.calls == [
        "get_current_program_scene",
        "get_virtual_cam_status",
        "disconnect",
    ]


@pytest.mark.asyncio
async def test_obs_connection_error_is_typed_and_redacts_password() -> None:
    password = "password-must-stay-secret"

    def client_factory(**_kwargs: Any) -> FakeObsClient:
        raise ConnectionError(f"could not authenticate with {password}")

    probe = ObsWebSocketProbe(
        ObsSettings(password=SecretStr(password)),
        client_factory=client_factory,
        run_sync=run_inline,
    )

    with pytest.raises(ObsAdapterError) as caught:
        await probe.inspect_obs()

    assert password not in str(caught.value)
    assert password not in repr(caught.value)
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
