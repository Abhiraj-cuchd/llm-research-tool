# Implementation Tasklist — AI-Assisted Qualitative Research Platform

Phases are sequential. Within a phase, tasks can be done in any order unless marked `→ depends on`.

---

## Phase 1 — Project Scaffold

Goal: bare repo that runs `streamlit run app.py` without errors.

- [ ] Create directory structure: `modules/`, `pages/`, `utils/`, `config/`, `data/failed/`
- [ ] Create `requirements.txt` with pinned versions:
  ```
  streamlit==1.35.0
  python-docx==1.1.2
  openai==1.30.0
  pydantic==2.7.0
  pyyaml==6.0.1
  plotly==5.22.0
  pandas==2.2.2
  numpy==1.26.4
  openpyxl==3.1.2
  reportlab==4.2.0
  ```
- [ ] Create `.env.example`:
  ```
  DEEPSEEK_API_KEY=your_key_here
  DEEPSEEK_BASE_URL=https://api.deepseek.com
  DEEPSEEK_MODEL=deepseek-chat
  ```
- [ ] Create `.gitignore` — exclude `data/`, `.env`, `__pycache__/`, `*.pyc`
- [ ] Create `app.py` — sets page config, loads `.env`, initialises session state, renders sidebar nav
- [ ] Create `utils/state.py` — `init_session_state()` that sets all keys to defaults if not already present; safe getter `get_state(key, default)`
- [ ] Verify: `streamlit run app.py` loads with empty sidebar and no errors

---

## Phase 2 — Config System

Goal: codebook loads from YAML; UI can display dimension names dynamically.

- [ ] Create `config/default_codebook.yaml` with all 6 dimensions, weights, scale=5, prompt template placeholder
- [ ] Create `utils/validators.py` — Pydantic models:
  - `DimensionConfig(id, label, weight, description)`
  - `Codebook(version, scale, dimensions, prompt_template)`
  - `LLMConfig(api_key, base_url, model)`
  - `DimensionScore(score, confidence, evidence, reason)`
  - `CodingResult(participant, dimensions, model, prompt_version, timestamp)`
  - `FailedCoding(participant, error, raw_output)`
  - `ParticipantScore(participant, dimension_scores, overall)`
- [ ] Create `modules/config_loader.py` — `load_codebook(path) -> Codebook`; validates against Pydantic on load; raises `ConfigError` with clear message on schema mismatch
- [ ] Load codebook into `session_state["codebook"]` on app start
- [ ] Verify: modify YAML, confirm Pydantic catches missing fields with a readable error

---

## Phase 3 — Upload & Parsing

Goal: researcher uploads ZIP → transcripts appear in session state as structured JSON.

- [ ] Create `modules/uploader.py`:
  - `extract_zip(file_bytes: bytes) -> list[tuple[str, bytes]]`
  - Validates ZIP is not empty, contains at least one `.docx`
  - Skips non-`.docx` files silently (logs warning)
  - Raises `UploadError` on corrupt ZIP
- [ ] Create `modules/parser.py`:
  - `parse_docx(filename: str, docx_bytes: bytes) -> InterviewJSON`
  - Reads via `io.BytesIO` — no disk write
  - Speaker detection: tries patterns in order — `Q:` / `A:`, `Interviewer:` / `Participant:`, `[Q]` / `[A]`, bold paragraph as question
  - Falls back to alternating paragraphs if no pattern matches (first para = question)
  - Derives `participant_id` from filename stem (`P11.docx` → `P11`)
  - Returns `InterviewJSON(participant, questions=[{question, answer}])`
  - Raises `ParseError` with filename in message on failure
- [ ] Create `pages/1_Upload.py`:
  - `st.file_uploader` accepting `.zip` only
  - On upload: call `extract_zip` → loop `parse_docx` per file
  - Progress bar during parsing
  - Show success table: participant ID, question count, status (`parsed` / `failed`)
  - Failed files show inline warning with error message — do not block other files
  - Store results in `session_state["transcripts"]`
  - "Clear & Re-upload" button that wipes session state and reruns
- [ ] Verify: upload a ZIP with 14 DOCX files, confirm all parse correctly and table renders

---

## Phase 4 — LLM Client & Coding Engine

Goal: given a parsed transcript + codebook, LLM returns a validated `CodingResult`.

