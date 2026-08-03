import streamlit as st
from modules.uploader import extract_zip, UploadError
from modules.parser import parse_docx, ParseError
from utils.persistence import list_sessions, load_session
from utils.auth import require_auth
from utils.state import bootstrap_session

require_auth()
bootstrap_session()

st.title("Upload Transcripts")

st.markdown("Upload a ZIP file containing interview transcripts in `.docx` format.")

uploaded = st.file_uploader("Choose a ZIP file", type=["zip"], key="zip_uploader")

if uploaded is not None:
    with st.spinner("Extracting and parsing transcripts..."):
        try:
            file_pairs = extract_zip(uploaded.read())
        except UploadError as e:
            st.error(str(e))
            st.stop()

        transcripts = {}
        failed = {}

        progress_bar = st.progress(0)
        status_text = st.empty()

        total = len(file_pairs)
        for idx, (filename, docx_bytes) in enumerate(file_pairs):
            status_text.text(f"Parsing: {filename}")
            try:
                interview = parse_docx(filename, docx_bytes)
                transcripts[interview.participant] = interview
            except ParseError as e:
                failed[filename] = str(e)
            progress_bar.progress((idx + 1) / total)

        status_text.text("Parsing complete!")
        st.session_state["transcripts"] = transcripts

    success_count = len(transcripts)
    fail_count = len(failed)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total files", total)
    col2.metric("Parsed", success_count)
    col3.metric("Failed", fail_count, delta=None if fail_count == 0 else f"-{fail_count}")

    if success_count > 0:
        st.subheader("Parsing Results")
        table_data = []
        for pid, interview in transcripts.items():
            table_data.append({
                "Participant ID": pid,
                "Questions": len(interview.questions),
                "Status": "✅ Parsed",
            })
        for filename, err in failed.items():
            table_data.append({
                "Participant ID": filename,
                "Questions": 0,
                "Status": f"❌ {err}",
            })
        st.dataframe(table_data, use_container_width=True, hide_index=True)

    if fail_count > 0:
        st.warning(f"{fail_count} file(s) failed to parse. Check the error messages above.")

    col_clear, col_next = st.columns([1, 1])
    with col_clear:
        if st.button("Clear & Re-upload", type="secondary", use_container_width=True):
            for key in ["transcripts", "coding_results", "scores", "run_metadata"]:
                st.session_state[key] = {} if key != "run_metadata" else {}
            st.rerun()
    with col_next:
        if success_count > 0:
            if st.button("Next: Run Analysis →", type="primary", use_container_width=True):
                st.switch_page("pages/2_Run_Analysis.py")

elif not st.session_state.get("transcripts"):
    st.info("No transcripts loaded yet. Upload a ZIP file to begin.")
else:
    existing = st.session_state["transcripts"]
    st.success(f"{len(existing)} transcript(s) loaded and ready for analysis.")
    col_clear, col_next = st.columns([1, 1])
    with col_clear:
        if st.button("Clear & Re-upload", type="secondary", use_container_width=True):
            for key in ["transcripts", "coding_results", "scores", "run_metadata"]:
                st.session_state[key] = {} if key != "run_metadata" else {}
            st.rerun()
    with col_next:
        if st.button("Next: Run Analysis →", type="primary", use_container_width=True):
            st.switch_page("pages/2_Run_Analysis.py")

st.divider()

with st.expander("Load Previous Session"):
    sessions = list_sessions()
    if not sessions:
        st.info("No saved sessions found.")
    else:
        for s in sessions:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**{s['study_name']}** — {s['timestamp'][:16] if s['timestamp'] else 'Unknown date'}")
            with col2:
                st.caption(f"{s['participant_count']} participants")
            with col3:
                if st.button("Load", key=f"load_{s['path']}"):
                    try:
                        data = load_session(s["path"])
                        st.session_state["transcripts"] = data.get("transcripts", {})
                        st.session_state["coding_results"] = data.get("coding_results", {})
                        st.session_state["scores"] = data.get("scores", {})
                        st.session_state["codebook"] = data.get("codebook", st.session_state.get("codebook"))
                        st.session_state["run_metadata"] = data.get("run_metadata", {})
                        st.success("Session loaded!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to load session: {e}")
