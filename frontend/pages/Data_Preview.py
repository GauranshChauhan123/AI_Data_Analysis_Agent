
import streamlit as st
import pandas as pd
from utils import render_sidebar

st.set_page_config(page_title="Data Preview", page_icon="🔎", layout="wide")
render_sidebar()

st.title("🔎 Data Preview")

if "preview" not in st.session_state:
    st.info("Upload a CSV using the sidebar first.")
else:
    df = pd.DataFrame(st.session_state.preview)

    col1, col2 = st.columns(2)
    col1.metric("Preview Rows", len(df))
    col2.metric("Columns", len(df.columns))

    st.subheader("Dataset Records")
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.subheader("Column Data Types")
    types_df = pd.DataFrame(
        list(st.session_state.column_types.items()),
        columns=["Column Name", "Data Type"],
    )
    st.dataframe(types_df, use_container_width=True, hide_index=True)
