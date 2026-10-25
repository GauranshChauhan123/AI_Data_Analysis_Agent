import os
import pandas as pd
import streamlit as st
from utils import render_sidebar

st.set_page_config(page_title="Data Preview", page_icon="🔎", layout="wide")
render_sidebar()

st.title("🔎 Data Preview")

if "preview" not in st.session_state and "edited_file_path" not in st.session_state:
    st.info("Upload a CSV using the sidebar first.")
else:
    edited_path = st.session_state.get("edited_file_path")
    has_edited = bool(edited_path and os.path.isfile(edited_path))

    version = "Original Uploaded Dataset"
    if has_edited:
        version = st.radio(
            "Select dataset version to preview:",
            ["Original Uploaded Dataset", f"AI-Edited Dataset ({os.path.basename(edited_path)})"],
            horizontal=True
        )

    if version.startswith("AI-Edited") and has_edited:
        df = pd.read_csv(edited_path)
        col1, col2, col3 = st.columns([1, 1, 2])
        col1.metric("Rows", len(df))
        col2.metric("Columns", len(df.columns))
        with col3:
            with open(edited_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download This Edited CSV",
                    data=f.read(),
                    file_name=os.path.basename(edited_path),
                    mime="text/csv",
                    use_container_width=True,
                )

        st.subheader("Dataset Records")
        st.dataframe(df.head(50), use_container_width=True, hide_index=True)

        st.subheader("Column Data Types")
        types_df = pd.DataFrame(
            [{"Column Name": col, "Data Type": str(dtype)} for col, dtype in df.dtypes.items()]
        )
        st.dataframe(types_df, use_container_width=True, hide_index=True)

    else:
        df = pd.DataFrame(st.session_state.get("preview", []))

        col1, col2 = st.columns(2)
        col1.metric("Preview Rows", len(df))
        col2.metric("Columns", len(df.columns))

        st.subheader("Dataset Records")
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.subheader("Column Data Types")
        types_df = pd.DataFrame(
            list(st.session_state.get("column_types", {}).items()),
            columns=["Column Name", "Data Type"],
        )
        st.dataframe(types_df, use_container_width=True, hide_index=True)

