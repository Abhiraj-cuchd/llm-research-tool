import streamlit as st
from datetime import datetime
import random
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

from utils.validators import RunMetadata
from modules.coder import code_interview
from modules.scorer import compute_scores
from utils.persistence import save_session
from utils.spinner_messages import RESEARCH_PHRASES

BATCH_SIZE = 5

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

st.subheader(f"Ready to code {len(transcripts)} participant(s)")

run = st.button("Run Analysis", type="primary", use_container_width=True)

if run:
    coding_results = {}
    scores = {}
    failed = {}
    total = len(transcripts)

    progress_bar = st.progress(0)
    status_text = st.empty()
    status_text.text(random.choice(RESEARCH_PHRASES))

    # Submit all at once; poll every 5 s from the main thread so st.* calls
    # work (background threads lack ScriptRunContext). Each 5 s wakeup rotates
    # the status phrase; any futures that completed in that window are harvested.
    raw_results: dict[str, object] = {}

    with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
        future_to_pid = {
            executor.submit(code_interview, interview, codebook, llm_config): pid
            for pid, interview in transcripts.items()
        }
        pending = set(future_to_pid.keys())
        while pending:
            done, pending = wait(pending, timeout=5, return_when=FIRST_COMPLETED)
            for future in done:
                pid = future_to_pid[future]
                raw_results[pid] = future.result()
                progress_bar.progress(len(raw_results) / total)
            if pending:
                status_text.text(random.choice(RESEARCH_PHRASES))

    # All futures done — render outcome messages in a single pass
    completed = 0
    for pid, result in raw_results.items():
        if hasattr(result, "error"):
            failed[pid] = result
            st.error(f"❌ {pid}: {result.error}")
        else:
            coding_results[pid] = result
            score = compute_scores(result, codebook)
            scores[pid] = score
            completed += 1
            st.success(f"✅ {pid}: overall score {score.overall}")

    st.session_state["coding_results"] = coding_results
    st.session_state["scores"] = scores

    status_text.text("Analysis complete!")

    run_metadata = RunMetadata(
        model=llm_config.model,
        timestamp=datetime.now().isoformat(),
        prompt_version=codebook.version,
        codebook_version=codebook.version,
        participant_count=total,
        completed_count=completed,
        failed_count=len(failed),
    )
    st.session_state["run_metadata"] = run_metadata.model_dump()

    try:
        save_path = save_session(st.session_state)
        st.info(f"Session auto-saved to `{save_path}`")
    except Exception as e:
        st.warning(f"Could not auto-save session: {e}")

    if failed:
        st.warning(f"{len(failed)} participant(s) failed. You can re-run them below.")
        if st.button("Re-run Failed"):
            raw_retry: dict[str, object] = {}
            with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
                future_to_pid = {
                    executor.submit(code_interview, transcripts[pid], codebook, llm_config): pid
                    for pid in list(failed.keys())
                }
                pending = set(future_to_pid.keys())
                while pending:
                    done, pending = wait(pending, timeout=5, return_when=FIRST_COMPLETED)
                    for future in done:
                        pid = future_to_pid[future]
                        raw_retry[pid] = future.result()

            for pid, result in raw_retry.items():
                if hasattr(result, "error"):
                    st.error(f"❌ {pid}: still failed — {result.error}")
                else:
                    coding_results[pid] = result
                    score = compute_scores(result, codebook)
                    scores[pid] = score
                    failed.pop(pid)
                    st.success(f"✅ {pid}: overall score {score.overall}")
            st.session_state["coding_results"] = coding_results
            st.session_state["scores"] = scores
            st.rerun()

if st.session_state.get("coding_results"):
    st.divider()
    if st.button("Re-run All", type="secondary"):
        for key in ["coding_results", "scores", "run_metadata"]:
            st.session_state[key] = {} if key != "run_metadata" else {}
        st.rerun()
