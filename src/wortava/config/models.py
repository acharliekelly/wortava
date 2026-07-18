from pydantic import BaseModel, Field, SecretStr


class ProcessExpectation(BaseModel):
    name: str
    executable: str | None = None
    required: bool = True


class ObsSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = Field(default=4455, ge=1, le=65535)
    password: SecretStr | None = None
    timeout_seconds: float = Field(default=2.0, gt=0, le=30)
    expected_scene: str | None = None


class MixerSettings(BaseModel):
    host: str | None = None
    port: int = Field(default=10024, ge=1, le=65535)
    timeout_seconds: float = Field(default=2.0, gt=0, le=30)


class AudioSettings(BaseModel):
    expected_render_endpoint: str | None = None
    expected_capture_endpoint: str | None = None
    expected_render_default_multimedia: bool | None = None
    expected_render_default_communications: bool | None = None
    expected_capture_default_multimedia: bool | None = None
    expected_capture_default_communications: bool | None = None


class Settings(BaseModel):
    adapter_mode: str = "real"
    processes: tuple[ProcessExpectation, ...] = ()
    obs: ObsSettings = ObsSettings()
    mixer: MixerSettings = MixerSettings()
    audio: AudioSettings = AudioSettings()
