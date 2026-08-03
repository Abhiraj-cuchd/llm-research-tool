# Deployment Runbook — AI-Assisted Qualitative Research Platform

Target: Streamlit Community Cloud (free tier)
Result: a public URL your supervisor opens in any browser — no setup required on their end.

---

## Prerequisites (one-time)

- [ ] GitHub account
- [ ] Streamlit Community Cloud account — sign up at https://share.streamlit.io using your GitHub account
- [ ] DeepSeek API key

---

## Step 1 — Prepare the Repo

### 1.1 — Create a `secrets.toml` reference file (do NOT commit real values)

Create `.streamlit/secrets.toml.example` in the repo:

```toml
DEEPSEEK_API_KEY = "your_key_here"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
```

Add the real file to `.gitignore`:
```
.streamlit/secrets.toml
```

### 1.2 — Ensure these files exist in the repo root

| File | Purpose |
|---|---|
| `requirements.txt` | Python dependencies |
| `app.py` | Streamlit entry point |
| `config/default_codebook.yaml` | Default codebook |
| `.streamlit/config.toml` | Optional UI config (see below) |

### 1.3 — Create `.streamlit/config.toml`

```toml
[server]
maxUploadSize = 200

[theme]
base = "light"
```

`maxUploadSize = 200` raises the upload limit to 200 MB — necessary for large ZIP files with many DOCX transcripts.

### 1.4 — Create `packages.txt` in repo root

Required if `reportlab` needs system libraries on the cloud runner:

```
libpango-1.0-0
libcairo2
```

### 1.5 — Update `app.py` to read secrets from `st.secrets` with `.env` fallback

```python
import os
import streamlit as st

def get_secret(key: str) -> str:
    # Streamlit Cloud injects secrets via st.secrets
    # Local dev falls back to environment variable / .env
    if key in st.secrets:
        return st.secrets[key]
    return os.getenv(key, "")
```

Use `get_secret("DEEPSEEK_API_KEY")` everywhere instead of `os.getenv(...)` directly.

### 1.6 — Remove disk-based persistence for PoC

Streamlit Cloud runs on an ephemeral filesystem — files written during a session are lost on restart or redeploy. 

- Remove auto-save to `data/<session>.json`
- Add a banner on the Study Dashboard page:

```python
st.info("Session data lives in memory. Export your results before closing the browser.")
```

- Keep the JSON download button so the researcher can manually save and reload if needed.

### 1.7 — Ensure `data/failed/` directory creation is in-code, not assumed

```python
import pathlib
pathlib.Path("data/failed").mkdir(parents=True, exist_ok=True)
```

Call this once at app startup in `app.py` — do not rely on `.gitkeep` files on cloud.

---

## Step 2 — Push to GitHub

```bash
git init                          # if not already a git repo
git add .
git commit -m "initial commit"
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

Repo can be **private** — Streamlit Cloud supports private repos.

---

## Step 3 — Deploy on Streamlit Community Cloud

1. Go to https://share.streamlit.io
2. Click **"New app"**
3. Select:
   - **Repository**: `<your-username>/<repo-name>`
   - **Branch**: `main`
   - **Main file path**: `app.py`
4. Click **"Advanced settings"**
5. Under **Secrets**, paste:

```toml
DEEPSEEK_API_KEY = "sk-your-actual-key"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
```

6. Click **"Deploy"**

Build takes ~2–4 minutes on first deploy (installs all dependencies).

---

## Step 4 — Verify Deployment

- [ ] App loads at the generated URL without errors
- [ ] Upload page renders with file uploader
- [ ] Upload a test ZIP (even 1–2 DOCX files) and confirm parsing works
- [ ] Run Analysis with the real DeepSeek key — confirm at least one participant codes successfully
- [ ] Export Excel — open in spreadsheet tool, confirm columns and types are correct
- [ ] Check the URL works in an incognito window (no login required by default)

---

## Step 5 — Share with Supervisor

Send the URL. Nothing else needed on their end.

If you want to restrict access so only your supervisor can use it:

1. In Streamlit Cloud dashboard → your app → **Settings** → **Sharing**
2. Set to **"Only specific people"**
3. Add your supervisor's email address

They will be prompted to log in with Google or GitHub once — no password setup needed.

---

## Redeploying After Code Changes

```bash
git add .
git commit -m "your change description"
git push origin main
```

Streamlit Cloud auto-detects the push and redeploys within ~1 minute. The app shows a "Rerunning..." spinner during the update. No manual steps needed.

---

## Updating the API Key

1. Streamlit Cloud dashboard → your app → **Settings** → **Secrets**
2. Edit the `DEEPSEEK_API_KEY` value
3. Save — app restarts automatically with the new key

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Build fails with `ModuleNotFoundError` | Package missing from `requirements.txt` | Add it and push |
| Build fails with system library error | Missing `packages.txt` entry | Add the library name and push |
| `st.secrets` key not found error | Secret not added in dashboard | Add it under Settings → Secrets |
| Upload fails with "file too large" | `maxUploadSize` not set | Confirm `.streamlit/config.toml` is committed |
| App crashes on ZIP upload | `data/failed/` dir not created | Confirm `mkdir` call is in `app.py` startup |
| Blank page after deploy | `app.py` import error | Check logs in Streamlit Cloud dashboard → "Manage app" → logs tab |
| LLM calls time out | DeepSeek latency on cloud | Increase timeout in `llm_client.py` to 90s; acceptable for PoC |

---

## Resource Limits (Streamlit Community Cloud Free Tier)

| Resource | Limit |
|---|---|
| Apps | 3 public or 1 private |
| Memory | ~1 GB RAM |
| CPU | Shared |
| Storage | Ephemeral — wiped on restart |
| Uptime | Sleeps after ~7 days of inactivity; wakes on next visit |

For a PoC with 14 interview transcripts, these limits are well within range. Memory usage will be under 200 MB.

---

## Local Development (for you, not your supervisor)

```bash
# clone the repo
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>

# create local secrets file (gitignored)
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# fill in your real API key in secrets.toml

# install dependencies
pip install -r requirements.txt

# run
streamlit run app.py
```
