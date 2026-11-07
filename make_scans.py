from pathlib import Path

import cv2
import numpy as np
import pymupdf

ROOT = Path("data/samples")
SRC_DIRS = [ROOT / "real", ROOT / "online"]
OUT = ROOT / "simulated"
OUT.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(7)
DPI = 200


def degrade(img, max_angle=1.5, blur=0.6, noise=4):
    h, w = img.shape
    angle = rng.uniform(-max_angle, max_angle)
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    out = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR,
                         borderValue=255).astype(np.float32)
    out = cv2.GaussianBlur(out, (0, 0), blur)
    out += rng.normal(0, noise, out.shape)
    return np.clip(out, 0, 255).astype(np.uint8)


def pdf_pages_gray(pdf_path):
    doc = pymupdf.open(pdf_path)
    for page in doc:
        pix = page.get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY)
        yield np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width).copy()
    doc.close()


def has_text_layer(pdf_path):
    doc = pymupdf.open(pdf_path)
    n = sum(len(p.get_text().strip()) for p in doc)
    doc.close()
    return n > 80


def save_image_pdf(imgs, path):
    doc = pymupdf.open()
    for img in imgs:
        h, w = img.shape
        page = doc.new_page(width=w * 72 / DPI, height=h * 72 / DPI)
        ok, png = cv2.imencode(".png", img)
        page.insert_image(page.rect, stream=png.tobytes())
    doc.save(path)
    doc.close()


def main():
    for d in SRC_DIRS:
        if not d.exists():
            continue
        for f in sorted(d.iterdir()):
            ext = f.suffix.lower()
            if ext == ".pdf":
                if not has_text_layer(f):
                    print(f"[already scanned] {f.name}")
                    continue
                print(f"[digital PDF]     {f.name}")
                imgs = [degrade(p) for p in pdf_pages_gray(f)]
                stem = f.stem.replace("_digital", "_scansim")
                if stem == f.stem:
                    stem += "_scansim"
                save_image_pdf(imgs, str(OUT / f"{stem}.pdf"))
            elif ext in {".jpg", ".jpeg", ".png"}:
                img = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
                if img is None:
                    print(f"[unreadable]      {f.name}")
                    continue
                print(f"[photo]           {f.name}")
                stem = f.stem.replace("_photo", "_photopdf")
                if stem == f.stem:
                    stem += "_photopdf"
                save_image_pdf([img], str(OUT / f"{stem}.pdf"))


if __name__ == "__main__":
    main()