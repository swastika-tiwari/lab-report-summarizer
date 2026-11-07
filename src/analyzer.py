from src.parser import LabResult


def classify(r: LabResult) -> dict:
    status, deviation = "Normal", 0.0
    if r.low is not None and r.value < r.low:
        status, deviation = "Low", (r.low - r.value) / r.low * 100 if r.low else 0
    elif r.high is not None and r.value > r.high:
        status, deviation = "High", (r.value - r.high) / r.high * 100 if r.high else 0

    severity = ""
    if status != "Normal":
        severity = "Mild" if deviation < 10 else "Moderate" if deviation < 30 else "Marked"

    if r.low is not None and r.high is not None:
        rng = f"{r.low:g} - {r.high:g}"
    elif r.high is not None:
        rng = f"< {r.high:g}"
    elif r.low is not None:
        rng = f"> {r.low:g}"
    else:
        rng = ""

    return {"Test": r.name, "Value": r.value, "Unit": r.unit, "Reference": rng,
            "Status": status, "Severity": severity,
            "Review": "⚠️" if r.review else "", "Note": r.note, "Suggested": r.suggested}


def analyze(results: list[LabResult]) -> list[dict]:
    return [classify(r) for r in results]