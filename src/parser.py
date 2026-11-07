import re
from dataclasses import dataclass
from typing import Optional

NUM = r"\d+(?:\.\d+)?"


@dataclass
class LabResult:
    name: str
    value: float
    unit: str
    low: Optional[float]
    high: Optional[float]
    printed_flag: str = ""
    review: bool = False
    note: str = ""
    suggested: Optional[float] = None
    raw: str = ""


@dataclass
class QualResult:
    name: str
    value: str
    reference: str
    status: str                      # Normal / Abnormal / Review
    raw: str = ""


# ---------- cleaning ----------
UNIT_FIX = {
    "em/dl": "gm/dl", "gm/di": "gm/dl", "gmail": "gm/dl", "{l": "fL", "fi.": "fL",
    "fi": "fL", "fl": "fL", "/omm": "/cmm", "/cram": "/cmm", "vor": "%",
    "picogram": "pg", "celivcumm": "cells/cumm", "cellscumm": "cells/cumm",
    "cellsvcumm": "cells/cumm", "millionvcumm": "million/cumm",
    "millions/emm": "million/cumm", "lakh/icmm": "lakh/cumm",    "expn": "10^n",
    "cumm": "/cumm", "cmm": "/cmm", "ps": "pg", "pa": "pg",
    "y%": "%", "yo": "%", "ye": "%", "mg/d": "mg/dL",
}
FLAG_RE = re.compile(r"^[oO0]?[HL]{1,2}\*?$")
FLAG_WORDS = {"low": "L", "high": "H", "borderline": "", "critical": "",
              "normal": "", "abnormal": ""}
BAD_NAMES = {"optimal", "near optimal", "above optimal", "desirable", "borderline",
             "borderline high", "high", "very high", "low", "normal", "intermediate",
             "deficient", "insufficient", "sufficient", "toxic", "prediabetes", "diabetes"}
KNOWN_UNIT = re.compile(
    r"^(?:%|g/?dl|gm/?dl|gm%|g/l|mg/?dl|mg%|mg/l|mg|u/l|iu/l|miu/l|uiu/ml|miu/ml|iu/ml|"
    r"ng/ml|ng/dl|pg/ml|pg|fl|mmol/l|meq/l|ratio|sec|seconds|mm/hr|10\^n|"
    r"mil{1,3}(?:ion)?s?\.?/c?u?mm|lakh/c?u?mm|cells/c?u?mm|/c?u?mm|/ul|/µl|/μl)$",
    re.IGNORECASE)

