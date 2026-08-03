import re
import json
import io
import pandas as pd


def _sanitise_column_name(name: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", name.lower())


def build_export_df(session_state: dict) -> pd.DataFrame:
    coding_results = session_state.get("coding_results", {})
    scores = session_state.get("scores", {})
    codebook = session_state.get("codebook")

    rows = []
    for pid, result in coding_results.items():
        row = {
            "participant_id": pid,
            "overall_score": scores[pid].overall if pid in scores else pd.NA,
        }
        if codebook:
            for dim in codebook.dimensions:
                d = result.dimensions.get(dim.id) if hasattr(result, "dimensions") else None
                col_id = _sanitise_column_name(dim.id)
                row[f"{col_id}_score"] = d.score if d else pd.NA
                row[f"{col_id}_evidence"] = " | ".join(d.evidence) if d and d.evidence else ""
                row[f"{col_id}_reasoning"] = d.reason if d else ""
        rows.append(row)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Column ordering
    codebook_order = ["participant_id", "overall_score"]
    if codebook:
        for dim in codebook.dimensions:
            col_id = _sanitise_column_name(dim.id)
            codebook_order.extend([f"{col_id}_score", f"{col_id}_evidence", f"{col_id}_reasoning"])
    existing_cols = [c for c in codebook_order if c in df.columns]
    other_cols = [c for c in df.columns if c not in existing_cols]
    df = df[existing_cols + other_cols]

    # Enforce dtypes
    score_cols = [c for c in df.columns if c.endswith("_score")]
    for c in score_cols:
        df[c] = df[c].astype("Int64")
    df["overall_score"] = df["overall_score"].astype("Float64")

    return df


def to_excel(session_state: dict) -> bytes:
    df = build_export_df(session_state)
    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Participants", index=False)
        ws = writer.sheets["Participants"]
        for col in ws.columns:
            col_letter = col[0].column_letter
            max_len = max((len(str(c.value or "")) for c in col), default=0)
            ws.column_dimensions[col_letter].width = min(max_len + 2, 60)

    return buffer.getvalue()


def to_csv(session_state: dict) -> bytes:
    df = build_export_df(session_state)
    buffer = io.BytesIO()
    df.to_csv(buffer, index=False, encoding="utf-8-sig")
    return buffer.getvalue()


def to_json(session_state: dict) -> bytes:
    payload = {
        "transcripts": session_state.get("transcripts", {}),
        "coding_results": session_state.get("coding_results", {}),
        "scores": session_state.get("scores", {}),
        "codebook": session_state.get("codebook"),
        "run_metadata": session_state.get("run_metadata", {}),
    }

    def serialise(o):
        if hasattr(o, "model_dump"):
            return o.model_dump()
        raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")

    return json.dumps(payload, default=serialise, ensure_ascii=False, indent=2).encode("utf-8")


def to_pdf(session_state: dict) -> bytes:
    try:
        from datetime import datetime as _dt
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import cm

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=(21 * cm, 29.7 * cm),
            leftMargin=2.5 * cm,
            rightMargin=2.5 * cm,
            topMargin=2.5 * cm,
            bottomMargin=2.5 * cm,
        )

        styles = getSampleStyleSheet()
        bullet_style = ParagraphStyle(
            "BulletEvidence",
            parent=styles["Normal"],
            leftIndent=18,
            spaceAfter=2,
        )

        elements = []

        # Title
        elements.append(Paragraph("Qualitative Research Analysis Report", styles["Heading1"]))
        elements.append(Spacer(1, 0.4 * cm))

        # Study metadata
        run_metadata = session_state.get("run_metadata")
        date_str = _dt.now().strftime("%Y-%m-%d")
        model_str = "N/A"
        coding_results = session_state.get("coding_results", {})
        scores = session_state.get("scores", {})
        codebook = session_state.get("codebook")
        total_participants = len(coding_results)

        if run_metadata:
            ts = getattr(run_metadata, "timestamp", None)
            if ts:
                try:
                    date_str = str(ts)[:10]
                except Exception:
                    pass
            model_str = getattr(run_metadata, "model", None) or "N/A"
            pc = getattr(run_metadata, "participant_count", None)
            if pc:
                total_participants = pc

        elements.append(Paragraph("Study Metadata", styles["Heading2"]))
        meta_table = Table(
            [
                ["Total Participants", str(total_participants)],
                ["Date Generated", date_str],
                ["Model Used", model_str],
            ],
            colWidths=[5 * cm, 10.5 * cm],
        )
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eeeeee")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 0.6 * cm))

        # Summary table
        elements.append(Paragraph("Participant Summary", styles["Heading2"]))
        elements.append(Spacer(1, 0.2 * cm))

        dim_configs = codebook.dimensions if codebook else []
        header_row = ["Participant", "Overall Score"] + [d.label for d in dim_configs]
        summary_rows = [header_row]
        for pid, result in coding_results.items():
            overall = scores[pid].overall if pid in scores else None
            overall_str = f"{overall:.2f}" if isinstance(overall, float) else (str(overall) if overall is not None else "")
            row = [pid, overall_str]
            for dim in dim_configs:
                d = result.dimensions.get(dim.id) if hasattr(result, "dimensions") else None
                row.append(str(d.score) if d else "")
            summary_rows.append(row)

        if len(summary_rows) > 1:
            available = 16 * cm
            pid_w = 3.5 * cm
            overall_w = 2.5 * cm
            dim_w = (available - pid_w - overall_w) / len(dim_configs) if dim_configs else (available - pid_w - overall_w)
            col_widths = [pid_w, overall_w] + [dim_w] * len(dim_configs)
            sum_table = Table(summary_rows, colWidths=col_widths, repeatRows=1)
            sum_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ]))
            elements.append(sum_table)

        elements.append(Spacer(1, 0.5 * cm))

        # Per-participant detail sections
        pids = list(coding_results.keys())
        for idx, pid in enumerate(pids):
            if idx > 0:
                elements.append(PageBreak())

            result = coding_results[pid]
            elements.append(Paragraph(f"Participant: {pid}", styles["Heading2"]))
            elements.append(Spacer(1, 0.15 * cm))

            overall = scores[pid].overall if pid in scores else None
            overall_str = f"{overall:.2f}" if isinstance(overall, float) else (str(overall) if overall is not None else "N/A")
            elements.append(Paragraph(f"Overall Score: {overall_str}", styles["Normal"]))
            elements.append(Spacer(1, 0.3 * cm))

            for dim in dim_configs:
                d = result.dimensions.get(dim.id) if hasattr(result, "dimensions") else None
                elements.append(Paragraph(dim.label, styles["Heading3"]))
                if d:
                    elements.append(Paragraph(f"Score: {d.score}", styles["Normal"]))
                    if d.evidence:
                        elements.append(Spacer(1, 0.1 * cm))
                        elements.append(Paragraph("Evidence:", styles["Normal"]))
                        for quote in d.evidence:
                            elements.append(Paragraph(f"• {quote}", bullet_style))
                    if d.reason:
                        elements.append(Spacer(1, 0.1 * cm))
                        elements.append(Paragraph(f"Reasoning: {d.reason}", styles["Normal"]))
                else:
                    elements.append(Paragraph("No data available.", styles["Normal"]))
                elements.append(Spacer(1, 0.25 * cm))

        doc.build(elements)
        return buffer.getvalue()

    except Exception:
        # Fallback: plain UTF-8 text report
        coding_results = session_state.get("coding_results", {})
        scores = session_state.get("scores", {})
        codebook = session_state.get("codebook")
        run_metadata = session_state.get("run_metadata")

        lines = ["Qualitative Research Analysis Report", "=" * 44, ""]

        lines.append("Study Metadata")
        lines.append("-" * 20)
        lines.append(f"Total Participants: {len(coding_results)}")
        if run_metadata:
            ts = getattr(run_metadata, "timestamp", None)
            if ts:
                lines.append(f"Date Generated: {str(ts)[:10]}")
            model = getattr(run_metadata, "model", None)
            if model:
                lines.append(f"Model Used: {model}")
        lines.append("")

        dim_configs = codebook.dimensions if codebook else []

        for pid, result in coding_results.items():
            lines.append(f"Participant: {pid}")
            lines.append("-" * 30)
            overall = scores[pid].overall if pid in scores else None
            lines.append(f"Overall Score: {overall:.2f}" if isinstance(overall, float) else f"Overall Score: {overall}")
            lines.append("")
            for dim in dim_configs:
                d = result.dimensions.get(dim.id) if hasattr(result, "dimensions") else None
                lines.append(dim.label)
                if d:
                    lines.append(f"  Score: {d.score}")
                    if d.evidence:
                        lines.append("  Evidence:")
                        for q in d.evidence:
                            lines.append(f"    - {q}")
                    if d.reason:
                        lines.append(f"  Reasoning: {d.reason}")
                else:
                    lines.append("  No data available.")
                lines.append("")
            lines.append("")

        return "\n".join(lines).encode("utf-8")
