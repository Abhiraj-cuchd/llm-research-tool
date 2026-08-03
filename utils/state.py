import streamlit as st


def init_session_state():
    defaults = {
        "transcripts": {},
        "coding_results": {},
        "scores": {},
        "codebook": None,
        "llm_config": {},
        "run_metadata": {},
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def get_state(key, default=None):
    return st.session_state.get(key, default)