- [ ] Create `modules/llm_client.py`:
  - `call(prompt: str, config: LLMConfig) -> str | LLMError`
  - `openai.OpenAI(api_key=config.api_key, base_url=config.base_url)`
  - Always pass `response_format={"type": "json_object"}` — guarantees valid JSON back, no prose fallback needed
  - Retry loop: max 3 attempts, backoff 2s → 4s → 8s
  - Catches `openai.RateLimitError`, `openai.APITimeoutError`, `openai.APIConnectionError`
  - Hard timeout: `timeout=60.0` in the `create()` call
  - Returns `LLMError(message, raw_exception)` on all failures — never raises
- [ ] Update `config/default_codebook.yaml` with real prompt template:
  - Instructs LLM to return JSON only, no prose
  - Includes codebook dimension definitions inline
  - Specifies exact output schema with field names and types
  - Includes instruction: "If a dimension has no evidence in the transcript, set score to 0 and evidence to an empty list"
- [ ] Create `modules/coder.py`:
  - `build_prompt(interview: InterviewJSON, codebook: Codebook) -> str`
    - Serialises codebook dimensions to JSON and injects into template
    - Serialises interview Q&A pairs and injects
    - Injects scoring scale
  - `validate_coding(raw: str, participant: str, codebook: Codebook) -> CodingResult | FailedCoding`
    - `json.loads(raw)` directly — no regex needed, `json_object` mode guarantees valid JSON
    - Pydantic parse → score range validation (score must be within configured scale)
    - On failure: writes raw output to `data/failed/<participant>.txt`, returns `FailedCoding`
  - `code_interview(interview: InterviewJSON, codebook: Codebook, llm_config: LLMConfig) -> CodingResult | FailedCoding`
    - Orchestrates: `build_prompt` → `llm_client.call` → `validate_coding`
- [ ] Create `modules/scorer.py`:
  - `normalise_weights(dimensions: list[DimensionConfig]) -> dict[str, float]`
  - `compute_scores(result: CodingResult, codebook: Codebook) -> ParticipantScore`
  - `rank_participants(scores: dict[str, ParticipantScore]) -> list[tuple[str, float]]`
  - `dimension_averages(scores: dict[str, ParticipantScore]) -> dict[str, float]`
- [ ] Unit test `coder.py` with a mocked LLM response and a malformed response — confirm both paths work
- [ ] Verify: call `code_interview` manually in a script with one real transcript

---

## Phase 5 — Run Analysis Page

Goal: researcher clicks Run → all participants are coded sequentially with live progress.

- [ ] Create `pages/2_Run_Analysis.py`:
  - Guard: redirect to Upload page if `session_state["transcripts"]` is empty
  - LLM config form: API key input (`type="password"`), base URL (default `https://api.deepseek.com`), model (default `deepseek-chat`) — pre-fill from `.env` if set
  - "Run Analysis" button
  - On run:
    - Validate API key is not empty
    - `st.progress` bar tracking overall completion (e.g. `3 / 14 participants`)
    - Per-participant loading spinner using `st.spinner` with a **randomly selected message** from the research phrases array on each call (see below)
    - Loop through transcripts sequentially
    - Store each result immediately into `session_state["coding_results"]` and `session_state["scores"]` as it completes — so a mid-run crash doesn't lose completed work
    - Show per-participant result inline: green tick (success) / red badge (failed) with error reason
  - "Re-run Failed" button appears after run if any participants failed — re-runs only the failed ones
  - "Re-run All" button to wipe results and start fresh
  - Stores `run_metadata` (model, timestamp, prompt version, codebook version) in session state

- [ ] Add `utils/spinner_messages.py` — single constant list of 25 research phrases:

  ```python
  RESEARCH_PHRASES = [
      "Traversing the landscape of lived experience...",
      "Surfacing patterns beneath the narrative...",
      "Weighing the evidence against the codebook...",
      "Listening closely to what wasn't said...",
      "Mapping precarity across dimensions...",
      "Tracing threads of financial vulnerability...",
      "Reading between the lines of the transcript...",
      "Grounding theory in participant voice...",
      "Interrogating the silences in the data...",
      "Constructing meaning from raw testimony...",
      "Cross-referencing themes with the literature...",
      "Calibrating confidence against the evidence...",
      "Attending to the texture of the response...",
      "Locating this voice within the broader study...",
      "Parsing the architecture of precarity...",
      "Holding the data with interpretive care...",
      "Extracting signal from lived complexity...",
      "Situating the narrative in structural context...",
      "Weighing intersecting dimensions of hardship...",
      "Letting the transcript speak for itself...",
      "Distilling experience into structured insight...",
      "Following the evidence wherever it leads...",
      "Coding with fidelity to the participant's words...",
      "Drawing the contours of this individual's story...",
      "Synthesising vulnerability into meaning...",
  ]
  ```

  Usage in the run loop:
  ```python
  import random
  from utils.spinner_messages import RESEARCH_PHRASES

  for pid, interview in transcripts.items():
      msg = random.choice(RESEARCH_PHRASES)
      with st.spinner(f"{msg}"):
          result = code_interview(interview, codebook, llm_config)
      # update progress bar and result list after spinner exits
  ```
