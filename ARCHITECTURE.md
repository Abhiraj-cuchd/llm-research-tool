# PoC Architecture — AI-Assisted Qualitative Research Platform

## Guiding Constraints

- Streamlit single-process app — no separate backend server
- No database — `st.session_state` + local JSON files for persistence
- Sequential LLM calls — no async batching (keeps error handling simple)
- Crash-safe — validate at every boundary; never let a bad LLM response bring down the session
- No auth, no multi-user, no deployment infra

---

## File Structure

```
research_tool/
├── app.py                        # Entry point — page router + global state init
│
├── config/
│   └── default_codebook.yaml     # Default dimensions, weights, prompt template, scale
│
├── modules/
│   ├── uploader.py               # ZIP extraction → list of (name, bytes) pairs
│   ├── parser.py                 # DOCX bytes → structured interview JSON
│   ├── llm_client.py             # Provider-agnostic LLM wrapper (OpenAI / Anthropic / Gemini / OpenRouter)
│   ├── coder.py                  # Prompt builder + calls llm_client + validates output
│   ├── scorer.py                 # Weighted score aggregation per participant
│   ├── analytics.py              # All Plotly chart builders
│   └── exporter.py               # CSV / Excel / JSON / PDF generation
│
├── pages/
│   ├── 1_Upload.py               # ZIP upload, extraction, parsing trigger
│   ├── 2_Run_Analysis.py         # Per-participant LLM coding with progress bar
│   ├── 3_Study_Dashboard.py      # KPI cards + study-level charts
│   ├── 4_Participant_View.py     # Individual radar chart, dimension cards, evidence
│   ├── 5_Question_Analysis.py    # Question selector + cross-participant synthesis
│   ├── 6_Search.py               # Keyword search + transcript highlight
│   └── 7_Configuration.py        # Codebook editor, weights slider, LLM key config
│
├── utils/
│   ├── state.py                  # st.session_state schema + safe accessors
│   ├── validators.py             # Pydantic models for LLM JSON output
│   └── persistence.py            # Save/load session to data/<session_id>.json
│
├── data/                         # Runtime only — gitignored
│
├── requirements.txt
└── .env.example
```

---

## Data Flow

```
ZIP Upload
    │
    ▼
uploader.py
  extract_zip(bytes) → [(filename, docx_bytes), ...]
    │
    ▼
parser.py
  parse_docx(docx_bytes) → InterviewJSON
  {participant, questions: [{question, answer}]}
    │
    ▼
  stored in st.session_state["transcripts"]
    │
    ▼
coder.py
  build_prompt(interview, codebook) → str
  call_llm(prompt) → raw_str
  validate_output(raw_str) → CodingResult   ← Pydantic validation here
    │
    ▼
  stored in st.session_state["coding_results"]
    │
    ▼
scorer.py
  compute_scores(coding_result, weights) → ParticipantScore
    │
    ▼
  stored in st.session_state["scores"]
    │
    ▼
analytics.py / pages/    ← read-only from session state
    │
    ▼
exporter.py              ← read-only from session state
```

---

## Session State Schema

```python
st.session_state = {
    "transcripts":     dict[str, InterviewJSON],     # keyed by participant ID
    "coding_results":  dict[str, CodingResult],      # keyed by participant ID
    "scores":          dict[str, ParticipantScore],  # keyed by participant ID
    "codebook":        Codebook,                     # loaded from YAML, editable in UI
    "llm_config":      LLMConfig,                    # provider, model, api_key
    "run_metadata":    RunMetadata,                  # timestamp, model used, prompt version
}
```

State is initialised once in `app.py` on first load. All pages read from it — nothing writes to it except the Upload and Run Analysis pages.

---

## Module Responsibilities

### `uploader.py`
- Accepts `bytes` from `st.file_uploader`
- Uses `zipfile.ZipFile` in-memory — no disk write
- Returns `list[tuple[str, bytes]]`
- Raises `UploadError` (caught by page, shown as `st.error`)

