import difflib
import re

from src.checks import differential_check


def _key(name: str) -> str:
    return re.sub(r"[^a-z]", "", name.lower())


def truncated(name: str) -> bool:
    """A name starting with a lowercase letter ('rystals', 'asts') lost its first letter."""
    return bool(name) and name[0].islower()


def annotate(primary, secondary):
    """Flag rows where the two OCR passes disagree, and rows with cut-off names.
    Mutates `primary`. Never changes a value."""
    for r in primary:
        notes = []
        best, score = None, 0.0
        for s in secondary:
            sc = difflib.SequenceMatcher(None, _key(r.name), _key(s.name)).ratio()
            if sc > score:
                best, score = s, sc
        r.alt = None
        if best is not None and score >= 0.75 and abs(best.value - r.value) > 1e-9:
            r.alt = best.value
            notes.append(f"two OCR passes disagree ({r.value:g} vs {best.value:g})")
        if truncated(r.name):
            notes.append("name looks cut off")
        if notes:
            r.review = True
            r.note = "; ".join(([r.note] if r.note else []) + notes)


def quality_messages(results, quals):
    """Plain-language warnings about the whole report."""
    msgs = []
    total = len(results) + len(quals)
    if total < 5:
        msgs.append(f"Only {total} result rows were detected. The photo may be blurry, "
                    "cropped or dark. Retake it with the whole page in frame, in even light.")
    cut = sum(truncated(r.name) for r in results) + sum(truncated(q.name) for q in quals)
    if cut:
        msgs.append(f"{cut} row name(s) start mid-word. The left edge of the page is probably "
                    "cut off. Retake the photo with the full page in frame.")
    d = differential_check(results)
    if d:
        msgs.append(d)
    flagged = sum(r.review for r in results)
    if results and flagged / len(results) > 0.4:
        msgs.append(f"{flagged} of {len(results)} rows need checking. The image quality is low, "
                    "so a clearer photo or the original PDF will work much better.")
    return msgs