
import streamlit as st
from utils import render_sidebar

st.set_page_config(
    page_title="Data Analyst Agent",
    page_icon="📊",
    layout="wide",
)

render_sidebar()

st.title("📊 Data Analyst Workspace")
st.write("Welcome! Explore and analyze your data in one place.")

if "file_id" in st.session_state:
    st.success("Your dataset is ready.")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("### 🔎 Data Preview")
        st.write("Explore raw & edited rows and column types.")

    with col2:
        st.markdown("### 📈 Dataset Summary")
        st.write("Review dimensions and missing values.")

    with col3:
        st.markdown("### 🤖 AI Analysis")
        st.write("Run agent analysis, modify data & create charts.")

    with col4:
        st.markdown("### 📁 Artifacts & Exports")
        st.write("View & download charts, edited CSVs & reports.")
else:
    st.info("Upload a CSV using the sidebar to begin.")

st.markdown("---")
st.caption("Use the navigation menu to switch between pages.")
