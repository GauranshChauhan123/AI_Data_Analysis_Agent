
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
            "- Analyze a column\n"
            "- Fill missing values\n"
            "- Generate a chart\n"
            "- Create a report"
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
                    st.session_state.analysis_result = response.json()
                    st.success("Analysis completed!")
                else:
                    st.error(response.text)

            except requests.RequestException as exc:
                st.error(f"Backend connection failed: {exc}")

    if "analysis_result" in st.session_state:
        st.subheader("Analysis Results")
        st.json(st.session_state.analysis_result)
