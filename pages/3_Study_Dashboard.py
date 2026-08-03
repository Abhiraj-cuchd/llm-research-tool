import streamlit as st

from modules.scorer import rank_participants, dimension_averages
from modules.analytics import (
    score_distribution_histogram,
    dimension_bar_chart,
    participant_ranking_chart,
    theme_frequency_chart,
)
from modules.exporter import to_excel, to_csv, to_json, to_pdf

st.title("Study Dashboard")

if not st.session_state.get("scores"):
    st.warning("No analysis results yet. Please run the analysis first.")
    st.page_link("pages/2_Run_Analysis.py", label="Go to Run Analysis")
    st.stop()

scores = st.session_state["scores"]
coding_results = st.session_state["coding_results"]
codebook = st.session_state["codebook"]

st.info("Session data lives in memory. Export your results before closing the browser.")

with st.sidebar:
    st.subheader("Export Data")
    try:
        excel_data = to_excel(st.session_state)
        st.download_button("Download Excel", data=excel_data, file_name="study_results.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        st.error(f"Excel: {e}")
    try:
        csv_data = to_csv(st.session_state)
        st.download_button("Download CSV", data=csv_data, file_name="study_results.csv", mime="text/csv")
    except Exception as e:
        st.error(f"CSV: {e}")
    try:
        json_data = to_json(st.session_state)
        st.download_button("Download JSON", data=json_data, file_name="study_results.json", mime="application/json")
    except Exception as e:
        st.error(f"JSON: {e}")
    try:
        pdf_data = to_pdf(st.session_state)
        st.download_button("Download PDF Report", data=pdf_data, file_name="study_report.pdf", mime="application/pdf")
    except Exception as e:
        st.error(f"PDF: {e}")

dim_avgs = dimension_averages(scores)
ranked = rank_participants(scores)

highest_dim = max(dim_avgs, key=dim_avgs.get) if dim_avgs else None
lowest_dim = min(dim_avgs, key=dim_avgs.get) if dim_avgs else None

all_confidences = []
for result in coding_results.values():
    if hasattr(result, "dimensions"):
        for ds in result.dimensions.values():
            all_confidences.append(ds.confidence)
avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0

st.subheader("Key Metrics")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Participants", len(scores))
col2.metric("Avg Overall Score", f"{sum(ps.overall for ps in scores.values()) / len(scores):.1f}")
col3.metric("Highest Dimension", highest_dim, f"{dim_avgs.get(highest_dim, 0):.1f}")
col4.metric("Lowest Dimension", lowest_dim, f"{dim_avgs.get(lowest_dim, 0):.1f}")
col5.metric("Avg AI Confidence", f"{avg_confidence:.2f}")

st.divider()

col_left, col_right = st.columns(2)
with col_left:
    st.plotly_chart(score_distribution_histogram(scores), use_container_width=True)
with col_right:
    st.plotly_chart(dimension_bar_chart(dim_avgs), use_container_width=True)

st.plotly_chart(participant_ranking_chart(ranked), use_container_width=True)

st.subheader("Evidence Frequency")
st.plotly_chart(theme_frequency_chart(coding_results), use_container_width=True)

st.subheader("Top 20 Evidence Quotes")
evidence_data = []
for pid, result in coding_results.items():
    if hasattr(result, "dimensions"):
        for dim_id, ds in result.dimensions.items():
            for quote in ds.evidence:
                if quote:
                    evidence_data.append({
                        "Participant": pid,
                        "Dimension": dim_id,
                        "Quote": quote,
                    })

if evidence_data:
    st.dataframe(evidence_data[:20], use_container_width=True, hide_index=True)
else:
    st.info("No evidence quotes extracted yet.")
