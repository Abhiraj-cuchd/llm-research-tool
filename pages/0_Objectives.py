import streamlit as st

from utils.validators import Codebook, DimensionConfig
from utils.auth import require_auth
from utils.state import bootstrap_session
from modules.rule_generator import extract_objectives, generate_codebook, CodebookGenerationError

require_auth()
bootstrap_session()

st.title("Research Objectives & Rule")

st.markdown(
    "Upload your research objectives (e.g. a dissertation or proposal document). "
    "The LLM will derive a coding rule (codebook) from those objectives, which you "
    "can review and edit before analysing transcripts."
)

llm_config = st.session_state.get("llm_config")

st.subheader("1. Upload Objectives")
uploaded = st.file_uploader(
    "Objectives document",
    type=["docx", "txt", "md"],
    key="objectives_uploader",
)

if uploaded is not None:
    try:
        if uploaded.name.lower().endswith(".docx"):
            text = extract_objectives(uploaded.read())
        else:
            text = uploaded.read().decode("utf-8")
        st.session_state["objectives"] = text
    except CodebookGenerationError as e:
        st.error(str(e))
    except Exception as e:
        st.error(f"Failed to read objectives document: {e}")

objectives = st.text_area(
    "Objectives (editable)",
    value=st.session_state.get("objectives", ""),
    height=220,
    key="objectives_text",
)

if objectives and objectives != st.session_state.get("objectives"):
    st.session_state["objectives"] = objectives

st.subheader("2. Generate Rule")

if not objectives.strip():
    st.info("Paste or upload objectives above, then generate a rule.")
elif not llm_config or not llm_config.api_key:
    st.error("LLM not configured. Please set API credentials in Configuration.")
else:
    gen_scale = st.radio(
        "Scoring scale for generated dimensions",
        options=[5, 10, 100],
        index=0,
        horizontal=True,
        key="gen_scale",
    )
    if st.button("Generate Codebook from Objectives", type="primary"):
        with st.spinner("Generating codebook from objectives..."):
            try:
                generated = generate_codebook(objectives, llm_config, scale=gen_scale)
                st.session_state["codebook"] = generated
                st.session_state["codebook_source"] = "generated"
                st.success("Codebook generated. Review it below.")
                st.rerun()
            except CodebookGenerationError as e:
                st.error(str(e))

st.divider()

st.subheader("3. Review & Continue")

codebook = st.session_state.get("codebook")
if codebook is None:
    st.warning("No codebook loaded yet.")
else:
    new_scale = st.radio(
        "Scoring scale",
        options=[5, 10, 100],
        index=[5, 10, 100].index(codebook.scale),
        horizontal=True,
        key="review_scale",
    )

    edited_dims = []
    for i, dim in enumerate(codebook.dimensions):
        with st.container(border=True):
            cols = st.columns([3, 1, 6])
            with cols[0]:
                new_label = st.text_input("Label", value=dim.label, key=f"obj_dim_label_{i}")
            with cols[1]:
                new_weight = st.slider(
                    "Weight",
                    min_value=0,
                    max_value=100,
                    value=int(dim.weight),
                    key=f"obj_dim_weight_{i}",
                )
            new_desc = st.text_area(
                "Description",
                value=dim.description,
                key=f"obj_dim_desc_{i}",
                height=80,
            )
            edited_dims.append(DimensionConfig(
                id=dim.id,
                label=new_label,
                weight=float(new_weight),
                description=new_desc,
            ))

    col_save, col_default = st.columns([1, 1])
    with col_save:
        if st.button("Save Codebook & Continue", type="primary", use_container_width=True):
            new_codebook = Codebook(
                version=codebook.version,
                scale=new_scale,
                dimensions=edited_dims,
                prompt_template=codebook.prompt_template,
            )
            st.session_state["codebook"] = new_codebook
            for key in ["coding_results", "scores", "run_metadata"]:
                st.session_state[key] = {}
            st.switch_page("pages/1_Upload.py")
    with col_default:
        if st.button("Continue with default codebook", type="secondary", use_container_width=True):
            from modules.config_loader import load_codebook
            st.session_state["codebook"] = load_codebook("config/default_codebook.yaml")
            st.session_state["codebook_source"] = "default"
            st.switch_page("pages/1_Upload.py")
