from typing import Literal

from pydantic import Field

from .contracts import Contract, CreateRequest, EditRequest, HistoryRequest, Selector, StateInput
from .render_contracts import RenderRequest


class ToolRequest(Contract):
    schema_version: Literal[1] = 1


class SearchTool(ToolRequest):
    minecraft_version: str | None = Field(default=None, min_length=1, max_length=32)
    project: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    query: str = Field(default="", max_length=256)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=24, ge=1, le=128)
    category: str = Field(default="", max_length=128)


class MaterialTool(ToolRequest):
    minecraft_version: str | None = Field(default=None, min_length=1, max_length=32)
    project: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    state: StateInput


class CreateTool(ToolRequest):
    request_id: str = Field(min_length=1, max_length=128)
    request: CreateRequest


class ProjectTool(ToolRequest):
    project: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")


class InspectTool(ProjectTool):
    selector: Selector = Field(default_factory=Selector)
    limit: int = Field(default=128, ge=1, le=2048)


class EditTool(ProjectTool):
    request: EditRequest


class HistoryTool(ProjectTool):
    request: HistoryRequest


class ImportTool(HistoryTool):
    source: str = Field(min_length=1, max_length=4096)


class ExportTool(ProjectTool):
    request_id: str = Field(min_length=1, max_length=128)
    expected_revision: int = Field(ge=0)
    output: str | None = Field(default=None, max_length=4096)
    allow_lossy: bool = False


class RenderTool(ProjectTool):
    request: RenderRequest


class TaskTool(ToolRequest):
    task_id: str = Field(pattern=r"^[a-f0-9]{32}$")
