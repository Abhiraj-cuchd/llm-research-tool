import os
import streamlit as st


def _get_secret(key: str) -> str:
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, "")


def require_auth() -> None:
    """Call at the top of every page. Shows a password gate if APP_PASSWORD is set."""
    password = _get_secret("APP_PASSWORD")
    if not password:
        return  # No password configured — open access (local dev)

    if st.session_state.get("_authenticated"):
        return  # Already authenticated this session

    st.title("Research Tool")
    pwd = st.text_input("Password", type="password", key="_login_pwd")
    if st.button("Sign in", type="primary"):
        if pwd == password:
            st.session_state["_authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()
