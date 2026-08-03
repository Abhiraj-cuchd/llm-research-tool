import streamlit as st
import re

st.title("Search Transcripts")

if not st.session_state.get("transcripts"):
    st.warning("No transcripts loaded. Please upload transcripts first.")
    st.page_link("pages/1_Upload.py", label="Go to Upload Page")
    st.stop()

transcripts = st.session_state["transcripts"]

query = st.text_input("Search keyword or phrase", placeholder="e.g. financial abuse, custody, police")

if query:
    pattern = re.compile(re.escape(query.strip()), re.IGNORECASE)
    total_matches = 0

    for pid, interview in transcripts.items():
        matches = []
        for qa in interview.questions:
            for field in ("question", "answer"):
                text = qa[field]
                if pattern.search(text):
                    highlighted = pattern.sub(
                        lambda m: f"<mark>{m.group()}</mark>", text
                    )
                    matches.append({"field": field.capitalize(), "text": highlighted})

        if matches:
            total_matches += len(matches)
            with st.expander(f"{pid} — {len(matches)} match(es)"):
                for m in matches:
                    st.markdown(f"**{m['field']}:** {m['text']}", unsafe_allow_html=True)
                    st.divider()

    if total_matches == 0:
        st.info(f'No matches found for "{query}".')
    else:
        st.caption(f"{total_matches} match(es) across {len(transcripts)} participants.")
