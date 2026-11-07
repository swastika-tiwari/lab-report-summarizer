import os
import tempfile

import pandas as pd
import streamlit as st

from src.analyzer import analyze
from src.checks import differential_check
from src.ocr import extract_text
from src.parser import LabResult, parse_qualitative, parse_results
from src.quality import annotate, quality_messages, truncated
from src.summarizer import summarize

st.set_page_config(page_title="Lab Report Summarizer", page_icon="🧪", layout="wide")
st.title("v1 Lab Report Summarizer")
st.caption("we have created this version for sample running purpose")


@st.cache_data(show_spinner=False)
def read_report(data: bytes, suffix: str):
    """Two OCR passes for images (basic = primary, full = second opinion)."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        path = tmp.name
    try:
        basic, kinds = extract_text(path, "basic")
        full = basic if set(kinds) == {"text"} else extract_text(path, "full")[0]
    finally:
        os.unlink(path)
    return basic, full, kinds


f = st.file_uploader("Upload a lab report", type=["pdf", "png", "jpg", "jpeg", "tif", "tiff"])
if not f:
    st.stop()

data = f.getvalue()
fid = f"{f.name}_{len(data)}"
with st.spinner("Reading report (two passes for photos)..."):
    text_basic, text_full, kinds = read_report(data, os.path.splitext(f.name)[1])

results = parse_results(text_basic)
annotate(results, parse_results(text_full))
quals = parse_qualitative(text_basic)

with st.expander("Raw extracted text"):
    st.text(text_basic)

for m in quality_messages(results, quals):
    st.warning(m)

# ---------------- step 1: review ----------------
st.subheader("1. Check the extracted values")
st.write("Compare with your report. Rows marked ⚠️ must be confirmed. Edit any cell, "
         "tick **Confirmed**, and delete wrong rows with the row menu.")

if not results:
    st.error("No numeric results were found.")
else:
    df = pd.DataFrame([{
        "Confirmed": not r.review,
        "Check": "⚠️" if r.review else "",
        "Test": r.name, "Value": r.value, "Unit": r.unit,
        "Low": r.low, "High": r.high,
        "Note": r.note, "Suggested": r.suggested, "Second read": getattr(r, "alt", None),
    } for r in results])
    df = df.sort_values("Check", ascending=False, kind="stable").reset_index(drop=True)

    edited = st.data_editor(
        df, key=f"editor_{fid}", hide_index=True, num_rows="dynamic",
        disabled=["Check", "Note", "Suggested", "Second read"],
        column_config={
            "Confirmed": st.column_config.CheckboxColumn("Confirmed"),
            "Value": st.column_config.NumberColumn("Value", format="%g"),
            "Low": st.column_config.NumberColumn("Low", format="%g"),
            "High": st.column_config.NumberColumn("High", format="%g"),
        })

    pending = int((~edited["Confirmed"].fillna(False).astype(bool)).sum())
    if pending:
        st.info(f"{pending} row(s) still need confirmation.")

    if st.button("Confirm and summarize", type="primary", disabled=pending > 0):
        confirmed = []
        for _, row in edited.iterrows():
            name = "" if pd.isna(row["Test"]) else str(row["Test"]).strip()
            if not name or pd.isna(row["Value"]):
                continue
            confirmed.append(LabResult(
                name, float(row["Value"]),
                "" if pd.isna(row["Unit"]) else str(row["Unit"]),
                None if pd.isna(row["Low"]) else float(row["Low"]),
                None if pd.isna(row["High"]) else float(row["High"])))
        rows = analyze(confirmed)
        with st.spinner("Writing summary..."):
            summary = summarize(rows, quals)
        st.session_state[fid] = {"rows": rows, "summary": summary,
                                 "diff": differential_check(confirmed)}

# ---------------- qualitative ----------------
if quals:
    st.subheader("Non-numeric results (urine and similar)")
    st.dataframe(pd.DataFrame([{
        "Check": "⚠️ name cut off" if truncated(q.name) else "",
        "Test": q.name, "Result": q.value, "Expected": q.reference, "Status": q.status,
    } for q in quals]), hide_index=True)

# ---------------- step 2: summary ----------------
out = st.session_state.get(fid)
if out:
    st.subheader("2. Results")
    if out["diff"]:
        st.warning(out["diff"])
    res = pd.DataFrame(out["rows"])[["Test", "Value", "Unit", "Reference", "Status", "Severity"]]
    st.dataframe(res.style.apply(
        lambda r: ["background-color:#ffe0e0" if r.Status != "Normal" else ""] * len(r), axis=1),
        hide_index=True)
    st.subheader("Summary")
    st.write(out["summary"])
    st.download_button("Download summary", out["summary"], file_name="summary.txt")

st.info("⚠️ For information only, not medical advice. Always check the values against your "
        "original report and consult a doctor.")