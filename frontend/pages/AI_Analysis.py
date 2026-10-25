import os
import pandas as pd
import requests
import streamlit as st
from utils import API_URL, render_sidebar

st.set_page_config(page_title="AI Analysis", page_icon="🤖", layout="wide")
render_sidebar()

st.title("🤖 AI Data Analysis")
st.write("Describe what you want the agent to do with your dataset.")

if "file_id" not in st.session_state:
    st.info("Upload a CSV using the sidebar first.")
else:
    user_request = st.text_area(
        "Your request",
        placeholder=(
            "Examples:\n"
            "- Analyze descriptive statistics for mark column\n"
            "- Fill missing values with mean\n"
            "- Generate a bar chart of class vs mark\n"
            "- Create a full analysis report"
        ),
        height=140,
    )

    if st.button("▶ Run Analysis", use_container_width=True):
        if not user_request.strip():
            st.warning("Please enter a request.")
        else:
            try:
                with st.spinner("Agent is analyzing your dataset..."):
                    response = requests.post(
                        f"{API_URL}/analyze",
                        json={
                            "file_id": st.session_state.file_id,
                            "user_request": user_request,
                        },
                        timeout=300,
                    )

                if response.ok:
                    res_data = response.json()
                    st.session_state.analysis_result = res_data
                    if res_data.get("needs_clarification"):
                        st.warning("⚠️ Clarification Needed")
                    else:
                        st.success("Analysis completed!")
                        summary = res_data.get("summary", {})
                        if summary.get("is_modified") and summary.get("final_file_path"):
                            st.session_state.edited_file_path = summary.get("final_file_path")
                else:
                    st.error(response.text)

            except requests.RequestException as exc:
                st.error(f"Backend connection failed: {exc}")

    if "analysis_result" in st.session_state:
        res = st.session_state.analysis_result
        if res.get("needs_clarification"):
            st.subheader("❓ Clarification Needed")
            st.info(res.get("clarification_question", "Please provide more details in your request."))
        else:
            if res.get("message"):
                st.markdown(res["message"])

            summary = res.get("summary", {})

            # 1. Show Edited Dataset if AI modified the file
            if summary.get("is_modified") or summary.get("modifications"):
                st.divider()
                st.subheader("📝 Edited / Cleaned Dataset")
                final_path = summary.get("final_file_path") or res.get("output_path")
                if final_path and os.path.isfile(final_path):
                    try:
                        edited_df = pd.read_csv(final_path)
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.caption(f"📁 **File:** `{os.path.basename(final_path)}` | **Rows:** {len(edited_df)} | **Columns:** {len(edited_df.columns)}")
                        with col2:
                            with open(final_path, "rb") as f:
                                st.download_button(
                                    label="⬇️ Download Edited CSV",
                                    data=f.read(),
                                    file_name=os.path.basename(final_path),
                                    mime="text/csv",
                                    key="dl_edited_csv_direct",
                                    use_container_width=True,
                                )
                        st.dataframe(edited_df.head(25), use_container_width=True)
                    except Exception as err:
                        st.error(f"Could not load edited dataset preview: {err}")

            # 2. Show Generated Charts
            charts = summary.get("charts", [])
            if charts:
                st.divider()
                st.subheader("📈 Generated Charts & Graphs")
                chart_cols = st.columns(min(len(charts), 2) if len(charts) > 1 else 1)
                for idx, chart in enumerate(charts):
                    cpath = chart.get("output_path", "")
                    col = chart_cols[idx % len(chart_cols)]
                    with col:
                        if cpath and os.path.isfile(cpath):
                            st.image(cpath, caption=chart.get("chart_type", "Chart").title(), use_container_width=True)
                            with open(cpath, "rb") as f:
                                st.download_button(
                                    label=f"⬇️ Download {os.path.basename(cpath)}",
                                    data=f.read(),
                                    file_name=os.path.basename(cpath),
                                    mime="image/png",
                                    key=f"dl_chart_{idx}",
                                    use_container_width=True,
                                )
                        else:
                            st.info(f"Chart saved at: `{cpath}`")

            # 3. Show Generated Reports
            reports = summary.get("reports", [])
            if reports:
                st.divider()
                st.subheader("📄 Generated Text Reports")
                for idx, rep in enumerate(reports):
                    rpath = rep.get("output_path", "")
                    if rpath and os.path.isfile(rpath):
                        with open(rpath, "r", encoding="utf-8") as f:
                            report_text = f.read()
                        with st.expander(f"📑 View Report: {os.path.basename(rpath)}", expanded=True):
                            st.text(report_text)
                        with open(rpath, "rb") as f:
                            st.download_button(
                                label=f"⬇️ Download {os.path.basename(rpath)}",
                                data=f.read(),
                                file_name=os.path.basename(rpath),
                                mime="text/plain",
                                key=f"dl_rep_{idx}",
                            )

            with st.expander("🔍 View Raw Execution Data", expanded=False):
                st.json(res)


