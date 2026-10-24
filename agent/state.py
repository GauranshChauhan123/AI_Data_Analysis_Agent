
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class MessageState(TypedDict):
    messages: Annotated[list, add_messages]

    file_path: str
    user_request: str

    plan: list[dict]
    current_step: int

    dataset_info: dict
    results: list[dict]

    output_path: str
    errors: list[str]

    summary: dict
