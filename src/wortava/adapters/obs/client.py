import asyncio
from collections.abc import Callable
from typing import Any, Protocol

import obsws_python  # type: ignore[import-untyped]

from wortava.config.models import ObsSettings
from wortava.ports.probes import ObsObservation


class ObsClient(Protocol):
    def get_current_program_scene(self) -> Any: ...

    def get_virtual_cam_status(self) -> Any: ...


type ClientFactory = Callable[..., ObsClient]


class ObsAdapterError(RuntimeError):
    """A sanitized failure while reading OBS state."""


class ObsWebSocketProbe:
    def __init__(
        self,
        settings: ObsSettings,
        client_factory: ClientFactory = obsws_python.ReqClient,
    ) -> None:
        self._settings = settings
        self._client_factory = client_factory

    async def inspect_obs(self) -> ObsObservation:
        return await asyncio.to_thread(self._inspect_obs_sync)

    def _inspect_obs_sync(self) -> ObsObservation:
        password = (
            self._settings.password.get_secret_value()
            if self._settings.password is not None
            else ""
        )
        client: ObsClient | None = None
        observation: ObsObservation | None = None
        failed = False
        try:
            client = self._client_factory(
                host=self._settings.host,
                port=self._settings.port,
                password=password,
                timeout=self._settings.timeout_seconds,
            )
            scene = client.get_current_program_scene()
            virtual_camera = client.get_virtual_cam_status()
            observation = ObsObservation(
                connected=True,
                current_scene=scene.current_program_scene_name,
                virtual_camera_active=virtual_camera.output_active,
            )
        except Exception:
            failed = True
        finally:
            if client is not None:
                disconnect = getattr(client, "disconnect", None)
                close = getattr(client, "close", None)
                try:
                    if callable(disconnect):
                        disconnect()
                    elif callable(close):
                        close()
                except Exception:
                    pass
        if failed or observation is None:
            raise ObsAdapterError("Unable to read OBS status")
        return observation
