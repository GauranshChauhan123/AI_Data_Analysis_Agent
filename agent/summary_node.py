import json
import os
import pandas as pd
from langchain_core.messages import AIMessage
from agent.state import MessageState


def summary_node(state: MessageState) -> dict:
    """
    Final node of the LangGraph workflow.
    Compiles all workflow results, artifacts, files, and statistics
    into a structured dictionary designed for dashboard rendering,
    and returns a user-friendly summary AIMessage.
    """
    final_file = state.get("file_path", "")
    modifications = []
    charts = []
    reports = []
    analyses = []
    errors = list(state.get("errors", []))

    # Parse all tool outputs stored in messages
    for msg in state.get("messages", []):
        msg_type = getattr(msg, "type", "")
        if msg_type == "tool":
            content = msg.content
            try:
                data = json.loads(content) if isinstance(content, str) else content
            except Exception:
                continue

            if not isinstance(data, dict):
                continue

            # Record errors if any
            if "error" in data or data.get("success") is False:
                errors.append(str(data.get("error", "Unknown tool error")))

            # Modification operations
            if "operation" in data:
                modifications.append({
                    "operation": data.get("operation"),
                    "output_path": data.get("output_path", ""),
                    "original_rows": data.get("original_rows"),
                    "remaining_rows": data.get("remaining_rows"),
                    "removed_rows": data.get("removed_rows"),
                    "success": data.get("success", True)
                })

            # Chart generation
            elif "chart_type" in data or (isinstance(data.get("output_path"), str) and data["output_path"].lower().endswith((".png", ".jpg", ".jpeg", ".svg"))):
                charts.append({
                    "chart_type": data.get("chart_type", "chart"),
                    "output_path": data.get("output_path", ""),
                    "message": data.get("message", "")
                })

            # Text report generation
            elif "rows_analyzed" in data or (isinstance(data.get("output_path"), str) and data["output_path"].lower().endswith(".txt")):
                reports.append({
                    "output_path": data.get("output_path", ""),
                    "rows_analyzed": data.get("rows_analyzed"),
                    "columns_analyzed": data.get("columns_analyzed")
                })

            # Data column analysis
            elif "column" in data and ("mean" in data or "median" in data):
                analyses.append({
                    "column": data.get("column"),
                    "count": data.get("count"),
                    "mean": data.get("mean"),
                    "median": data.get("median"),
                    "min": data.get("min"),
                    "max": data.get("max"),
                    "sum": data.get("sum")
                })

    # Inspect the final CSV file if it exists
    dataset_overview = {}
    if final_file and os.path.isfile(final_file) and final_file.lower().endswith(".csv"):
        try:
            df = pd.read_csv(final_file)
            missing_dict = df.isnull().sum().to_dict()
            dataset_overview = {
                "file_path": os.path.abspath(final_file),
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": list(df.columns),
                "total_missing": int(df.isnull().sum().sum()),
                "missing_per_column": missing_dict
            }
        except Exception as e:
            dataset_overview = {
                "file_path": os.path.abspath(final_file),
                "error": str(e)
            }

    needs_clarification = state.get("needs_clarification", False)
    clarification_question = state.get("clarification_question", "")

    # Structured dictionary for dashboard UIs (Streamlit, React, Gradio, etc.)
    summary_data = {
        "final_file_path": os.path.abspath(final_file) if final_file else "",
        "is_modified": len(modifications) > 0,
        "needs_clarification": needs_clarification,
        "clarification_question": clarification_question,
        "dataset_overview": dataset_overview,
        "modifications": modifications,
        "charts": charts,
        "reports": reports,
        "analyses": analyses,
        "errors": errors,
        "total_steps_executed": len(state.get("plan", []))
    }

    # If clarification is needed, output the question directly to the user
    if needs_clarification and clarification_question:
        summary_message = f"### Clarification Needed\n\n{clarification_question}"
        return {
            "summary": summary_data,
            "output_path": os.path.abspath(final_file) if final_file else "",
            "clarification_question": clarification_question,
            "needs_clarification": True,
            "messages": [AIMessage(content=summary_message)]
        }

    # Generate a human-readable markdown message for the user/chat interface
    md_lines = ["### 📊 Workflow Execution Summary\n"]

    if final_file:
        md_lines.append(f"**Final Dataset:**\n- **Saved Location:** `{os.path.abspath(final_file)}`")
        if dataset_overview and "rows" in dataset_overview:
            md_lines.append(
                f"- **Dimensions:** {dataset_overview['rows']} rows × {dataset_overview['columns']} columns\n"
                f"- **Remaining Missing Values:** {dataset_overview['total_missing']}"
            )
        md_lines.append("")


    if modifications:
        md_lines.append("**Applied Modifications:**")
        for idx, mod in enumerate(modifications, 1):
            op = mod.get("operation", "modify")
            out = mod.get("output_path", "")
            rem = mod.get("remaining_rows", "N/A")
            md_lines.append(f"- Step {idx}: `{op}` → Remaining rows: {rem} (Saved: `{out}`)")
        md_lines.append("")

    if charts:
        md_lines.append("**Generated Charts:**")
        for chart in charts:
            ctype = chart.get("chart_type", "chart").title()
            cpath = chart.get("output_path", "")
            md_lines.append(f"- 📈 **{ctype}**: `{cpath}`")
        md_lines.append("")

    if reports:
        md_lines.append("**Generated Reports:**")
        for rep in reports:
            rpath = rep.get("output_path", "")
            md_lines.append(f"- 📄 `{rpath}`")
        md_lines.append("")

    if analyses:
        md_lines.append("**Summary Statistics:**")
        for ana in analyses:
            col = ana.get("column", "")
            mean_val = ana.get("mean")
            med_val = ana.get("median")
            md_lines.append(f"- Column `{col}`: Mean = {mean_val:.2f}, Median = {med_val:.2f}, Min = {ana.get('min')}, Max = {ana.get('max')}")
        md_lines.append("")

    if errors:
        md_lines.append("**Warnings / Errors Encountered:**")
        for err in errors:
            md_lines.append(f"- ⚠️ {err}")
        md_lines.append("")

    summary_message = "\n".join(md_lines).strip()

    return {
        "summary": summary_data,
        "output_path": os.path.abspath(final_file) if final_file else "",
        "messages": [AIMessage(content=summary_message)]
    }