### `parser.py`
- Accepts DOCX `bytes` via `io.BytesIO` → `python-docx`
- Detects speaker turns via regex patterns (e.g. `"Q:"`, `"A:"`, `"Interviewer:"`, `"Participant:"`)
- Falls back to paragraph-level splitting if no speaker markers found
- Returns `InterviewJSON` dataclass

### `llm_client.py`
- Single `call(prompt, config) -> str` interface
- Uses `openai` SDK only — DeepSeek is OpenAI-compatible, just set `base_url`
- `LLMConfig` holds `api_key`, `model`, and optional `base_url` (defaults to OpenAI; set to `https://api.deepseek.com` for DeepSeek)
- **`response_format={"type": "json_object"}` is always set** — forces the model to return valid JSON; prose leakage is impossible
- Retries up to 3× on rate limit / timeout with exponential backoff
- Hard timeout of 60s per call
- Never raises — returns `LLMError` result object on failure so the pipeline can skip + log

```python
client = openai.OpenAI(api_key=config.api_key, base_url=config.base_url)
response = client.chat.completions.create(
    model=config.model,
    messages=[{"role": "user", "content": prompt}],
    response_format={"type": "json_object"},
    timeout=60.0,
)
```

### `coder.py`
- `build_prompt(interview, codebook)` — injects dimension definitions and scoring scale into a template string stored in `codebook.yaml`
- `validate_output(raw)` — direct `json.loads` → Pydantic parse; no regex extraction needed because `json_object` mode guarantees valid JSON from the LLM
- Returns a typed `CodingResult` or `FailedCoding` (never crashes the loop)
- Only remaining failure modes: Pydantic field mismatch (wrong keys/types) or score out of configured scale range — both caught and logged

### `scorer.py`
- Pure functions — no I/O
- `compute_overall(dimension_scores, weights) -> float`
- Normalises weights to sum to 1 before applying

### `analytics.py`
- One function per chart, each returns a `plotly.Figure`
- All accept plain dicts/lists — no Streamlit dependencies
- Charts: score distribution, dimension bar, radar, theme frequency, evidence frequency, participant ranking, correlation heatmap

### `exporter.py`
- `to_csv`, `to_excel`, `to_json`, `to_pdf`
- Each returns `bytes` — caller passes to `st.download_button`
- PDF uses `reportlab`; if it fails, falls back to text export with a warning
- Excel export is multi-sheet (see **Excel Export Spec** below)

---

## Config Schema (`default_codebook.yaml`)

```yaml
version: "1.0"
scale: 5                          # 5 | 10 | 100

dimensions:
  - id: financial_precarity
    label: Financial Precarity
    weight: 20
    description: >
      Covers income instability, financial abuse, inability to meet basic needs.

prompt_template: |
  You are a qualitative research assistant...
  Codebook: {codebook_json}
  Interview: {interview_json}
  Return JSON only. Schema: {schema_json}
```

---

## LLM Output Validation (Pydantic)

```python
class DimensionScore(BaseModel):
    score: int                  # validated against configured scale
    confidence: float           # 0.0–1.0
    evidence: list[str]         # min 1 item
    reason: str

class CodingResult(BaseModel):
    participant: str
    dimensions: dict[str, DimensionScore]
    model: str
    prompt_version: str
    timestamp: str
```

Validation runs before anything is stored in session state. A failed parse logs the raw LLM output to `data/failed/<participant_id>.txt` for debugging and marks that participant as `status: "failed"` in the UI.

---

## Error Handling Strategy

| Layer | What can go wrong | How it's handled |
|---|---|---|
| ZIP upload | Corrupt ZIP, wrong format | `st.error` + stop |
| DOCX parse | Unreadable file | Skip file, show warning |
| LLM call | Rate limit, timeout, bad key | Retry 3×, then mark participant failed |
| Pydantic validation | Wrong keys, out-of-range score | Log raw JSON, mark failed, continue loop |
| Score calc | Division by zero on weights | Normalise weights before use |
| Export | reportlab crash | Fall back to plain text PDF |