def clean_line(s: str) -> str:
    s = s.replace("§", "5").replace("–", "-").replace("—", "-")
    s = re.sub(r"[A-Za-z0-9\-]+\.(?:com|org|net)", " ", s, flags=re.I)   # watermarks
    s = re.sub(r"\b10\s*[°^*³]\s*\d{0,2}\s*/?\s*(?:[uµμ]?[lL1])?(?![A-Za-z0-9])", " EXPN ", s)
    s = re.sub(r"(?<=\d),(?=\d{2,3}\b)", "", s)                           # 7,800 -> 7800
    s = re.sub(r"[“”‘’\"'`»«|=_~]", " ", s)
    s = re.sub(r"\b(Borderline|Critical|High|Low)(?=\d)", r"\1 ", s, flags=re.I)
    s = re.sub(r"(?<=[A-Za-z])(?=\d+(?:\.\d+)?\s*-\s*\d)", " ", s)        # cumm2000 - 7000
    s = re.sub(r"\s*[:;]\s*", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def clean_name(n: str) -> str:
    n = n.strip()                                      # <-- new: trailing space broke the rules below
    n = re.split(r"[*•]", n)[-1].strip()
    n = re.sub(r"^[^A-Za-z]+", "", n)
    n = re.sub(r"^[A-Za-z]\s+(?=[A-Za-z]{3,})", "", n)
    n = re.sub(r"\s+[^A-Za-z0-9)]{1,2}$", "", n)       # trailing "$" etc.
    n = re.sub(r"\s+[a-z]{1,2}$", "", n)               # trailing "sy", "s"
    return re.sub(r"[\s.\-:,]+$", "", n)
    n = re.split(r"[*•]", n)[-1]
    n = re.sub(r"^[^A-Za-z]+", "", n)
    n = re.sub(r"^[A-Za-z]\s+(?=[A-Za-z]{3,})", "", n)
    n = re.sub(r"\s+[^A-Za-z0-9)]{1,2}$", "", n)      # trailing "$" etc.
    n = re.sub(r"\s+[a-z]{1,2}$", "", n)              # trailing "sy", "s"
    return re.sub(r"[\s.\-:,]+$", "", n)


# ---------- numeric results ----------
RANGE = re.compile(rf"(?<![\d.\-])(?P<lo>{NUM})\s*(?:-|to)\s*(?P<hi>{NUM})(?![\d.])")
LIMIT = re.compile(rf"(?P<op><=|>=|<|>)\s*(?P<n>{NUM})")
VAL = re.compile(rf"(?<![\d.\-])(?P<v>{NUM})(?![\d.\-])")
UNIT_TOK = re.compile(r"^[A-Za-zµμ%/][A-Za-z0-9%/µμ.^*]{0,14}$")


def _review(r: LabResult, value_text: str, lo_t: str, hi_t: str):
    lo, hi, v = r.low, r.high, r.value
    comp = "H" if hi is not None and v > hi else "L" if lo is not None and v < lo else ""
    notes, range_issue = [], False

    if r.printed_flag and r.printed_flag != comp:
        notes.append(f"report prints {r.printed_flag} but value reads as {comp or 'in range'}")

    if lo is not None and hi is not None:
        if lo > hi:
            notes.append("reference range looks damaged (low > high)")
            range_issue = True
        elif lo > 0 and "." in lo_t and "." not in hi_t and hi >= 4 * lo:
            notes.append(f"reference range may have lost a decimal ({lo_t} - {hi_t} may be "
                         f"{lo_t} - {hi / 10:g})")
            range_issue = True
        elif (lo > 0 and lo_t.isdigit() and hi_t.isdigit() and len(lo_t) >= 3
              and len(hi_t) >= 3 and v < 0.25 * lo
              and any(lo / d <= v <= hi / d for d in (10, 100))):
            d = next(d for d in (10, 100) if lo / d <= v <= hi / d)
            notes.append(f"reference range may have lost a decimal "
                         f"({lo:g} - {hi:g} may be {lo / d:g} - {hi / d:g})")
            range_issue = True
        elif "." not in value_text and v > 2 * hi:
            for d in (10, 100, 1000):
                c = v / d
                if 0.5 * lo <= c <= hi:
                    r.suggested = round(c, 3)
                    notes.append(f"decimal point may be lost, maybe {r.suggested}")
                    break

    if r.suggested is None and not range_issue:
        if lo and lo > 0 and v < 0.25 * lo:
            notes.append("value far below range, check for a dropped digit")
        if hi and hi > 0 and v > 5 * hi:
            notes.append("value far above range, check for an extra digit")

    if re.search(r"(?<![A-Za-z])\d+(?:\.\d+)?(?![A-Za-z])", r.name):
        notes.append("value may be mangled by OCR")

    if r.unit and not KNOWN_UNIT.match(r.unit.replace(" ", "")):
        notes.append(f"unrecognised unit '{r.unit}'")

    if notes:
        r.review, r.note = True, "; ".join(notes)


def _build(left, right, lo, hi, lo_t, hi_t, raw):
    ms = list(VAL.finditer(left))
    if not ms:
        return None
    m = ms[-1]
    name = clean_name(left[:m.start()])
    letters_only = re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", name.lower())).strip()
    if (len(re.findall(r"[A-Za-z]", name)) < 3 or len(name) > 50
            or re.search(r"[<>]", name) or letters_only in BAD_NAMES):
        return None

    flag, unit_toks = "", []
    for t in left[m.end():].split():
        tl = t.lower().strip("*")
        if tl in FLAG_WORDS:
            flag = flag or FLAG_WORDS[tl]
        elif FLAG_RE.match(t):
            flag = "H" if "H" in t.upper() else "L"
        else:
            unit_toks.append(t)
    unit = " ".join(unit_toks)
    if not unit:
        rt = right.split()
        while rt and (FLAG_RE.match(rt[0]) or rt[0].lower() in FLAG_WORDS):
            rt = rt[1:]
        if rt and UNIT_TOK.match(rt[0]):
            unit = rt[0] + ("%" if len(rt) > 1 and rt[1] == "%" else "")
    unit = UNIT_FIX.get(unit.lower(), unit)

    r = LabResult(name, float(m["v"]), unit, lo, hi, flag, raw=raw)
    _review(r, m["v"], lo_t, hi_t)
    return r


def parse_line(line: str) -> Optional[LabResult]:
    s = clean_line(line)
    if len(s) < 6 or "hpf" in s.lower():
        return None
    cands = [(m.start(), m.end(), float(m["lo"]), float(m["hi"]), m["lo"], m["hi"])
             for m in RANGE.finditer(s)]
    for m in LIMIT.finditer(s):
        n = float(m["n"])
        lo, hi = (None, n) if m["op"].startswith("<") else (n, None)
        cands.append((m.start(), m.end(), lo, hi, "", ""))
    for start, end, lo, hi, lo_t, hi_t in sorted(cands, key=lambda c: c[0]):
        r = _build(s[:start].strip(), s[end:].strip(), lo, hi, lo_t, hi_t, line)
        if r:
            return r
    return None


def parse_results(text: str) -> list[LabResult]:
    out, seen = [], set()
    for line in text.splitlines():
        r = parse_line(line)
        if r and r.name.lower() not in seen:
            seen.add(r.name.lower())
            out.append(r)
    return out


# ---------- qualitative results (urine etc.) ----------
QUAL_WORDS = ["pale yellow", "not detected", "non reactive", "nonreactive", "straw",
              "yellow", "clear", "turbid", "hazy", "absent", "nil", "nii", "normal",
              "present", "negative", "positive", "trace", "reactive", "detected"]
QUAL_RE = re.compile(r"\b(" + "|".join(QUAL_WORDS) + r")\b", re.IGNORECASE)
SYN = {"not detected": "absent", "non reactive": "absent", "nonreactive": "absent",
       "negative": "absent", "nil": "absent", "nii": "absent"}
HPF_RE = re.compile(r"^(?P<name>[A-Za-z][A-Za-z .\-/()]{2,40}?)\s+(?P<rest>\d.*hpf.*)$",
                    re.IGNORECASE)


def _canon(text: str) -> set:
    t = text.lower()
    for k, v in SYN.items():
        t = re.sub(rf"\b{k}\b", v, t)
    return set(re.findall(r"[a-z]+", t))


def parse_hpf(line: str) -> Optional[QualResult]:
    """Microscopy rows like 'Pus Cells 8-10/hpf  0 - 5/hpf'."""
    s = clean_line(line)
    if "hpf" not in s.lower():
        return None
    s = re.sub(r"\b[Ss]\b(?=\s*/)", "5", s)
    m = HPF_RE.match(s)
    if not m:
        return None
    name = clean_name(m["name"])
    if len(re.findall(r"[A-Za-z]", name)) < 3:
        return None
    rngs = re.findall(rf"({NUM})\s*-\s*({NUM})", m["rest"])
    if not rngs:
        return None
    value = f"{rngs[0][0]}-{rngs[0][1]}/hpf"
    if len(rngs) < 2:
        return QualResult(name, value, "", "Review", line)
    ref = f"{rngs[1][0]}-{rngs[1][1]}/hpf"
    status = "Normal" if float(rngs[0][1]) <= float(rngs[1][1]) else "Abnormal"
    return QualResult(name, value, ref, status, line)


def parse_qualitative(text: str) -> list[QualResult]:
    out = []
    for line in text.splitlines():
        h = parse_hpf(line)
        if h:
            out.append(h)
            continue
        s = clean_line(line)
        ms = list(QUAL_RE.finditer(s))
        if len(ms) < 2:
            continue
        name = clean_name(re.sub(r"\s+[^A-Za-z]{1,2}$", "", s[:ms[0].start()].strip()))
        if len(re.findall(r"[A-Za-z]", name)) < 3:
            continue
        value, ref = ms[0].group(0), s[ms[0].end():].strip()
        status = "Normal" if _canon(value) & _canon(ref) else "Abnormal"
        out.append(QualResult(name, value, ref, status, line))
    return out