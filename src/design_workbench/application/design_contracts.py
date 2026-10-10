"""Persistent controls for externally driven AI design sessions."""

from typing import Any, Literal

from pydantic import ConfigDict, Field, StrictInt

from .contracts import Contract, EditRequest
from .tool_contracts import ProjectTool, ToolRequest

type Stage = Literal["planning", "building", "reviewing", "revising", "exporting"]


class DesignBudget(Contract):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    tool_calls: StrictInt = Field(default=256, ge=1, le=4096)
    model_calls: StrictInt = Field(default=64, ge=1, le=4096)
    seconds: StrictInt = Field(default=1800, ge=1, le=86400)
    tokens: StrictInt = Field(default=3_000_000, ge=1)
    cost_usd: float | None = Field(default=None, gt=0)
    revisions: StrictInt = Field(default=64, ge=1, le=1024)


class DesignCreate(ProjectTool):
    request_id: str = Field(min_length=1, max_length=128)
    expected_revision: StrictInt = Field(ge=0)
    prompt: str = Field(min_length=1, max_length=16000)
    model: str = Field(default="", max_length=256)
    auto_build: bool = False
    budget: DesignBudget = Field(default_factory=DesignBudget)


class DesignList(ProjectTool):
    pass


class DesignRef(ToolRequest):
    run_id: str = Field(pattern=r"^[a-f0-9]{32}$")


class DesignAction(DesignRef):
    request_id: str = Field(min_length=1, max_length=128)


class DesignUpdate(DesignAction):
    stage: Stage
    message: str = Field(default="", max_length=2000)


class DesignUsage(DesignAction):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    # Cumulative counters, not increments: retrying cannot double-charge usage.
    input_tokens: StrictInt = Field(ge=0)
    cached_input_tokens: StrictInt = Field(default=0, ge=0)
    output_tokens: StrictInt = Field(ge=0)
    model_calls: StrictInt = Field(default=0, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    source: str = Field(min_length=1, max_length=512)


class DesignCall(DesignAction):
    tool: str = Field(min_length=1, max_length=80)
    arguments: dict[str, Any]


class DesignPropose(DesignAction):
    request: EditRequest
    explanation: str = Field(min_length=1, max_length=4000)


class DesignDecision(DesignAction):
    proposal_id: str = Field(pattern=r"^[a-f0-9]{32}$")


class DesignResume(DesignAction):
    # An explicit extension; previously consumed budget is never reset.
    budget: DesignBudget | None = None


class DesignFinish(DesignAction):
    outcome: Literal["succeeded", "failed"]
    message: str = Field(min_length=1, max_length=2000)


class CandidateSave(DesignAction):
    expected_revision: StrictInt = Field(ge=0)
    name: str = Field(min_length=1, max_length=128)
    feedback: str = Field(default="", max_length=4000)


class CandidateOpen(Contract):
    request_id: str = Field(min_length=1, max_length=128)
