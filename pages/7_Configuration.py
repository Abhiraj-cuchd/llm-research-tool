import os
import streamlit as st
import yaml
import io
import copy

from utils.validators import Codebook, DimensionConfig, LLMConfig

st.title("Configuration")

if os.getenv("DEV_MODE", "").lower() not in ("1", "true", "yes"):
    st.error("This page is only available in development mode.")
    st.stop()

codebook = st.session_state.get("codebook")
llm_config = st.session_state.get("llm_config")

if codebook is None or llm_config is None:
    st.warning("Configuration not yet loaded. Please reload the app.")
    st.stop()

st.header("Codebook")

st.subheader("Scoring Scale")
new_scale = st.radio(
    "Scoring scale",
    options=[5, 10, 100],
    index=[5, 10, 100].index(codebook.scale),
    horizontal=True,
)

st.subheader("Dimensions")

edited_dims = []
for i, dim in enumerate(codebook.dimensions):
    with st.container(border=True):
        cols = st.columns([3, 1, 6])
        with cols[0]:
            new_label = st.text_input(f"Label", value=dim.label, key=f"dim_label_{i}")
        with cols[1]:
            new_weight = st.slider(
                f"Weight",
                min_value=0,
                max_value=100,
                value=int(dim.weight),
                key=f"dim_weight_{i}",
            )
        new_desc = st.text_area(
            f"Description",
            value=dim.description,
            key=f"dim_desc_{i}",
            height=80,
        )
        edited_dims.append(DimensionConfig(
            id=dim.id,
            label=new_label,
            weight=float(new_weight),
            description=new_desc,
        ))

st.subheader("Prompt Template")
new_template = st.text_area(
    "Prompt template",
    value=codebook.prompt_template,
    height=250,
    key="prompt_template",
)

st.header("LLM Configuration")
col1, col2, col3 = st.columns(3)
with col1:
    new_api_key = st.text_input("API Key", value=llm_config.api_key, type="password", key="config_api_key")
with col2:
    new_base_url = st.text_input("Base URL", value=llm_config.base_url, key="config_base_url")
with col3:
    new_model = st.text_input("Model", value=llm_config.model, key="config_model")

st.divider()

st.warning("⚠️ Changing configuration will clear existing analysis results.")

confirm = st.checkbox("I understand — clear existing results and apply new configuration")

if st.button("Save Configuration", type="primary"):
    if confirm:
        new_codebook = Codebook(
            version=codebook.version,
            scale=new_scale,
            dimensions=edited_dims,
            prompt_template=new_template,
        )
        st.session_state["codebook"] = new_codebook

        st.session_state["llm_config"] = LLMConfig(
            api_key=new_api_key,
            base_url=new_base_url,
            model=new_model,
        )

        for key in ["coding_results", "scores", "run_metadata"]:
            st.session_state[key] = {}

        st.success("Configuration saved and results cleared.")
        st.rerun()

st.divider()

st.subheader("Export / Import Configuration")

yaml_str = yaml.dump(
    codebook.model_dump(),
    default_flow_style=False,
    allow_unicode=True,
    sort_keys=False,
)
st.download_button(
    "Export Config as YAML",
    data=yaml_str,
    file_name="codebook_export.yaml",
    mime="text/yaml",
)

uploaded_config = st.file_uploader("Import Config from YAML", type=["yaml", "yml"], key="config_import")
if uploaded_config is not None:
    try:
        raw = yaml.safe_load(uploaded_config.read())
        imported = Codebook(**raw)
        st.session_state["codebook"] = imported
        st.success("Configuration imported successfully. Reloading...")
        st.rerun()
    except Exception as e:
        st.error(f"Invalid configuration file: {e}")
