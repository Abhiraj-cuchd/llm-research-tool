import streamlit as st

from utils.auth import require_auth
from utils.state import bootstrap_session
from modules.analytics import radar_chart

require_auth()
bootstrap_session()
from modules.scorer import compute_scores

st.title("Participant View")

if not st.session_state.get("scores"):
    st.warning("No analysis results yet. Please run the analysis first.")
    st.page_link("pages/2_Run_Analysis.py", label="Go to Run Analysis")
    st.stop()

scores = st.session_state["scores"]
coding_results = st.session_state["coding_results"]
codebook = st.session_state["codebook"]

sorted_pids = sorted(scores.keys())
selected_pid = st.selectbox("Select Participant", sorted_pids)

if not selected_pid:
    st.stop()

participant_score = scores[selected_pid]
result = coding_results[selected_pid]

st.subheader(f"Participant: {selected_pid}")

col1, col2 = st.columns([1, 2])
with col1:
    st.metric("Overall Score", f"{participant_score.overall:.1f}")
with col2:
    if hasattr(result, "summary") and result.summary:
        st.info(f"**AI Summary:** {result.summary}")

st.plotly_chart(radar_chart(participant_score, codebook.dimensions), use_container_width=True)

st.subheader("Dimension Scores")

edited = False
for i in range(0, len(codebook.dimensions), 2):
    col_a, col_b = st.columns(2)
    for col, j in [(col_a, i), (col_b, i + 1)]:
        if j >= len(codebook.dimensions):
            break
        dim = codebook.dimensions[j]
        ds = result.dimensions.get(dim.id) if hasattr(result, "dimensions") else None

        with col:
            with st.container(border=True):
                st.markdown(f"**{dim.label}**")
                if ds:
                    new_score = st.number_input(
                        f"Score (0-{codebook.scale})",
                        min_value=0,
                        max_value=codebook.scale,
                        value=ds.score,
                        key=f"score_{selected_pid}_{dim.id}",
                    )
                    if new_score != ds.score:
                        ds.score = new_score
                        result.human_reviewed = True
                        edited = True

                    st.caption(f"Confidence: {ds.confidence:.2f}")

                    if ds.evidence:
                        st.markdown("**Evidence:**")
                        for quote in ds.evidence:
                            st.markdown(f"> {quote}")

                    if ds.reason:
                        st.markdown(f"**Reasoning:** {ds.reason}")
                else:
                    st.warning("No data for this dimension")

if edited:
    if st.button("Save Edits", type="primary"):
        new_score = compute_scores(result, codebook)
        st.session_state["scores"][selected_pid] = new_score
        st.session_state["coding_results"][selected_pid] = result
        st.success("Edits saved!")
        st.rerun()