- [ ] Auto-save to `data/<timestamp>_session.json` on run completion via `utils/persistence.py`
- [ ] Verify: run against real transcripts, confirm progress bar moves and results populate

---

## Phase 6 — Study Dashboard

Goal: study-level KPIs and charts render correctly from session state.

- [ ] Create `modules/analytics.py` — all functions return `plotly.Figure`, no `st.*` calls:
  - `score_distribution_histogram(scores)` — overall score spread
  - `dimension_bar_chart(dim_averages)` — avg score per dimension
  - `participant_ranking_chart(ranked)` — horizontal bar, sorted by overall score
  - `theme_frequency_chart(coding_results)` — top N evidence quotes by occurrence
  - `radar_chart(participant_score)` — single participant radar
- [ ] Create `pages/3_Study_Dashboard.py`:
  - Guard: redirect if no scores in session state
  - KPI row (use `st.metric`):
    - Total Participants
    - Avg Overall Score
    - Highest Dimension (name + avg score)
    - Lowest Dimension (name + avg score)
    - Avg AI Confidence
  - Score distribution histogram
  - Dimension averages bar chart
  - Participant ranking chart
  - Evidence frequency table (top 20 quotes, sortable)
- [ ] Verify: all charts render, no KeyError on missing dimensions

---

## Phase 7 — Individual Participant View

Goal: researcher can drill into any participant and optionally edit scores.

- [ ] Create `pages/4_Participant_View.py`:
  - Guard: redirect if no scores
  - Participant selector dropdown (sorted by ID)
  - Top row: overall score badge + radar chart
  - Dimension cards in a 2-column grid, each showing:
    - Score (editable `st.number_input`, min=0, max=scale)
    - Confidence badge
    - Evidence quotes (displayed as blockquotes)
    - Reasoning text
  - "Save Edits" button — updates `session_state["scores"]` and `session_state["coding_results"]` with edited values; marks result as `human_reviewed: true`
  - AI-generated participant summary (pre-computed during coding run, stored in `CodingResult`)
- [ ] Add `summary` field to `CodingResult` Pydantic model
- [ ] Add summary generation to prompt template: "Also return a `summary` field: 2–3 sentence narrative of this participant's overall precarity situation"
- [ ] Verify: edit a score, save, confirm it reflects in the Study Dashboard

---

## Phase 8 — Question Analysis & Search

Goal: cross-participant question comparison and keyword search.

- [ ] Create `pages/5_Question_Analysis.py`:
  - Guard: redirect if no transcripts
  - Question selector: unique questions extracted from all transcripts, deduplicated by similarity (simple exact-match first; fuzzy fallback not needed for PoC)
  - On question select: show all participant answers in an expandable list
  - "Synthesise" button: sends all answers for that question to LLM → returns common themes + contrasting perspectives; displayed as formatted text
  - Cache synthesis result in `session_state` keyed by question text to avoid re-calling
- [ ] Create `pages/6_Search.py`:
  - Text input for keyword/phrase
  - On search: scan all transcript answers for case-insensitive match
  - Results grouped by participant, matching text highlighted using `st.markdown` with `<mark>` HTML
  - Show match count per participant
- [ ] Verify: search "financial", confirm matches highlight correctly across participants

---

## Phase 9 — Configuration Page

Goal: researcher can change codebook, weights, and LLM settings; changes propagate cleanly.

- [ ] Create `pages/7_Configuration.py`:
  - **Codebook section**: editable table (one row per dimension) — label, weight slider (0–100), description textarea
  - **Scoring scale**: radio — `5 / 10 / 100`
  - **Prompt template**: `st.text_area` showing current template, editable
  - **LLM section**: API key, base URL, model name
  - "Save Configuration" button — updates `session_state["codebook"]` and `session_state["llm_config"]`
  - Warning banner: "Changing configuration will clear existing analysis results. Save to re-run."
  - Confirm dialog before clearing results
  - "Export Config as YAML" download button — lets researcher save their codebook for reuse
  - "Import Config from YAML" uploader — loads a previously exported codebook
