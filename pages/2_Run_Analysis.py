import streamlit as st
from datetime import datetime
import random
import logging
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

from utils.validators import RunMetadata
from utils.auth import require_auth
from utils.state import bootstrap_session

require_auth()
bootstrap_session()
from modules.coder import code_interview
from modules.scorer import compute_scores
from utils.persistence import (
    save_session,
    save_checkpoint,
    load_checkpoint,
    clear_checkpoint,
)
from utils.spinner_messages import RESEARCH_PHRASES

logger = logging.getLogger(__name__)

BATCH_SIZE = 8

st.title("Run Analysis")

if not st.session_state.get("transcripts"):
    st.warning("No transcripts loaded. Please upload transcripts first.")
    st.page_link("pages/1_Upload.py", label="Go to Upload Page")
    st.stop()

transcripts = st.session_state["transcripts"]
codebook = st.session_state["codebook"]
llm_config = st.session_state.get("llm_config")

if not llm_config or not llm_config.api_key:
    st.error("LLM not configured. Please set API credentials in Configuration.")
    st.stop()

# ── Resume state ─────────────────────────────────────────────────────────
# A checkpoint captures transcripts + results as they complete. On a timeout,
# reload it so completed participants are not re-billed.
checkpoint = load_checkpoint()
if checkpoint:
    st.session_state["transcripts"] = checkpoint.get("transcripts", transcripts)
    st.session_state["coding_results"] = checkpoint.get("coding_results", {})
    st.session_state["scores"] = checkpoint.get("scores", {})
    if checkpoint.get("codebook"):
        st.session_state["codebook"] = checkpoint["codebook"]
    transcripts = st.session_state["transcripts"]
    codebook = st.session_state["codebook"]
    st.info(
        f"Resuming previous run: {len(st.session_state.get('coding_results', {}))} "
        f"of {len(transcripts)} participant(s) already coded. Already-coded "
        "participants will be skipped to avoid wasting credits."
    )

pending_pids = [
    pid for pid in transcripts
    if pid not in st.session_state.get("coding_results", {})
]

st.subheader(
    f"Ready to code {len(pending_pids)} participant(s) "
    f"({len(transcripts) - len(pending_pids)} already complete)"
)

run = st.button("Run Analysis", type="primary", use_container_width=True)

if run:
    coding_results = dict(st.session_state.get("coding_results", {}))
    scores = dict(st.session_state.get("scores", {}))
    failed = {}
    total = len(pending_pids)

    progress_bar = st.progress(0)
    status_text = st.empty()
    status_text.text(random.choice(RESEARCH_PHRASES))

    with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
        future_to_pid = {
            executor.submit(code_interview, transcripts[pid], codebook, llm_config): pid
            for pid in pending_pids
        }
        pending = set(future_to_pid.keys())
        while pending:
            done, pending = wait(pending, timeout=5, return_when=FIRST_COMPLETED)
            for future in done:
                pid = future_to_pid[future]
                result = future.result()

                if hasattr(result, "error"):
                    failed[pid] = result
                    st.error(f"❌ {pid}: {result.error}")
                else:
                    coding_results[pid] = result
                    score = compute_scores(result, codebook)
                    scores[pid] = score
                    st.success(f"✅ {pid}: overall score {score.overall}")

                # Persist progress after every participant so a timeout cannot
                # wipe out completed work.
                st.session_state["coding_results"] = coding_results
                st.session_state["scores"] = scores
                try:
                    save_checkpoint(st.session_state)
                except Exception:
                    pass

                progress_bar.progress(len(coding_results) + len(failed))
            if pending:
                status_text.text(random.choice(RESEARCH_PHRASES))

    st.session_state["coding_results"] = coding_results
    st.session_state["scores"] = scores

    status_text.text("Analysis complete!")

    run_metadata = RunMetadata(
        model=llm_config.model,
        timestamp=datetime.now().isoformat(),
        prompt_version=codebook.version,
        codebook_version=codebook.version,
        participant_count=len(transcripts),
        completed_count=len(coding_results),
        failed_count=len(failed),
    )
    st.session_state["run_metadata"] = run_metadata.model_dump()

    try:
        save_path = save_session(st.session_state)
        clear_checkpoint()
        st.info(f"Session auto-saved to `{save_path}`")
    except Exception as e:
        st.warning(f"Could not auto-save session: {e}")

    if failed:
        st.warning(
            f"{len(failed)} participant(s) failed. Click 'Run Analysis' again "
            "to retry them (already-coded participants will be skipped)."
        )

if st.session_state.get("coding_results"):
    st.divider()
    if st.button("Re-run All", type="secondary", use_container_width=True):
        for key in ["coding_results", "scores", "run_metadata"]:
            st.session_state[key] = {} if key != "run_metadata" else {}
        clear_checkpoint()
        st.rerun()
