
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

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 🔎 Data Preview")
        st.write("Explore rows and column types.")

    with col2:
        st.markdown("### 📈 Dataset Summary")
        st.write("Review dimensions and missing values.")

    with col3:
        st.markdown("### 🤖 AI Analysis")
        st.write("Run analysis and generate reports.")
else:
    st.info("Upload a CSV using the sidebar to begin.")

st.markdown("---")
st.caption("Use the navigation menu to switch between pages.")
