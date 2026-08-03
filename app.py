import streamlit as st

from utils.auth import require_auth
from utils.state import bootstrap_session

st.set_page_config(page_title="Research Tool", page_icon="📊", layout="wide")

require_auth()
bootstrap_session()

st.switch_page("pages/1_Upload.py")
