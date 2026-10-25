import os
import json
from pathlib import Path
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

    # 1. Analyzer node (Runs first so planner has dataset context)
    def data_info(state: MessageState):
        result = inspect_data.invoke({
            "file_path": state["file_path"]
        })
        return {"dataset_info": result}

    # 2. Plan node
    def plan_node(state: MessageState):
        """Generate a structured plan or request clarification from the user."""
        planner = base_model.with_structured_output(Plan)
        
        dataset_info_str = json.dumps(state.get("dataset_info", {}), default=str)
        prompt = f"""
        You are a data analyst agent.

        User request: {state['user_request']} 
        Dataset path: {state['file_path']}
        Dataset structure & columns:
        {dataset_info_str}

        Available tools:
        - inspect_data(file_path)
        - validate_dataset(file_path)
        - analyze_data(file_path, column)
        - modify_dataset(file_path, operation, output_path, column, value, new_column_name, operator)
        - generate_graph(file_path, chart_type, x_col, y_col, hue_col, column, title, xlabel, ylabel, bins, output_path)
        - generate_report(file_path, output_path)

        Instructions:
        1. If the user request is ambiguous, lacks required parameters (such as which column to analyze/plot, which operation or value to use), or cannot be answered with this dataset:
           - Set needs_clarification = True
           - Formulate a clear, friendly clarification_question asking the user for the specific missing information.
           - Leave steps empty.
        2. If sufficient information is provided:
           - Set needs_clarification = False
           - Set clarification_question = ""
           - Create the ordered steps needed to fulfill the request.
        3. Do not invent non-existent column names; use only valid columns found in the dataset structure.
        4. Supported modify_dataset operations:
           drop_missing, remove_duplicates, fill_missing, rename_column, drop_column, filter_rows.
        """
        response = planner.invoke(prompt)
        return {
            "plan": [step.model_dump() for step in response.steps],
            "needs_clarification": response.needs_clarification,
            "clarification_question": response.clarification_question,
            "current_step": 0
        }

    # Router after plan node
    def route_after_plan(state: MessageState):
        if state.get("needs_clarification") or not state.get("plan"):
            return "summary_node"
        return "executor_node"

    # 3. Executor node
    def executor_node(state: MessageState):
        """Execute the current plan step while ensuring proper message turns."""
        plan = state.get("plan", [])
        current_step = state.get("current_step", 0)

        if current_step >= len(plan):
            return {}

        step = plan[current_step]
        base_name = Path(state['file_path']).stem
        base_name = base_name.replace("_cleaned", "").replace("_modified", "").replace("_filtered", "")

        prompt = f"""
        You are an execution agent for a data analyst system.

        User request: {state['user_request']}
        Dataset path: {state['file_path']}
        Dataset base name: {base_name}

        Current plan step:
        {step}

        Dataset analysis:
        {state.get('dataset_info', '')}

        Execute ONLY this plan step.
        Call the appropriate tool with the required arguments.
        Make sure to provide output_path for tools that require saving files.
        Always save generated files into the 'data/outputs/' directory using clear, descriptive names:
        - For modified CSV: 'data/outputs/{base_name}_cleaned.csv'
        - For charts/graphs: 'data/outputs/{base_name}_chart.png'
        - For text reports: 'data/outputs/{base_name}_report.txt'
        Do not use random IDs or hex strings. Use human-readable names.
        Do not execute future steps.
        """

        messages = list(state.get("messages", []))

        if messages and getattr(messages[-1], "type", "") == "tool":
            response = model.invoke(messages)
            return {"messages": [response]}
        else:
            human_msg = HumanMessage(content=prompt)
            response = model.invoke(messages + [human_msg])
            return {"messages": [human_msg, response]}

    # 4. Increment step
    def increment_step(state: MessageState):
        """Move to the next plan step and update dataset path if modified."""
        updates = {"current_step": state["current_step"] + 1}
        for msg in reversed(state.get("messages", [])):
            if getattr(msg, "type", "") == "tool":
                try:
                    data = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                    if isinstance(data, dict) and data.get("success") and data.get("output_path"):
                        if str(data["output_path"]).lower().endswith(".csv"):
                            updates["file_path"] = data["output_path"]
                            break
                except Exception:
                    pass
        return updates

    # 5. Conditional router after step increment
    def check_plan_status(state: MessageState):
        """Check whether all plan steps are completed."""
        if state["current_step"] < len(state.get("plan", [])):
            return "data_info"
        return "summary_node"

    # Assemble Graph
    workflow = StateGraph(MessageState)

    workflow.add_node("analyzer_node", data_info)
    workflow.add_node("plan_node", plan_node)
    workflow.add_node("executor_node", executor_node)
    workflow.add_node("increment_node", increment_step)
    workflow.add_node("summary_node", summary_node)
    workflow.add_node("executor_tools", ToolNode(tool_list))

    # Edges: START -> analyzer_node -> plan_node
    workflow.add_edge(START, "analyzer_node")
    workflow.add_edge("analyzer_node", "plan_node")

    workflow.add_conditional_edges(
        "plan_node",
        route_after_plan,
        {
            "executor_node": "executor_node",
            "summary_node": "summary_node",
        },
    )

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

