import requests

from config import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT

PROMPT = """You are a medical report explainer for patients.
Using ONLY the data below, write a short, plain-language summary (under 200 words).
Rules:
- Do NOT diagnose or state diseases as certain. Say "may be associated with" if needed.
- Do NOT invent values or tests that are not listed.
- Start with one overall sentence, then explain each abnormal result simply.
- End by advising the patient to discuss the results with their doctor.

Numeric tests checked: {total}.
Abnormal numeric results:
{numeric}
Abnormal non-numeric results:
{qual}
"""


def _numeric_lines(rows):
    return [f"- {r['Test']}: {r['Value']:g} {r['Unit']} ({r['Status']}, "
            f"{r['Severity'].lower()}, reference {r['Reference']})"
            for r in rows if r["Status"] != "Normal"]


def _qual_lines(quals):
    return [f"- {q.name}: {q.value} (expected {q.reference})"
            for q in quals if q.status == "Abnormal"]


def fallback_summary(rows, quals):
    n, q = _numeric_lines(rows), _qual_lines(quals)
    if not n and not q:
        return ("All detected values are within their reference ranges. "
                "Please confirm with your doctor.")
    return ("Results outside the expected range:\n" + "\n".join(n + q)
            + "\n\nPlease discuss these results with your doctor.")


def summarize(rows, quals=()):
    n, q = _numeric_lines(rows), _qual_lines(quals)
    if not n and not q:
        return fallback_summary(rows, quals)
    try:
        resp = requests.post(OLLAMA_URL, timeout=OLLAMA_TIMEOUT, json={
            "model": OLLAMA_MODEL,
            "prompt": PROMPT.format(total=len(rows), numeric="\n".join(n) or "none",
                                    qual="\n".join(q) or "none"),
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 400},
        })
        resp.raise_for_status()
        return resp.json()["response"].strip()
    except Exception:
        return fallback_summary(rows, quals)    # works even if Ollama is off