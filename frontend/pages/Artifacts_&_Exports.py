import os
import requests
import pandas as pd
import streamlit as st
from utils import API_URL, render_sidebar

st.set_page_config(
    page_title="Artifacts & Exports",
    page_icon="📁",
    layout="wide"
)

render_sidebar()

st.title("📁 Artifacts & Export Center")
st.write("Browse, preview, and download all charts, cleaned/modified datasets, and reports produced during your analysis.")

col_head1, col_head2 = st.columns([4, 1])
with col_head2:
    if st.button("🔄 Refresh Artifacts", use_container_width=True):
        st.session_state.pop("artifacts_cache", None)

# Fetch artifacts from backend API
artifacts = []
try:
    if "artifacts_cache" not in st.session_state:
        response = requests.get(f"{API_URL}/artifacts", timeout=15)
        if response.ok:
            artifacts = response.json().get("artifacts", [])
            st.session_state.artifacts_cache = artifacts
        else:
            artifacts = []
    else:
        artifacts = st.session_state.artifacts_cache
except Exception as e:
    st.warning(f"Could not connect to backend artifacts API: {e}")
    artifacts = []

if not artifacts:
    st.info("No generated files found yet. Run an analysis on the AI Analysis page to create charts, modified datasets, or reports!")
else:
    # Separate into categories
    charts = [a for a in artifacts if a["category"] == "chart"]
    datasets = [a for a in artifacts if a["category"] == "dataset"]
    reports = [a for a in artifacts if a["category"] == "report"]

    tab_charts, tab_datasets, tab_reports, tab_all = st.tabs([
        f"📈 Charts & Graphs ({len(charts)})",
        f"📝 Datasets & CSVs ({len(datasets)})",
        f"📄 Text Reports ({len(reports)})",
        f"🗂️ All Files ({len(artifacts)})",
    ])

    # 1. Charts Tab
    with tab_charts:
        if not charts:
            st.info("No charts generated yet.")
        else:
            cols = st.columns(2)
            for idx, c in enumerate(charts):
                c_col = cols[idx % 2]
                with c_col:
                    st.markdown(f"#### 📊 `{c['filename']}`")
                    c_path = c["path"]
                    if os.path.isfile(c_path):
                        st.image(c_path, use_container_width=True)
                        with open(c_path, "rb") as f:
                            st.download_button(
                                label=f"⬇️ Download {c['filename']}",
                                data=f.read(),
                                file_name=c["filename"],
                                mime="image/png",
                                key=f"art_chart_{idx}",
                                use_container_width=True,
                            )
                    else:
                        st.caption(f"Path: `{c_path}`")
                    st.divider()

    # 2. Datasets Tab (Show only the latest dataset being worked on)
    with tab_datasets:
        latest_edited = st.session_state.get("edited_file_path")
        original_file_id = st.session_state.get("file_id")

        if not latest_edited and not original_file_id:
            st.info("No active dataset. Upload a CSV to get started.")
        else:
            if latest_edited and os.path.isfile(latest_edited):
                st.markdown(f"### 🌟 Latest Working Dataset: `{os.path.basename(latest_edited)}`")
                st.caption("This is the most recent version containing all AI cleanings and modifications.")
                try:
                    df_latest = pd.read_csv(latest_edited)
                    col1, col2, col3 = st.columns([1, 1, 2])
                    col1.metric("Rows", f"{len(df_latest):,}")
                    col2.metric("Columns", f"{len(df_latest.columns):,}")
                    with col3:
                        with open(latest_edited, "rb") as f:
                            st.download_button(
                                label="⬇️ Download Latest Edited CSV",
                                data=f.read(),
                                file_name=os.path.basename(latest_edited),
                                mime="text/csv",
                                key="dl_latest_active_csv",
                            )
                    st.dataframe(df_latest.head(25), hide_index=True)
                except Exception as exc:
                    st.error(f"Could not load latest edited dataset: {exc}")

                st.divider()

            if original_file_id:
                orig_path = os.path.join("data", "uploads", original_file_id)
                st.markdown(f"#### 📄 Original Upload: `{original_file_id}`")
                if os.path.isfile(orig_path):
                    try:
                        df_orig = pd.read_csv(orig_path)
                        st.caption(f"Original unedited file: {len(df_orig):,} rows × {len(df_orig.columns):,} columns")
                        with open(orig_path, "rb") as f:
                            st.download_button(
                                label=f"⬇️ Download Original ({original_file_id})",
                                data=f.read(),
                                file_name=original_file_id,
                                mime="text/csv",
                                key="dl_original_csv",
                            )
                    except Exception as exc:
                        st.error(f"Could not load original dataset: {exc}")


    # 3. Reports Tab
    with tab_reports:
        if not reports:
            st.info("No reports generated yet.")
        else:
            for idx, r in enumerate(reports):
                r_path = r["path"]
                st.markdown(f"#### 📄 `{r['filename']}`")
                if os.path.isfile(r_path):
                    try:
                        with open(r_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        with st.expander("Preview Report", expanded=True):
                            st.text(content)
                        with open(r_path, "rb") as f:
                            st.download_button(
                                label=f"⬇️ Download {r['filename']}",
                                data=f.read(),
                                file_name=r["filename"],
                                mime="text/plain",
                                key=f"art_rep_{idx}",
                            )
                    except Exception as exc:
                        st.error(f"Could not read report file: {exc}")
                st.divider()

    # 4. All Files Catalog Tab
    with tab_all:
        table_data = []
        for a in artifacts:
            table_data.append({
                "Filename": a["filename"],
                "Category": a["category"].title(),
                "Size (KB)": round(a["size_bytes"] / 1024, 2),
                "Location": a["path"]
            })
        st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)
