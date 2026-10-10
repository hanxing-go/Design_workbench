import json
import os
import tomllib
from pathlib import Path
from typing import Any

from platformdirs import user_cache_path, user_config_path, user_data_path, user_log_path
from pydantic import BaseModel, ConfigDict, Field


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_dir: Path = Field(
        default_factory=lambda: user_data_path("DesignWorkbench", appauthor=False)
    )
    cache_dir: Path = Field(
        default_factory=lambda: user_cache_path("DesignWorkbench", appauthor=False)
    )
    log_dir: Path = Field(default_factory=lambda: user_log_path("DesignWorkbench", appauthor=False))
    minecraft_version: str = "1.20.1"
    max_blocks: int = Field(default=250_000, ge=1, le=5_000_000)
    max_edit_cells: int = Field(default=500_000, ge=1, le=5_000_000)
    max_selection_volume: int = Field(default=2_000_000, ge=1, le=16_000_000)
    max_operations: int = Field(default=256, ge=1, le=4096)
    database_timeout: float = Field(default=10.0, gt=0, le=60)
    tool_timeout: float = Field(default=30.0, gt=0, le=120)
    max_tool_response_bytes: int = Field(default=2_000_000, ge=4096, le=8_000_000)
    render_timeout: float = Field(default=60.0, gt=0, le=120)
    max_render_jobs: int = Field(default=16, ge=1, le=64)
    render_workers: int = Field(default=2, ge=1, le=4)
    max_render_cells: int = Field(default=100_000, ge=1, le=500_000)
    max_render_bytes: int = Field(default=16_000_000, ge=1024, le=64_000_000)
    browser_channel: str | None = None

    @classmethod
    def load(cls, config_file: Path | None = None, **overrides: Any) -> "Settings":
        configured = config_file or Path(
            os.environ.get(
                "DW_CONFIG",
                str(user_config_path("DesignWorkbench", appauthor=False) / "config.toml"),
            )
        )
        values: dict[str, Any] = {}
        if configured.is_file():
            with configured.open("rb") as handle:
                values = tomllib.load(handle)
            for key in ("data_dir", "cache_dir", "log_dir"):
                if key in values:
                    candidate = Path(values[key]).expanduser()
                    values[key] = (
                        candidate if candidate.is_absolute() else configured.parent / candidate
                    )
        for key in cls.model_fields:
            env_key = f"DW_{key.upper()}"
            if env_key in os.environ:
                values[key] = os.environ[env_key]
        values.update({key: value for key, value in overrides.items() if value is not None})
        settings = cls.model_validate(values)
        for key in ("data_dir", "cache_dir", "log_dir"):
            setattr(settings, key, getattr(settings, key).expanduser().resolve())
        return settings

    def json_dict(self) -> dict[str, Any]:
        return json.loads(self.model_dump_json())  # type: ignore[no-any-return]
