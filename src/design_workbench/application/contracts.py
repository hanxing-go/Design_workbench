from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints

type Position = tuple[StrictInt, StrictInt, StrictInt]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Box(Contract):
    low: Position
    high: Position


class StateInput(Contract):
    name: str = Field(min_length=1, max_length=128)
    properties: dict[str, str] = Field(default_factory=dict)


class Selector(Contract):
    bounds: Box | None = None
    name: str | None = None
    group: str | None = None
    region: str | None = None


class PlacedBlock(Contract):
    position: Position
    state: StateInput
    group: str = Field(default="main", min_length=1, max_length=128)


class SetBlocks(Contract):
    op: Literal["set"]
    complete_beds: bool = False
    blocks: list[PlacedBlock] = Field(min_length=1, max_length=500_000)


class Fill(Contract):
    op: Literal["fill"]
    bounds: Box
    state: StateInput
    group: str = Field(default="main", min_length=1, max_length=128)
    hollow: bool = False


class Delete(Contract):
    op: Literal["delete"]
    selector: Selector


class Replace(Contract):
    op: Literal["replace"]
    selector: Selector
    state: StateInput


class Group(Contract):
    op: Literal["group"]
    selector: Selector
    name: str = Field(min_length=1, max_length=128)


class Transform(Contract):
    op: Literal["transform"]
    selector: Selector
    origin: Position = (0, 0, 0)
    offset: Position = (0, 0, 0)
    rotation: Literal[0, 90, 180, 270] = 0
    mirror: Literal["x", "z"] | None = None
    duplicate: bool = Field(default=False, alias="copy")
    overwrite: bool = False
    group: str | None = Field(default=None, min_length=1, max_length=128)


class Array(Contract):
    op: Literal["array"]
    selector: Selector
    count: Position
    step: Position
    overwrite: bool = False
    group: str | None = Field(default=None, min_length=1, max_length=128)


class Extrude(Contract):
    op: Literal["extrude"]
    polygon: list[tuple[StrictInt, StrictInt]] = Field(min_length=3, max_length=256)
    base_y: StrictInt
    height: int = Field(ge=1, le=256)
    state: StateInput
    group: str = Field(default="main", min_length=1, max_length=128)


class Arc(Contract):
    op: Literal["arc"]
    center: Position
    radius: int = Field(ge=1, le=256)
    thickness: int = Field(default=1, ge=1, le=256)
    height: int = Field(default=1, ge=1, le=256)
    start: float = Field(default=0, ge=0, le=360)
    end: float = Field(default=360, ge=0, le=360)
    state: StateInput
    group: str = Field(default="main", min_length=1, max_length=128)


class Roof(Contract):
    op: Literal["roof"]
    bounds: Box
    ridge_axis: Literal["x", "z"] = "z"
    height: int = Field(default=8, ge=1, le=128)
    state: StateInput
    group: str = Field(default="roof", min_length=1, max_length=128)


class Window(Contract):
    op: Literal["window"]
    bounds: Box
    axis: Literal["x", "z"]
    frame: StateInput
    glass: StateInput
    group: str = Field(default="windows", min_length=1, max_length=128)


type Operation = Annotated[
    SetBlocks | Fill | Delete | Replace | Group | Transform | Array | Extrude | Arc | Roof | Window,
    Field(discriminator="op"),
]


class EditRequest(Contract):
    schema_version: Literal[1] = 1
    expected_revision: int = Field(ge=0)
    request_id: str = Field(min_length=1, max_length=128)
    operations: list[Operation] = Field(min_length=1, max_length=256)


class HistoryRequest(Contract):
    expected_revision: int = Field(ge=0)
    request_id: str = Field(min_length=1, max_length=128)


class RenameRequest(HistoryRequest):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]


class CreateRequest(Contract):
    name: str = Field(default="新建筑", min_length=1, max_length=128)
    bounds: Box = Field(default_factory=lambda: Box(low=(-512, -64, -512), high=(511, 511, 511)))


class ExportRequest(Contract):
    expected_revision: int = Field(ge=0)
    allow_lossy: bool = False
