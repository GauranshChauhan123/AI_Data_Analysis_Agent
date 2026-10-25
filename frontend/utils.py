
import os
import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"


def render_sidebar():
    with st.sidebar:
        st.title("📊 Data Analyst")
        st.caption("AI-powered data workspace")
        st.divider()

        uploaded_file = st.file_uploader(
            "Upload CSV",
            type=["csv"],
            key="dataset_uploader",
        )

        if uploaded_file and st.button(
            "Upload Dataset",
            use_container_width=True,
        ):
            try:
                with st.spinner("Uploading dataset..."):
                    response = requests.post(
                        f"{API_URL}/upload",
                        files={
                            "file": (
                                uploaded_file.name,
                                uploaded_file.getvalue(),
                                "text/csv",
                            )
                        },
                        timeout=60,
                    )

                if response.ok:
                    result = response.json()
                    st.session_state.file_id = result["file_id"]
                    st.session_state.preview = result["preview"]
                    st.session_state.column_types = result["column_types"]
                    st.session_state.pop("dataset_summary", None)
                    st.session_state.pop("analysis_result", None)
                    st.session_state.pop("edited_file_path", None)
                    st.session_state.pop("artifacts_cache", None)
                    st.success("Dataset uploaded successfully!")
                else:
                    st.error(response.text)

            except requests.RequestException as exc:
                st.error(f"Backend connection failed: {exc}")

        if "file_id" in st.session_state:
            st.divider()
            st.success("🟢 Active Dataset")
            edited = st.session_state.get("edited_file_path")
            if edited and os.path.isfile(edited):
                st.markdown(f"**Current Working:** `{os.path.basename(edited)}` ✍️ *(AI Edited)*")
                st.caption(f"Original: `{st.session_state.file_id}`")
            else:
                st.markdown(f"**Current:** `{st.session_state.file_id}`")
        else:
            st.info("Upload a dataset to get started.")

