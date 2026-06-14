import streamlit as st
import anthropic
import json
import time
import io
import base64
from pathlib import Path

st.set_page_config(
    page_title="GEO Fact-Check — Truth Layer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 600;
        color: #d0d0df;
        margin-bottom: 0.25rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    .claim-card {
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
        background: #ffffff;
    }
    .verdict-verified {
        background: #f0fdf4;
        border-left: 4px solid #16a34a;
        border-radius: 0 8px 8px 0;
    }
    .verdict-inaccurate {
        background: #fffbeb;
        border-left: 4px solid #d97706;
        border-radius: 0 8px 8px 0;
    }
    .verdict-false {
        background: #fef2f2;
        border-left: 4px solid #dc2626;
        border-radius: 0 8px 8px 0;
    }
    .verdict-unverifiable {
        background: #f9fafb;
        border-left: 4px solid #9ca3af;
        border-radius: 0 8px 8px 0;
    }
    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 99px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.03em;
    }
    .badge-verified { background: #dcfce7; color: #15803d; }
    .badge-inaccurate { background: #fef3c7; color: #b45309; }
    .badge-false { background: #fee2e2; color: #b91c1c; }
    .badge-unverifiable { background: #f3f4f6; color: #6b7280; }
    .stat-box {
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        background: #f9fafb;
    }
    .stat-number { font-size: 2rem; font-weight: 700; }
    .stat-label { font-size: 0.8rem; color: #6b7280; margin-top: 2px; }
    .claim-text { font-size: 1rem; font-weight: 500; color: #111827; margin-bottom: 0.5rem; }
    .finding-text { font-size: 0.9rem; color: #374151; line-height: 1.6; }
    .source-text { font-size: 0.8rem; color: #6b7280; margin-top: 0.5rem; }
    .correct-fact { font-size: 0.9rem; color: #166534; background: #dcfce7; padding: 6px 10px; border-radius: 6px; margin-top: 8px; }
    div[data-testid="stFileUploader"] {
        border: 2px dashed #d1d5db;
        border-radius: 12px;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF using PyPDF2."""
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        st.error(f"PDF extraction error: {e}")
        return ""


def extract_and_verify_claims(pdf_text: str, api_key: str) -> list:
    """
    Uses Claude with web_search tool to extract claims and verify them live.
    Returns a list of verified claim objects.
    """
    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = """You are a professional fact-checking AI. Your job is to:
1. Extract specific, verifiable claims from the provided document text (focus on statistics, dates, financial figures, technical numbers, percentages, market sizes, research findings)
2. For each claim, use your web_search tool to find current, accurate information
3. Verify whether each claim is accurate based on live data

Extract 6-12 of the most specific and verifiable claims. Skip vague statements.

After verifying each claim via web search, return your results as a JSON array with this exact structure:
[
  {
    "claim": "The exact claim text from the document",
    "category": "statistic|date|financial|technical|research",
    "verdict": "Verified|Inaccurate|False|Unverifiable",
    "finding": "Your detailed explanation of what you found",
    "correct_fact": "The accurate fact if the claim is wrong (null if verified)",
    "source": "The source you found this information from",
    "confidence": "High|Medium|Low"
  }
]

Verdict definitions:
- Verified: The claim matches current data from reliable sources
- Inaccurate: The claim is outdated or contains wrong numbers (provide correct fact)
- False: The claim is factually wrong or fabricated (provide correct fact)
- Unverifiable: Cannot find reliable data to confirm or deny

Return ONLY the JSON array, no other text."""

    user_message = f"""Please extract all specific, verifiable claims from this document and fact-check each one using web search:

---DOCUMENT TEXT---
{pdf_text[:8000]}
---END DOCUMENT---

Extract claims, search the web for each, and return the JSON array of results."""

    with st.spinner("🔍 Extracting claims and searching the web for verification..."):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4000,
                system=system_prompt,
                tools=[{
                    "type": "web_search_20250305",
                    "name": "web_search"
                }],
                messages=[{"role": "user", "content": user_message}]
            )

            full_text = ""
            for block in response.content:
                if block.type == "text":
                    full_text += block.text

            if not full_text.strip():
                response2 = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=4000,
                    system=system_prompt,
                    tools=[{
                        "type": "web_search_20250305",
                        "name": "web_search"
                    }],
                    messages=[
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": response.content},
                        {"role": "user", "content": "Now provide the final JSON array of all verified claims."}
                    ]
                )
                for block in response2.content:
                    if block.type == "text":
                        full_text += block.text

            clean = full_text.strip()
            if "```json" in clean:
                clean = clean.split("```json")[1].split("```")[0].strip()
            elif "```" in clean:
                clean = clean.split("```")[1].split("```")[0].strip()

            start = clean.find("[")
            end = clean.rfind("]") + 1
            if start != -1 and end > start:
                clean = clean[start:end]

            claims = json.loads(clean)
            return claims

        except json.JSONDecodeError as e:
            st.error(f"Could not parse verification results: {e}")
            return []
        except anthropic.APIStatusError as e:
            st.error(f"API error: {e.message}")
            return []
        except Exception as e:
            st.error(f"Verification error: {e}")
            return []


def render_verdict_badge(verdict: str) -> str:
    v = verdict.lower()
    if v == "verified":
        return '<span class="badge badge-verified">✓ Verified</span>'
    elif v == "inaccurate":
        return '<span class="badge badge-inaccurate">⚠ Inaccurate</span>'
    elif v == "false":
        return '<span class="badge badge-false">✕ False</span>'
    else:
        return '<span class="badge badge-unverifiable">? Unverifiable</span>'


def render_claim_card(claim: dict, index: int):
    verdict = claim.get("verdict", "Unverifiable").lower()
    card_class = f"verdict-{verdict}" if verdict in ["verified", "inaccurate", "false"] else "verdict-unverifiable"
    badge_html = render_verdict_badge(claim.get("verdict", "Unverifiable"))
    category = claim.get("category", "claim").upper()
    correct_fact_html = ""
    if claim.get("correct_fact"):
        correct_fact_html = f'<div class="correct-fact">✦ Correct fact: {claim["correct_fact"]}</div>'

    confidence = claim.get("confidence", "")
    conf_color = {"High": "#15803d", "Medium": "#b45309", "Low": "#b91c1c"}.get(confidence, "#6b7280")

    st.markdown(f"""
    <div class="claim-card {card_class}">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            {badge_html}
            <span style="font-size:0.72rem;color:#9ca3af;font-weight:600;letter-spacing:0.05em;">{category}</span>
            <span style="font-size:0.72rem;color:{conf_color};margin-left:auto;">Confidence: {confidence}</span>
        </div>
        <div class="claim-text">"{claim.get('claim', '')}"</div>
        <div class="finding-text">{claim.get('finding', '')}</div>
        {correct_fact_html}
        <div class="source-text">Source: {claim.get('source', 'Web search')}</div>
    </div>
    """, unsafe_allow_html=True)


def main():
    st.markdown('<div class="main-header">🔍 GEO Fact-Check</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Truth Layer — Upload a PDF to automatically verify claims against live web data</div>', unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### Configuration")
        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            placeholder="sk-ant-...",
            help="Get your key at console.anthropic.com"
        )
        st.markdown("---")
        st.markdown("#### How it works")
        st.markdown("""
1. **Upload** any PDF document
2. **Extract** — Claude identifies specific claims (stats, dates, figures)
3. **Verify** — Each claim is cross-referenced with live web search
4. **Report** — Claims flagged as Verified, Inaccurate, or False
        """)
        st.markdown("---")
        st.markdown("#### Verdict guide")
        st.markdown("✓ **Verified** — matches live data")
        st.markdown("⚠ **Inaccurate** — outdated or wrong number")
        st.markdown("✕ **False** — fabricated or no evidence")
        st.markdown("? **Unverifiable** — insufficient data")

    uploaded_file = st.file_uploader(
        "Drop your PDF here",
        type=["pdf"],
        help="Upload any document containing factual claims — marketing content, reports, articles"
    )

    if uploaded_file and not api_key:
        st.warning("Please enter your Anthropic API Key in the sidebar to proceed.")
        return

    if uploaded_file and api_key:
        pdf_bytes = uploaded_file.read()
        file_size = len(pdf_bytes) / 1024

        col1, col2 = st.columns([3, 1])
        with col1:
            st.success(f"📄 **{uploaded_file.name}** ({file_size:.1f} KB) — ready to verify")
        with col2:
            run_btn = st.button("Run Fact-Check →", type="primary", use_container_width=True)

        if run_btn:
            with st.spinner("Extracting text from PDF..."):
                pdf_text = extract_text_from_pdf(pdf_bytes)

            if not pdf_text:
                st.error("Could not extract text from this PDF. Please try a text-based PDF.")
                return

            with st.expander("View extracted text", expanded=False):
                st.text_area("Raw text", pdf_text[:3000] + ("..." if len(pdf_text) > 3000 else ""), height=200)

            progress_bar = st.progress(0, text="Starting verification pipeline...")
            time.sleep(0.3)
            progress_bar.progress(20, text="Sending to Claude for claim extraction...")

            claims = extract_and_verify_claims(pdf_text, api_key)
            progress_bar.progress(100, text="Verification complete!")
            time.sleep(0.3)
            progress_bar.empty()

            if not claims:
                st.warning("No verifiable claims were found or the API returned an unexpected result. Try a document with specific statistics or figures.")
                return

            total = len(claims)
            verified = sum(1 for c in claims if c.get("verdict", "").lower() == "verified")
            inaccurate = sum(1 for c in claims if c.get("verdict", "").lower() == "inaccurate")
            false_count = sum(1 for c in claims if c.get("verdict", "").lower() == "false")
            unverifiable = total - verified - inaccurate - false_count

            st.markdown("---")
            st.markdown("### Verification Summary")
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.markdown(f'<div class="stat-box"><div class="stat-number" style="color:#374151">{total}</div><div class="stat-label">Claims found</div></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="stat-box"><div class="stat-number" style="color:#16a34a">{verified}</div><div class="stat-label">Verified</div></div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="stat-box"><div class="stat-number" style="color:#d97706">{inaccurate}</div><div class="stat-label">Inaccurate</div></div>', unsafe_allow_html=True)
            with c4:
                st.markdown(f'<div class="stat-box"><div class="stat-number" style="color:#dc2626">{false_count}</div><div class="stat-label">False</div></div>', unsafe_allow_html=True)
            with c5:
                accuracy = round((verified / total) * 100) if total > 0 else 0
                color = "#16a34a" if accuracy >= 70 else "#d97706" if accuracy >= 40 else "#dc2626"
                st.markdown(f'<div class="stat-box"><div class="stat-number" style="color:{color}">{accuracy}%</div><div class="stat-label">Accuracy score</div></div>', unsafe_allow_html=True)

            if false_count > 0 or inaccurate > 0:
                st.error(f"⚠ This document contains {false_count + inaccurate} problematic claim(s) — review flagged items below.")
            else:
                st.success("✓ All verifiable claims appear to be accurate based on current web data.")

            st.markdown("---")
            st.markdown("### Claim-by-Claim Results")

            filter_col1, filter_col2 = st.columns([2, 3])
            with filter_col1:
                filter_verdict = st.selectbox(
                    "Filter by verdict",
                    ["All", "Verified", "Inaccurate", "False", "Unverifiable"]
                )

            filtered = claims if filter_verdict == "All" else [
                c for c in claims if c.get("verdict", "").lower() == filter_verdict.lower()
            ]

            if not filtered:
                st.info(f"No claims with verdict '{filter_verdict}'.")
            else:
                for i, claim in enumerate(filtered):
                    render_claim_card(claim, i)

            st.markdown("---")
            json_str = json.dumps(claims, indent=2)
            st.download_button(
                label="Download full report (JSON)",
                data=json_str,
                file_name=f"factcheck_{uploaded_file.name.replace('.pdf','')}.json",
                mime="application/json"
            )

    else:
        st.markdown("""
        <div style="border:2px dashed #e5e7eb;border-radius:12px;padding:3rem;text-align:center;color:#9ca3af;margin-top:1rem;">
            <div style="font-size:3rem;margin-bottom:1rem;">📄</div>
            <div style="font-size:1.1rem;font-weight:500;color:#6b7280;">Upload a PDF to begin fact-checking</div>
            <div style="font-size:0.85rem;margin-top:0.5rem;">Marketing decks, reports, whitepapers, articles — anything with stats or figures</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center;margin-top:3rem;color:#d1d5db;font-size:0.75rem;">
        GEO Fact-Check + Web Search · Built for accuracy
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
