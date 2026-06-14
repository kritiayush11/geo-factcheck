# GEO Fact-Check — Truth Layer

A deployed fact-checking web app that reads PDFs, extracts specific claims, and cross-references them against live web data using Claude AI with real-time web search.

## Live Demo

Deploy to Streamlit Cloud and visit your app URL.
https://geo-factcheck-yvjprvsvdktsb5pua8xnc8.streamlit.app

---

## What it does

1. **Upload** any PDF — marketing decks, reports, whitepapers, research
2. **Extract** — Claude identifies specific, verifiable claims (stats, dates, financial figures, technical numbers)
3. **Verify** — Each claim is searched against live web data in real time
4. **Report** — Claims are flagged as:
   - ✓ **Verified** — matches current data from reliable sources
   - ⚠ **Inaccurate** — outdated or contains wrong numbers (with correct fact provided)
   - ✕ **False** — fabricated or contradicted by evidence (with correct fact provided)
   - ? **Unverifiable** — insufficient public data to confirm or deny

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| AI model | Claude claude-sonnet-4-6 (Anthropic) |
| Live web verification | Claude's `web_search_20250305` tool |
| PDF parsing | PyPDF2 |
| Deployment | Streamlit Cloud |

---

## Local Setup

```bash
git clone https://github.com/YOUR_USERNAME/geo-factcheck
cd geo-factcheck
pip install -r requirements.txt
streamlit run app.py
```

You will be prompted for your Anthropic API key in the sidebar.

---

## Deploy to Streamlit Cloud (Free)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set main file: `app.py`
5. Click **Deploy**

No secrets needed in Streamlit Cloud — users enter their own API key via the sidebar.

---

## Deploy to Render (Free tier)

1. Create a `render.yaml` in the root:
```yaml
services:
  - type: web
    name: geo-factcheck
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```
2. Connect your GitHub repo on [render.com](https://render.com)

---

## Requirements

```
streamlit==1.35.0
anthropic==0.28.0
pypdf2==3.0.1
requests==2.31.0
python-dotenv==1.0.0
```

---

## Evaluation / Trap Document Test

This app is specifically designed to catch:
- Outdated statistics (e.g., "global AI market is $50B" when it is now much larger)
- Fabricated figures (e.g., "90% of Fortune 500 companies use X" with no source)
- Wrong dates (e.g., incorrect product launch years)
- Inflated/deflated percentages
- False attribution of research

Each flagged claim includes the **correct fact** sourced from live web search, making it easy to identify what is wrong and what the truth is.

---

## Architecture

```
PDF Upload
    ↓
PyPDF2 text extraction
    ↓
Claude claude-sonnet-4-6 (claim extraction prompt)
    ↓
web_search_20250305 tool (live verification per claim)
    ↓
Structured JSON verdicts
    ↓
Streamlit UI with filtering + download
```

---

## Project Structure

```
geo-factcheck/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
├── README.md           # This file
└── .gitignore
```

---

Built for the GEO platform assignment — automated fact-checking as a "Truth Layer" for marketing and research content.
