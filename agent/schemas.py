
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
    steps: list[PlanStep] = Field(
        description="Ordered steps to complete the user's request"
    )

class DataInfo(BaseModel):
    info: dict[str,Any] = Field(
        description="Information about the dataset"
    )
