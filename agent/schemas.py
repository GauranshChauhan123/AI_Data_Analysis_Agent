
from typing import Any, Literal
from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    tool: Literal[
        "inspect_data",
        "validate_dataset",
        "analyze_data",
        "modify_dataset",
        "generate_graph",
        "generate_report"
    ]
    arguments: dict[str, Any] = Field(
        description="Arguments required by the selected tool"
    )


class Plan(BaseModel):
    needs_clarification: bool = Field(
        default=False,
        description="Set to true if user request is ambiguous, lacks required info, or cannot be fulfilled."
    )
    clarification_question: str = Field(
        default="",
        description="The specific question to ask the user if more details or clarification are needed."
    )
    steps: list[PlanStep] = Field(
        default_factory=list,
        description="Ordered steps to complete the user's request when info is sufficient"
    )


class DataInfo(BaseModel):
    info: dict[str,Any] = Field(
        description="Information about the dataset"
    )
