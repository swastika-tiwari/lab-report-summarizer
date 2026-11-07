import argparse
import csv
import difflib
import json
import re
from collections import defaultdict
from pathlib import Path

from src.ocr import extract_text
from src.parser import parse_results
from src.quality import annotate

KEYS = Path("data/answer_keys")
SAMPLES = Path("data/samples")
OUT = Path("data/outputs")
MATCH_MIN = 0.8


def letters(s):
    return re.sub(r"[^a-z]", "", s.lower())


def name_sim(a, b):
    a, b = letters(a), letters(b)
    return difflib.SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def close(a, b):
    return abs(a - b) <= 1e-6 * max(1.0, abs(a))


def same(a, b):
    return (a is None and b is None) or (a is not None and b is not None and close(a, b))


def status(v, lo, hi):
    if lo is not None and v < lo:
        return "Low"
    if hi is not None and v > hi:
        return "High"
    return "Normal"


def unit_norm(u):
    return re.sub(r"[^a-z0-9%]", "", (u or "").lower())


def load_cases(which, n):
    cases = []
    if which in ("real", "all"):
        for kj in sorted(KEYS.glob("*.json")):
            k = json.loads(kj.read_text(encoding="utf-8"))
            cases.append({"id": kj.stem, "file": k["file"], "split": k.get("split", "dev"),
                          "truth": k["results"]})
    if which in ("synth", "all"):
        for tj in sorted(SAMPLES.glob("synth_*.json"))[:n]:
            t = json.loads(tj.read_text(encoding="utf-8"))
            for form, ext in (("scan", "pdf"), ("photo", "jpg")):
                cases.append({"id": f"{tj.stem}_{form}",
                              "file": (SAMPLES / f"{tj.stem}_{form}.{ext}").as_posix(),
                              "split": f"synthetic-{form}", "truth": t["results"]})
    return cases


def match(truth, pred):
    pairs = sorted(((name_sim(t["name"], p.name), i, j)
                    for i, t in enumerate(truth) for j, p in enumerate(pred)), reverse=True)
    tm, pm = {}, {}
    for s, i, j in pairs:
        if s < MATCH_MIN:
            break
        if i not in tm and j not in pm:
            tm[i], pm[j] = j, i
    return tm, pm


def run_case(case, mode, second):
    if not Path(case["file"]).exists():
        print(f"  [skip] {case['file']} not found")
        return []
    text, kinds = extract_text(case["file"], mode)
    pred = parse_results(text)
    sec = []
    if second and mode != "full" and set(kinds) != {"text"}:
        sec = parse_results(extract_text(case["file"], "full")[0])
    annotate(pred, sec)

    truth = case["truth"]
    tm, pm = match(truth, pred)
    recs = []
    for i, t in enumerate(truth):
        base = {"case": case["id"], "split": case["split"], "truth_name": t["name"],
                "t_value": t["value"], "t_range": f"{t.get('low')}-{t.get('high')}"}
        if i not in tm:
            recs.append({**base, "pred_name": "", "matched": False, "spurious": False,
                         "value_ok": False, "range_ok": False, "unit_ok": False,
                         "status_ok": False, "flagged": False, "p_value": "", "p_range": "",
                         "note": "MISSED"})
            continue
        p = pred[tm[i]]
        lo, hi = t.get("low"), t.get("high")
        recs.append({**base, "pred_name": p.name, "matched": True, "spurious": False,
                     "value_ok": close(t["value"], p.value),
                     "range_ok": same(lo, p.low) and same(hi, p.high),
                     "unit_ok": unit_norm(t.get("unit")) == unit_norm(p.unit),
                     "status_ok": status(t["value"], lo, hi) == status(p.value, p.low, p.high),
                     "flagged": p.review, "p_value": p.value,
                     "p_range": f"{p.low}-{p.high}", "note": p.note})
    for j, p in enumerate(pred):
        if j not in pm:
            recs.append({"case": case["id"], "split": case["split"], "truth_name": "",
                         "t_value": "", "t_range": "", "pred_name": p.name, "matched": False,
                         "spurious": True, "value_ok": False, "range_ok": False,
                         "unit_ok": False, "status_ok": False, "flagged": p.review,
                         "p_value": p.value, "p_range": f"{p.low}-{p.high}",
                         "note": "SPURIOUS " + p.note})
    return recs


def pct(n, d):
    return f"{100 * n / d:5.1f}%  ({n}/{d})" if d else "  n/a"


def summarize(label, recs):
    truth = [r for r in recs if not r["spurious"]]
    pred = [r for r in recs if r["pred_name"]]
    row_ok = lambda r: r["matched"] and r["value_ok"] and r["range_ok"]
    wrong = [r for r in pred if not row_ok(r)]
    silent = [r for r in wrong if not r["flagged"]]
    flagged = [r for r in pred if r["flagged"]]
    stat_bad_silent = [r for r in pred if r["matched"] and not r["status_ok"] and not r["flagged"]]
    print(f"\n=== {label}  (truth rows {len(truth)}, predicted rows {len(pred)})")
    print(f"  Extraction recall (row found)        {pct(sum(r['matched'] for r in truth), len(truth))}")
    print(f"  Value accuracy                       {pct(sum(r['matched'] and r['value_ok'] for r in truth), len(truth))}")
    print(f"  Row accuracy (value + range)         {pct(sum(row_ok(r) for r in truth), len(truth))}")
    print(f"  Unit accuracy (matched rows)         {pct(sum(r['unit_ok'] for r in truth if r['matched']), sum(r['matched'] for r in truth))}")
    print(f"  Status accuracy (Low/Normal/High)    {pct(sum(r['matched'] and r['status_ok'] for r in truth), len(truth))}")
    print(f"  Precision (predicted rows correct)   {pct(sum(row_ok(r) for r in pred), len(pred))}")
    print(f"  Flag recall (wrong rows flagged)     {pct(len(wrong) - len(silent), len(wrong))}")
    print(f"  SILENT ERROR RATE (wrong, unflagged) {pct(len(silent), len(pred))}")
    print(f"  Silent WRONG STATUS (unflagged)      {pct(len(stat_bad_silent), len(pred))}")
    print(f"  Review burden (rows flagged)         {pct(len(flagged), len(pred))}")
    print(f"  Flag precision (flagged rows wrong)  {pct(len([r for r in flagged if r in wrong]), len(flagged))}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("which", choices=["real", "synth", "all"])
    ap.add_argument("--n", type=int, default=6, help="synthetic reports")
    ap.add_argument("--mode", default="basic", choices=["none", "basic", "full"])
    ap.add_argument("--no-second", action="store_true", help="disable the second OCR pass")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()

    cases = load_cases(a.which, a.n)
    if not cases:
        raise SystemExit("No cases found. Create answer keys in data/answer_keys/ first.")

    allrecs = []
    for c in cases:
        print(f"{c['id']} [{c['split']}]")
        allrecs += run_case(c, a.mode, not a.no_second)

    by_split = defaultdict(list)
    for r in allrecs:
        by_split[r["split"]].append(r)
    for split, recs in sorted(by_split.items()):
        summarize(split, recs)

    OUT.mkdir(parents=True, exist_ok=True)
    name = f"eval_{a.which}_{a.mode}{'_nosecond' if a.no_second else ''}{a.tag}.csv"
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(allrecs[0].keys()))
        w.writeheader()
        w.writerows(allrecs)
    print(f"\nPer-row details: {OUT / name}  (open in Excel, filter 'flagged' = FALSE and "
          "'value_ok' = FALSE to see the silent errors)")


if __name__ == "__main__":
    main()