The run loop **never crashes the app**. Failed participants show a red badge and can be re-run individually.

---

## Page Flow

```
1_Upload        → parse transcripts → store in session state
2_Run_Analysis  → foreach transcript: code → score → store; progress bar
3_Study_Dashboard  ← reads scores + coding_results
4_Participant_View ← reads single participant's data; editable scores
5_Question_Analysis← reads transcripts + coding_results
6_Search           ← reads raw transcripts
7_Configuration    → writes codebook + llm_config to session state; re-run clears results
```

---

## Persistence (optional, simple)

On completing a run, `persistence.py` serialises `session_state` to `data/<timestamp>_<study_name>.json`. Researchers can reload a prior session from the Upload page without re-running the LLM. This costs nothing and prevents losing results on accidental page refresh.

---

## Excel Export Spec

Single sheet, one row per participant. Each dimension expands into three columns: score, evidence, and reasoning. SPSS-ready out of the box.

---

### Column Layout

| Column | Type | Notes |
|---|---|---|
| participant_id | str | e.g. `P1`, `P11` |
| overall_score | Float64 | Weighted aggregate |
| financial_score | Int64 | |
| financial_evidence | str | Multiple quotes joined with ` \| ` |
| financial_reasoning | str | AI-generated rationale |
| employment_score | Int64 | |
| employment_evidence | str | |
| employment_reasoning | str | |
| housing_score | Int64 | |
| housing_evidence | str | |
| housing_reasoning | str | |
| institutional_score | Int64 | |
| institutional_evidence | str | |
| institutional_reasoning | str | |
| psychological_score | Int64 | |
| psychological_evidence | str | |
| psychological_reasoning | str | |
| social_score | Int64 | |
| social_evidence | str | |
| social_reasoning | str | |

Column order is always: `participant_id` → `overall_score` → then each dimension in the same order as the codebook, with `_score` / `_evidence` / `_reasoning` grouped together.

---

### SPSS Compatibility Rules

| Rule | How it's enforced |
|---|---|
| Column names `snake_case`, ≤ 64 chars, no spaces | Enforced; dynamic dimension IDs sanitised with `re.sub(r'[^a-z0-9_]', '_', id)` |
| Numeric columns purely numeric | `Int64` / `Float64` nullable dtypes — `None` stays `pd.NA`, never becomes a string |
| No mixed types in a column | Evidence and reasoning default to `""` (empty string) for failed participants, not `None` |
| One header row, no merged cells, no formulas | Enforced |
| Sheet name ≤ 31 chars, no spaces | Sheet named `Participants` |

---

### Implementation notes for `to_excel()`

```python
rows = []
for pid, result in session_state["coding_results"].items():
    row = {"participant_id": pid, "overall_score": session_state["scores"][pid].overall}
    for dim in codebook.dimensions:
        d = result.dimensions.get(dim.id)
        row[f"{dim.id}_score"]     = d.score if d else pd.NA
        row[f"{dim.id}_evidence"]  = " | ".join(d.evidence) if d else ""
        row[f"{dim.id}_reasoning"] = d.reason if d else ""
    rows.append(row)

df = pd.DataFrame(rows)
# enforce numeric dtypes
score_cols = [c for c in df.columns if c.endswith("_score")]
df[score_cols] = df[score_cols].astype("Int64")
df["overall_score"] = df["overall_score"].astype("Float64")

with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    df.to_excel(writer, sheet_name="Participants", index=False)
    ws = writer.sheets["Participants"]
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = min(
            max(len(str(c.value or "")) for c in col) + 2, 60
        )
```

---

## Dependencies (`requirements.txt`)

```
streamlit
python-docx
openai
pydantic
pyyaml
plotly
pandas
numpy
openpyxl
reportlab
```

No database. No task queue. No Docker required to run locally.
