import argparse
import json
import re
import time
from pathlib import Path

from src.ingest import load_pages
from src.ocr import extract_text, ocr_image

SAMPLES = Path("data/samples")
OUT = Path("data/outputs/ocr_text")
NUM_RE = re.compile(r"\d+(?:\.\d+)?")
RANGE_RE = re.compile(r"\d\s*(?:-|–|to)\s*\d")


def score(text, truth):
    """How many ground-truth (name, value) pairs appear on the same OCR line."""
    lines = text.lower().splitlines()
    hit = 0
    for r in truth["results"]:
        key = r["name"].lower()
        for ln in lines:
            if key in ln:
                nums = [float(x) for x in NUM_RE.findall(ln.replace(",", ""))]
                if any(abs(n - r["value"]) < 1e-6 for n in nums):
                    hit += 1
                    break
    return hit, len(truth["results"])


def run_synth(n, psm):
    modes = ["none", "basic", "full"]
    stats = {}   # (kind, mode) -> [hits, total, seconds, files]
    truths = sorted(SAMPLES.glob("synth_*.json"))[:n]
    for tj in truths:
        tag = tj.stem
        truth = json.loads(tj.read_text(encoding="utf-8"))
        files = {"digital": SAMPLES / f"{tag}_digital.pdf",
                 "scan": SAMPLES / f"{tag}_scan.pdf",
                 "photo": SAMPLES / f"{tag}_photo.jpg"}
        for kind, f in files.items():
            if kind == "digital":
                text, _ = extract_text(str(f))
                h, t = score(text, truth)
                s = stats.setdefault((kind, "textlayer"), [0, 0, 0.0, 0])
                s[0] += h; s[1] += t; s[3] += 1
                continue
            pages = [p["content"] for p in load_pages(str(f))]
            for mode in modes:
                t0 = time.time()
                text = "\n".join(ocr_image(p, mode, psm) for p in pages)
                dt = time.time() - t0
                h, t = score(text, truth)
                s = stats.setdefault((kind, mode), [0, 0, 0.0, 0])
                s[0] += h; s[1] += t; s[2] += dt; s[3] += 1
        print(f"done {tag}")

    print(f"\n{'type':<9}{'mode':<11}{'recall':>8}{'sec/file':>10}")
    for (kind, mode), (h, t, sec, nf) in stats.items():
        print(f"{kind:<9}{mode:<11}{h / t:>8.1%}{sec / nf:>10.1f}")


def run_real(mode, psm):
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"{'file':<45}{'pages':<14}{'chars':>6}{'range-lines':>12}{'sec':>6}")
    for sub in ["real", "online", "simulated"]:
        d = SAMPLES / sub
        if not d.exists():
            continue
        for f in sorted(d.iterdir()):
            if f.suffix.lower() not in {".pdf", ".jpg", ".jpeg", ".png"}:
                continue
            t0 = time.time()
            try:
                text, kinds = extract_text(str(f), mode, psm)
            except Exception as e:
                print(f"{sub + '/' + f.name:<45}ERROR {e}")
                continue
            dt = time.time() - t0
            (OUT / f"{sub}_{f.stem}.txt").write_text(text, encoding="utf-8")
            used = "+".join(sorted(set(kinds)))
            print(f"{sub + '/' + f.name:<45}{used:<14}{len(text):>6}"
                  f"{len(RANGE_RE.findall(text)):>12}{dt:>6.1f}")
    print(f"\nText files saved in {OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("which", choices=["synth", "real"])
    ap.add_argument("--n", type=int, default=6, help="synthetic reports to test")
    ap.add_argument("--mode", default="basic", choices=["none", "basic", "full"])
    ap.add_argument("--psm", type=int, default=6)
    a = ap.parse_args()
    run_synth(a.n, a.psm) if a.which == "synth" else run_real(a.mode, a.psm)