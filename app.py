import streamlit as st
from dotenv import load_dotenv
import pathlib
import os

from utils.state import init_session_state, get_state
from utils.auth import require_auth
from modules.config_loader import load_codebook, ConfigError
from utils.validators import LLMConfig

load_dotenv()
pathlib.Path("data/failed").mkdir(parents=True, exist_ok=True)


def get_secret(key: str) -> str:
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, "")


st.set_page_config(page_title="Research Tool", page_icon="📊", layout="wide")

require_auth()
init_session_state()

if st.session_state.get("codebook") is None:
    try:
        st.session_state["codebook"] = load_codebook("config/default_codebook.yaml")
    except ConfigError as e:
        st.error(f"Failed to load codebook: {e}")
        st.stop()

if not st.session_state.get("llm_config"):
    try:
        st.session_state["llm_config"] = LLMConfig(
            api_key=get_secret("DEEPSEEK_API_KEY"),
            base_url=get_secret("DEEPSEEK_BASE_URL") or "https://api.deepseek.com",
            model=get_secret("DEEPSEEK_MODEL") or "deepseek-chat",
        )
    except Exception:
        st.session_state["llm_config"] = None

st.switch_page("pages/1_Upload.py")
