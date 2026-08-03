import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from collections import Counter

from utils.validators import ParticipantScore


def score_distribution_histogram(scores: dict[str, ParticipantScore]) -> go.Figure:
    vals = [ps.overall for ps in scores.values()]
    fig = px.histogram(
        x=vals,
        nbins=10,
        title="Overall Precarity Score Distribution",
        labels={"x": "Overall Score (0-100)", "y": "Count"},
    )
    fig.update_layout(bargap=0.1)
    return fig


def dimension_bar_chart(dim_averages: dict[str, float]) -> go.Figure:
    names = list(dim_averages.keys())
    values = list(dim_averages.values())
    fig = go.Figure(data=[go.Bar(x=names, y=values, text=[f"{v:.1f}" for v in values], textposition="outside")])
    fig.update_layout(
        title="Average Score by Dimension",
        xaxis_title="Dimension",
        yaxis_title="Average Score (0-100)",
    )
    return fig


def participant_ranking_chart(ranked: list[tuple[str, float]]) -> go.Figure:
    names = [r[0] for r in reversed(ranked)]
    values = [r[1] for r in reversed(ranked)]
    fig = go.Figure(data=[go.Bar(x=values, y=names, orientation="h", text=[f"{v:.1f}" for v in values], textposition="outside")])
    fig.update_layout(
        title="Participant Ranking by Overall Score",
        xaxis_title="Overall Score (0-100)",
        yaxis_title="Participant",
        height=max(400, len(names) * 30),
    )
    return fig


def theme_frequency_chart(coding_results: dict) -> go.Figure:
    evidence_counter = Counter()
    for result in coding_results.values():
        if hasattr(result, "dimensions"):
            for ds in result.dimensions.values():
                for quote in ds.evidence:
                    if quote:
                        short = quote[:80] + ("..." if len(quote) > 80 else "")
                        evidence_counter[short] += 1

    top = evidence_counter.most_common(20)
    if not top:
        fig = go.Figure()
        fig.update_layout(title="No evidence quotes available")
        return fig

    names = [t[0] for t in reversed(top)]
    values = [t[1] for t in reversed(top)]
    fig = go.Figure(data=[go.Bar(x=values, y=names, orientation="h")])
    fig.update_layout(
        title="Top 20 Evidence Quotes by Frequency",
        xaxis_title="Occurrences",
        height=max(400, len(names) * 25),
    )
    return fig


def radar_chart(participant_score: ParticipantScore, dimensions) -> go.Figure:
    dim_labels = []
    dim_values = []
    for dim in dimensions:
        dim_labels.append(dim.label)
        dim_values.append(participant_score.dimension_scores.get(dim.id, 0))

    dim_values.append(dim_values[0])
    dim_labels.append(dim_labels[0])

    fig = go.Figure(data=go.Scatterpolar(r=dim_values, theta=dim_labels, fill="toself", name=participant_score.participant))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        title=f"Dimension Profile: {participant_score.participant}",
    )
    return fig


def correlation_heatmap(scores: dict[str, ParticipantScore]) -> go.Figure:
    """Return a Plotly heatmap of Pearson correlations between dimension scores.

    Participants with any missing dimension score are excluded before computing
    the correlation matrix. Returns a 'Not enough data' figure when fewer than
    2 participants have complete scores.
    """
    # Build DataFrame: rows = participants, columns = dimension IDs
    records = {pid: ps.dimension_scores for pid, ps in scores.items()}
    df = pd.DataFrame.from_dict(records, orient="index")

    # Drop participants with any missing dimension score
    df = df.dropna()

    if len(df) < 2:
        fig = go.Figure()
        fig.add_annotation(
            text="Not enough data (need at least 2 participants with complete scores)",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14),
        )
        fig.update_layout(title="Dimension Correlation Heatmap")
        return fig

    corr = df.corr()

    # Map raw dimension IDs to human-readable labels
    dim_labels = [col.replace("_", " ").title() for col in corr.columns]

    z = corr.values.tolist()
    text = [[f"{v:.2f}" for v in row] for row in corr.values]

    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=dim_labels,
        y=dim_labels,
        zmin=-1,
        zmax=1,
        colorscale="RdBu",
        text=text,
        texttemplate="%{text}",
        hovertemplate="x: %{x}<br>y: %{y}<br>r: %{z:.2f}<extra></extra>",
    ))
    fig.update_layout(
        title="Dimension Correlation Heatmap",
        xaxis_title="Dimension",
        yaxis_title="Dimension",
    )
    return fig