- [ ] Verify: change a weight, save, confirm `scorer.py` uses updated weights on next run

---

## Phase 10 — Export

Goal: one-click export produces a clean SPSS-compatible `.xlsx`.

- [ ] Create `modules/exporter.py`:
  - `build_export_df(session_state) -> pd.DataFrame`
    - One row per participant
    - Columns: `participant_id`, `overall_score`, then for each dimension: `<dim>_score`, `<dim>_evidence`, `<dim>_reasoning`
    - Column order follows codebook dimension order
    - `<dim>_evidence`: `" | ".join(evidence_list)`, empty string if no evidence
    - Score columns: `Int64` nullable dtype; `pd.NA` for failed participants
    - `overall_score`: `Float64`
    - Evidence/reasoning columns: `str`, `""` for failed participants (never `None`)
    - Column names sanitised: `re.sub(r'[^a-z0-9_]', '_', name.lower())`
  - `to_excel(df: pd.DataFrame) -> bytes`
    - Single sheet named `Participants`
    - Auto-fit column widths capped at 60
    - Returns `BytesIO` bytes
  - `to_csv(df: pd.DataFrame) -> bytes` — UTF-8 with BOM (`utf-8-sig`) for Excel compatibility
  - `to_json(session_state) -> bytes` — full session dump for reload
- [ ] Add export buttons to `pages/3_Study_Dashboard.py`:
  - `st.download_button` for Excel, CSV, JSON
  - Placed in a sidebar or expander to not clutter the dashboard
- [ ] Verify: open exported Excel in LibreOffice Calc, confirm no merged cells, all numeric columns are numeric, no `None` strings

---

## Phase 11 — Persistence & Session Reload

Goal: closing the browser and reopening does not lose results.

- [ ] Create `utils/persistence.py`:
  - `save_session(session_state, study_name: str)` — serialises to `data/<timestamp>_<study_name>.json`
    - Converts Pydantic models to dicts before serialising
  - `load_session(path: str) -> dict` — deserialises and reconstructs Pydantic models
  - `list_sessions() -> list[dict]` — returns `[{path, study_name, timestamp, participant_count}]` for display
- [ ] Add "Load Previous Session" expander to `pages/1_Upload.py`:
  - Lists saved sessions with timestamp and participant count
  - "Load" button per session — populates session state and redirects to Study Dashboard
- [ ] Auto-save after every completed coding run
- [ ] Verify: run analysis, close browser, reopen, load session, confirm dashboard renders correctly

---

## Phase 12 — Hardening & Deployment Readiness

Goal: app runs without crashes on edge cases; deployable with just an API key.

- [ ] Add `data/failed/.gitkeep` so the directory exists in the repo
- [ ] Add empty `data/.gitkeep`
- [ ] Test edge cases:
  - [ ] ZIP with one DOCX that has no speaker markers
  - [ ] DOCX with only one question-answer pair
  - [ ] LLM returns plain prose instead of JSON — confirm `FailedCoding` path works
  - [ ] LLM returns partial JSON (missing one dimension) — confirm Pydantic catches and marks failed
  - [ ] All participants fail — confirm Study Dashboard shows empty state message instead of crashing
  - [ ] Weights sum to 0 — confirm scorer handles gracefully
- [ ] Add `st.set_page_config(page_title="Research Tool", layout="wide")` to `app.py`
- [ ] Add sidebar status indicator: "X of Y participants coded" when a run is in progress or complete
- [ ] Add `.env` auto-load in `app.py` using `python-dotenv` (add to requirements) — researcher just fills `.env` and runs
- [ ] Add `run.sh`:
  ```bash
  #!/bin/bash
  pip install -r requirements.txt
  streamlit run app.py
  ```
- [ ] Final smoke test: fresh clone → fill `.env` → `bash run.sh` → upload ZIP → run analysis → export Excel → open in spreadsheet tool → confirm all columns present and typed correctly

---

## Dependency Map

```
Phase 1 (Scaffold)
    └── Phase 2 (Config)
            ├── Phase 3 (Upload & Parse)
            │       └── Phase 4 (LLM + Coding)
            │               └── Phase 5 (Run Analysis Page)
            │                       ├── Phase 6 (Study Dashboard)
            │                       │       └── Phase 10 (Export)
            │                       ├── Phase 7 (Participant View)
            │                       ├── Phase 8 (Question Analysis + Search)
            │                       └── Phase 11 (Persistence)
            └── Phase 9 (Config Page)   ← can be built in parallel with 6–8

Phase 12 (Hardening) — always last
```
