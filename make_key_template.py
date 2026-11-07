import argparse
import json
from pathlib import Path

from src.ocr import extract_text
from src.parser import parse_results

ap = argparse.ArgumentParser()
ap.add_argument("file", help="e.g. data/samples/real/lab09_photo_cbc.jpg")
ap.add_argument("--split", default="dev", choices=["dev", "heldout"])
a = ap.parse_args()

f = Path(a.file)
text, _ = extract_text(str(f), "basic")
rows = [{"name": r.name, "value": r.value, "unit": r.unit, "low": r.low, "high": r.high}
        for r in parse_results(text)]

out = Path("data/answer_keys")
out.mkdir(parents=True, exist_ok=True)
dest = out / f"{f.stem}.json"
if dest.exists():
    raise SystemExit(f"{dest} already exists, not overwriting")
dest.write_text(json.dumps({"file": f.as_posix(), "split": a.split, "results": rows},
                           indent=2), encoding="utf-8")
print(f"Wrote {dest} with {len(rows)} rows.")
print("NOW CHECK EVERY ROW AGAINST THE IMAGE: fix wrong values, names and ranges, "
      "and add rows the parser missed.")