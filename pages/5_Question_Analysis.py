import streamlit as st

from modules.llm_client import call
from utils.validators import LLMConfig

st.title("Question Analysis")

if not st.session_state.get("transcripts"):
    st.warning("No transcripts loaded. Please upload transcripts first.")
    st.page_link("pages/1_Upload.py", label="Go to Upload Page")
    st.stop()

transcripts = st.session_state["transcripts"]

# Collect all unique questions across participants
all_questions: dict[str, list[dict]] = {}
for pid, interview in transcripts.items():
    for qa in interview.questions:
        q = qa["question"].strip()
        if q not in all_questions:
            all_questions[q] = []
        all_questions[q].append({"participant": pid, "answer": qa["answer"]})

if not all_questions:
    st.warning("No questions found in transcripts.")
    st.stop()

selected_q = st.selectbox("Select a question", list(all_questions.keys()))

responses = all_questions[selected_q]
st.markdown(f"**{len(responses)} participant(s) answered this question.**")
st.divider()

for resp in responses:
    with st.expander(f"{resp['participant']}"):
        st.write(resp["answer"])

st.divider()

if st.button("Synthesise responses", type="primary"):
    llm_config: LLMConfig | None = st.session_state.get("llm_config")
    if not llm_config or not llm_config.api_key:
        st.error("API key not configured. Set it on the Run Analysis page first.")
        st.stop()

    cache_key = f"synthesis_{selected_q}"
    if cache_key in st.session_state:
        st.markdown(st.session_state[cache_key])
    else:
        answers_block = "\n\n".join(
            f"[{r['participant']}]: {r['answer']}" for r in responses
        )
        prompt = (
            "You are a qualitative research assistant. "
            "The following are participant responses to the interview question below.\n\n"
            f"Question: {selected_q}\n\nResponses:\n{answers_block}\n\n"
            "Provide:\n1. Common themes across responses\n2. Contrasting perspectives\n"
            "3. A 2-3 sentence synthesis\n\nReturn plain text, no JSON."
        )
        with st.spinner("Synthesising responses..."):
            # Use non-JSON mode for synthesis — plain text output is intentional here
            from openai import OpenAI
            client = OpenAI(api_key=llm_config.api_key, base_url=llm_config.base_url)
            response = client.chat.completions.create(
                model=llm_config.model,
                messages=[{"role": "user", "content": prompt}],
                timeout=60.0,
            )
            result = response.choices[0].message.content or ""
        st.session_state[cache_key] = result
        st.markdown(result)
