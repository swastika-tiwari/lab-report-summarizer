import argparse
from pathlib import Path

from src.ocr import extract_text
from src.parser import parse_results, parse_qualitative
from src.analyzer import analyze
from src.checks import differential_check

ap = argparse.ArgumentParser()
ap.add_argument("--only", default="", help="substring of file name, e.g. lab01")
ap.add_argument("--show", action="store_true", help="print the extracted text too")
ap.add_argument("--mode", default="basic", choices=["none", "basic", "full"])
a = ap.parse_args()

for f in sorted(Path("data/samples/real").iterdir()):
    if f.suffix.lower() not in {".pdf", ".jpg", ".jpeg", ".png"} or a.only not in f.name:
        continue
    text, kinds = extract_text(str(f), a.mode)
    res = parse_results(text)
    rows = analyze(res)
    quals = parse_qualitative(text)
    review = sum(1 for r in rows if r["Review"])
    abn = sum(1 for r in rows if r["Status"] != "Normal")
    print(f"\n=== {f.name}  [{'+'.join(sorted(set(kinds)))}]  "
          f"numeric={len(rows)}  abnormal={abn}  review={review}  qualitative={len(quals)}")
    msg = differential_check(res)
    if msg:
        print("  ⚠️ " + msg)
    if a.show:
        print("--- text ---\n" + text + "\n--- end text ---")
    for r in rows:
        ref = r["Reference"] or "?"
        print(f"  {r['Review'] or '  '} {r['Test'][:28]:<28}{r['Value']:>10g} {r['Unit']:<10}"
              f"{ref:<14}{r['Status']:<7}{r['Note']}")
    for q in quals:
        print(f"     {q.name[:28]:<28}{q.value:<12} ref: {q.reference:<18}{q.status}")