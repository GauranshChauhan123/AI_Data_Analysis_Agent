import os
import json
from dotenv import load_dotenv
from typing import Annotated, Literal, TypedDict
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import START, END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from agent.state import MessageState
from agent.schemas import Plan, DataInfo
from agent.summary_node import summary_node

from tools.data_tool import inspect_data, validate_dataset
from tools.analyze_tool import analyze_data
from tools.modify_data import modify_dataset
from tools.graph_tool import generate_graph
from tools.report_tool import generate_report

load_dotenv()


tool_list = [
    inspect_data,
    validate_dataset,
    analyze_data,
    modify_dataset,
    generate_graph,
    generate_report
]


def create_model():
    base_model = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        request_timeout=60,
        max_retries=5
    )
    return base_model, base_model.bind_tools(tool_list)


def build_graph(base_model=None, model=None):
    if base_model is None or model is None:
        base_model, model = create_model()

    # 1. Plan node
    def plan_node(state: MessageState):
        """Generate a structured plan to execute the user's request."""
        planner = base_model.with_structured_output(Plan)
        prompt = f"""
        You are a data analyst agent.

        Create an ordered plan to fulfill the user's request.

        User request: {state['user_request']} 
        Dataset path: {state['file_path']}

        Available tools:
      - inspect_data(file_path)
      - validate_dataset(file_path)
      - analyze_data(file_path, column)
      - modify_dataset(file_path, operation, output_path, column, value, new_column_name, operator)
      - generate_graph(file_path, chart_type, x_col, y_col, hue_col, column, title, xlabel, ylabel, bins, output_path)
      - generate_report(file_path, output_path)

        Rules:
        1. Return only steps needed for the request.
        2. Preserve the user's requested operation order.
        3. Use only the available tools and their supported operations.
        4. Include the required arguments for each operation.
        5. Do not invent column names; use names provided by the user or obtained from dataset inspection.
        6. Do not include file_path or output_path in the plan's arguments; the execution node will supply these.
        7. Use modify_dataset operations supported by the tool:
        drop_missing, remove_duplicates, fill_missing, rename_column, drop_column, filter_rows.
        """
        response = planner.invoke(prompt)
        return {
            "plan": [step.model_dump() for step in response.steps],
            "current_step": 0
        }

    # 2. Analyzer node
    def data_info(state: MessageState):
        result = inspect_data.invoke({
        "file_path": state["file_path"]
           })

        return {"dataset_info": result}

    # 3. Executor node
    def executor_node(state: MessageState):
        """Execute the current plan step."""

        step = state["plan"][state["current_step"]]

        prompt = f"""
        You are an execution agent for a data analyst system.

        User request: {state['user_request']}
        Dataset path: {state['file_path']}

        Current plan step:
        {step}

        Dataset analysis:
        {state.get('dataset_info', '')}

        Execute ONLY this plan step.
        Call the appropriate tool with the required arguments.
        Do not execute future steps.
        """

        messages = list(state.get("messages", []))

        if messages and getattr(messages[-1], "type", "") == "tool":
           response = model.invoke(messages)
        else:
           response = model.invoke([
           HumanMessage(content=prompt)
           ])

        return {"messages": [response]}
    # 4. Increment step
    def increment_step(state: MessageState):
        """Move to the next plan step and update dataset path if modified."""
        updates = {"current_step": state["current_step"] + 1}
        for msg in reversed(state.get("messages", [])):
            if getattr(msg, "type", "") == "tool":
                try:
                    data = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                    if isinstance(data, dict) and data.get("success") and data.get("output_path"):
                        if data["output_path"].endswith(".csv"):
                            updates["file_path"] = data["output_path"]
                            break
                except Exception:
                    pass
        return updates

    # 5. Conditional router
    def check_plan_status(state: MessageState):
        """Check whether all plan steps are completed."""
        if state["current_step"] < len(state["plan"]):
            return "data_info"
        return "summary_node"

    # Assemble Graph
    workflow = StateGraph(MessageState)

    workflow.add_node("plan_node", plan_node)
    workflow.add_node("analyzer_node", data_info)
    workflow.add_node("executor_node", executor_node)
    workflow.add_node("increment_node", increment_step)
    workflow.add_node("summary_node", summary_node)
    workflow.add_node("executor_tools", ToolNode(tool_list))

    # Edges
    workflow.add_edge(START, "plan_node")
    workflow.add_edge("plan_node", "analyzer_node")
    workflow.add_edge("analyzer_node", "executor_node")

    workflow.add_conditional_edges(
        "executor_node",
        tools_condition,
        {
            "tools": "executor_tools",
            END: "increment_node",
        },
    )
    workflow.add_edge("executor_tools", "executor_node")

    workflow.add_conditional_edges(
        "increment_node",
        check_plan_status,
        {
            "data_info": "analyzer_node",
            "summary_node": "summary_node",
        },
    )
    workflow.add_edge("summary_node", END)

    return workflow.compile()
