
import requests
import pandas as pd
import streamlit as st
from utils import API_URL, render_sidebar

st.set_page_config(page_title="Dataset Summary", page_icon="📊", layout="wide")
render_sidebar()

st.title("📊 Dataset Summary")

if "file_id" not in st.session_state:
    st.info("Upload a CSV using the sidebar first.")
else:
    if st.button("Generate Summary", use_container_width=True):
        try:
            with st.spinner("Generating summary..."):
                response = requests.get(
                    f"{API_URL}/summary/{st.session_state.file_id}",
                    timeout=60,
                )

            if response.ok:
                st.session_state.dataset_summary = response.json()
            else:
                st.error(response.text)
        except requests.RequestException as exc:
            st.error(f"Backend connection failed: {exc}")

    summary = st.session_state.get("dataset_summary")

    if summary:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Rows", f"{summary['total_rows']:,}")
        col2.metric("Total Columns", f"{summary['total_columns']:,}")
        col3.metric("Missing Values", f"{summary['total_missing_values']:,}")

        columns_df = pd.DataFrame(summary["columns"]).rename(
            columns={
                "name": "Column Name",
                "type": "Data Type",
                "missing_values": "Missing Values",
            }
        )

        st.subheader("Column Information")
        st.dataframe(columns_df, use_container_width=True, hide_index=True)

        missing_df = columns_df[columns_df["Missing Values"] > 0]
        with st.expander("Columns with Missing Values"):
            if missing_df.empty:
                st.success("No missing values found.")
            else:
                st.dataframe(missing_df, use_container_width=True, hide_index=True)
