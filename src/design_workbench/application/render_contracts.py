from typing import Literal

from pydantic import Field, FiniteFloat, model_validator

from .contracts import Box, Contract


class Camera(Contract):
    position: tuple[FiniteFloat, FiniteFloat, FiniteFloat]
    target: tuple[FiniteFloat, FiniteFloat, FiniteFloat]
    fov: FiniteFloat = Field(default=40, ge=10, le=100)

    @model_validator(mode="after")
    def check_direction(self) -> "Camera":
        if self.position == self.target:
            raise ValueError("camera.position 和 camera.target 不能相同")
        if any(abs(value) > 1_000_000 for value in (*self.position, *self.target)):
            raise ValueError("相机坐标绝对值不能超过 1000000")
        return self


class View(Contract):
    name: Literal["front", "side", "back", "top", "iso", "custom"] = "iso"
    layer: int | None = Field(default=None, ge=-4096, le=4096)
    camera: Camera | None = None
    bounds: Box | None = None

    @model_validator(mode="after")
    def check_custom(self) -> "View":
        if self.name == "custom" and self.camera is None:
            raise ValueError("custom 视角必须指定 camera")
        if self.bounds and any(
            a > b for a, b in zip(self.bounds.low, self.bounds.high, strict=True)
        ):
            raise ValueError("bounds.low 不能超过 bounds.high")
        return self


class RenderRequest(Contract):
    schema_version: Literal[1] = 1
    expected_revision: int = Field(ge=0)
    request_id: str = Field(min_length=1, max_length=128)
    views: list[View] = Field(
        default_factory=lambda: [
            View(name="front"),
            View(name="side"),
            View(name="top"),
            View(name="iso"),
        ],
        min_length=1,
        max_length=6,
    )
    width: int = Field(default=768, ge=64, le=1600)
    height: int = Field(default=768, ge=64, le=1600)
    timeout: float = Field(default=60, gt=0, le=120)
    wait: bool = True

    @model_validator(mode="after")
    def check_pixels(self) -> "RenderRequest":
        if self.width * self.height * len(self.views) > 8_000_000:
            raise ValueError("所有视角总像素不能超过 8000000")
        return self
