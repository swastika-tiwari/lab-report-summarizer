import json
import random
from pathlib import Path

import cv2
import numpy as np
import pymupdf

OUT = Path("data/samples")
OUT.mkdir(parents=True, exist_ok=True)

# name, unit, low, high, decimals   (low=None means "upper limit only", e.g. < 200)
TESTS = [
    ("Hemoglobin", "g/dL", 12.0, 15.5, 1),
    ("RBC Count", "million/cumm", 3.8, 4.8, 2),
    ("WBC Count", "/cumm", 4000, 11000, 0),
    ("Platelet Count", "/cumm", 150000, 410000, 0),
    ("Hematocrit", "%", 36, 46, 1),
    ("MCV", "fL", 80, 100, 1),
    ("Fasting Glucose", "mg/dL", 70, 100, 0),
    ("HbA1c", "%", 4.0, 5.6, 1),
    ("Creatinine", "mg/dL", 0.6, 1.1, 2),
    ("Urea", "mg/dL", 15, 40, 0),
    ("Uric Acid", "mg/dL", 2.5, 6.8, 1),
    ("Total Bilirubin", "mg/dL", 0.2, 1.2, 1),
    ("SGOT (AST)", "U/L", 5, 40, 0),
    ("SGPT (ALT)", "U/L", 5, 40, 0),
    ("Alkaline Phosphatase", "U/L", 44, 147, 0),
    ("Sodium", "mmol/L", 135, 145, 0),
    ("Potassium", "mmol/L", 3.5, 5.1, 1),
    ("Vitamin D", "ng/mL", 30, 100, 1),
    ("Vitamin B12", "pg/mL", 200, 900, 0),
    ("TSH", "uIU/mL", 0.4, 4.0, 2),
    ("Total Cholesterol", "mg/dL", None, 200, 0),
    ("LDL Cholesterol", "mg/dL", None, 100, 0),
    ("Triglycerides", "mg/dL", None, 150, 0),
]

LABS = ["City Diagnostics Pvt Ltd", "Apex Pathology Laboratory", "Sunrise Health Labs"]


def make_value(rng, low, high, dec):
    """About 70% normal, 30% abnormal."""
    if low is None:
        v = rng.uniform(0.5 * high, high) if rng.random() < 0.7 else high * rng.uniform(1.05, 1.5)
    elif rng.random() < 0.7:
        v = rng.uniform(low, high)
    elif rng.random() < 0.5:
        v = low * rng.uniform(0.6, 0.95)
    else:
        v = high * rng.uniform(1.05, 1.4)
    return round(v, dec) if dec else int(round(v))


def status_of(v, low, high):
    if low is not None and v < low:
        return "Low"
    if high is not None and v > high:
        return "High"
    return "Normal"


def build_rows(rng):
    chosen = rng.sample(TESTS, rng.randint(14, 20))
    chosen.sort(key=TESTS.index)
    rows = []
    for name, unit, low, high, dec in chosen:
        v = make_value(rng, low, high, dec)
        rows.append({"name": name, "value": v, "unit": unit, "low": low, "high": high,
                     "status": status_of(v, low, high), "dec": dec})
    return rows


def fmt(x, dec):
    return f"{x:.{dec}f}" if dec else f"{int(x)}"


def make_pdf(path, rows, lab, show_flags):
    doc = pymupdf.open()
    page = doc.new_page()  # A4
    page.insert_text((50, 55), lab, fontname="hebo", fontsize=16)
    page.insert_text((50, 75), "Patient Name: Test Patient    Age/Sex: 34 / F", fontname="cour", fontsize=10)
    page.insert_text((50, 90), "Date: 12/03/2025    Sample: Blood/Serum", fontname="cour", fontsize=10)
    page.draw_line((50, 100), (545, 100))
    page.insert_text((50, 118), f"{'TEST NAME':<24}{'RESULT':>8} {'UNIT':<14}REFERENCE RANGE",
                     fontname="cobo", fontsize=10)
    y = 138
    for r in rows:
        ref = (f"< {fmt(r['high'], r['dec'])}" if r["low"] is None
               else f"{fmt(r['low'], r['dec'])} - {fmt(r['high'], r['dec'])}")
        flag = ""
        if show_flags and r["status"] != "Normal":
            flag = "  H" if r["status"] == "High" else "  L"
        line = f"{r['name']:<24}{fmt(r['value'], r['dec']):>8} {r['unit']:<14}{ref}{flag}"
        page.insert_text((50, y), line, fontname="cour", fontsize=10)
        y += 18
    page.insert_text((50, y + 25), "*** End of Report ***", fontname="helv", fontsize=9)
    doc.save(path)
    doc.close()


def render_gray(pdf_path, dpi=200):
    doc = pymupdf.open(pdf_path)
    pix = doc[0].get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width).copy()
    doc.close()
    return img


def degrade(img, nprng, max_angle, blur, noise, shading):
    h, w = img.shape
    angle = nprng.uniform(-max_angle, max_angle)
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    out = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderValue=255)
    out = out.astype(np.float32)
    if shading:
        grad = np.tile(np.linspace(1.0, 1.0 - shading, w, dtype=np.float32), (h, 1))
        out *= grad
    if blur:
        out = cv2.GaussianBlur(out, (0, 0), blur)
    if noise:
        out += nprng.normal(0, noise, out.shape)
    return np.clip(out, 0, 255).astype(np.uint8), round(float(angle), 2)


def image_to_pdf(img, path):
    ok, png = cv2.imencode(".png", img)
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_image(page.rect, stream=png.tobytes())
    doc.save(path)
    doc.close()


def main(n=10, seed=42):
    rng = random.Random(seed)
    nprng = np.random.default_rng(seed)
    for i in range(1, n + 1):
        tag = f"synth_{i:03d}"
        rows = build_rows(rng)
        lab = rng.choice(LABS)

        digital = OUT / f"{tag}_digital.pdf"
        make_pdf(str(digital), rows, lab, show_flags=rng.random() < 0.5)
        clean = render_gray(str(digital))

        scan, a1 = degrade(clean, nprng, max_angle=1.5, blur=0.5, noise=4, shading=0)
        image_to_pdf(scan, str(OUT / f"{tag}_scan.pdf"))

        photo, a2 = degrade(clean, nprng, max_angle=4, blur=1.0, noise=10, shading=0.25)
        cv2.imwrite(str(OUT / f"{tag}_photo.jpg"), photo, [cv2.IMWRITE_JPEG_QUALITY, 55])

        truth = {"lab": lab, "scan_angle": a1, "photo_angle": a2,
                 "results": [{k: r[k] for k in ("name", "value", "unit", "low", "high", "status")}
                             for r in rows]}
        (OUT / f"{tag}.json").write_text(json.dumps(truth, indent=2), encoding="utf-8")
        abn = sum(r["status"] != "Normal" for r in rows)
        print(f"{tag}: {len(rows)} tests, {abn} abnormal, {lab}")


if __name__ == "__main__":
    main()