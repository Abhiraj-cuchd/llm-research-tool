import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def _get_secret(key: str) -> str:
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, "")


def init_session_state():
    defaults = {
        "transcripts": {},
        "coding_results": {},
        "scores": {},
        "codebook": None,
        "llm_config": None,
        "run_metadata": {},
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def bootstrap_session():
    """Initialize codebook and llm_config from secrets/env if not already set.
    Call at the top of every page so direct navigation works correctly.
    """
    import pathlib
    pathlib.Path("data/failed").mkdir(parents=True, exist_ok=True)

    init_session_state()

    if st.session_state.get("codebook") is None:
        try:
            from modules.config_loader import load_codebook, ConfigError
            st.session_state["codebook"] = load_codebook("config/default_codebook.yaml")
        except Exception as e:
            st.error(f"Failed to load codebook: {e}")
            st.stop()

    if not st.session_state.get("llm_config"):
        try:
            from utils.validators import LLMConfig
            st.session_state["llm_config"] = LLMConfig(
                api_key=_get_secret("DEEPSEEK_API_KEY"),
                base_url=_get_secret("DEEPSEEK_BASE_URL") or "https://api.deepseek.com",
                model=_get_secret("DEEPSEEK_MODEL") or "deepseek-chat",
            )
        except Exception:
            st.session_state["llm_config"] = None


def get_state(key, default=None):
    return st.session_state.get(key, default)
