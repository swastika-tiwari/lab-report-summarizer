from pathlib import Path

import cv2
import numpy as np
import pymupdf

from config import OCR_DPI

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
MIN_TEXT_CHARS = 80


def page_to_lines(page):
    """Group words into visual rows by vertical position, so a value and its
    test name end up on the same line even when the PDF stores them separately."""
    words = page.get_text("words")          # (x0, y0, x1, y1, word, ...)
    if not words:
        return ""
    words = sorted(words, key=lambda w: ((w[1] + w[3]) / 2, w[0]))
    heights = sorted(w[3] - w[1] for w in words)
    tol = 0.6 * heights[len(heights) // 2]

    rows, cur, cur_y = [], [], 0.0
    for w in words:
        yc = (w[1] + w[3]) / 2
        if cur and abs(yc - cur_y) > tol:
            rows.append(cur)
            cur = []
        cur.append(w)
        cur_y = sum((x[1] + x[3]) / 2 for x in cur) / len(cur)
    if cur:
        rows.append(cur)
    return "\n".join(" ".join(w[4] for w in sorted(r, key=lambda w: w[0])) for r in rows)


def load_pages(path: str):
    """Yield {'kind': 'text', 'content': str} or {'kind': 'image', 'content': ndarray}."""
    ext = Path(path).suffix.lower()

    if ext == ".pdf":
        doc = pymupdf.open(path)
        try:
            for page in doc:
                if len(page.get_text().strip()) >= MIN_TEXT_CHARS:
                    yield {"kind": "text", "content": page_to_lines(page)}
                else:
                    pix = page.get_pixmap(dpi=OCR_DPI, colorspace=pymupdf.csGRAY)
                    img = np.frombuffer(pix.samples, dtype=np.uint8)
                    yield {"kind": "image", "content": img.reshape(pix.height, pix.width).copy()}
        finally:
            doc.close()

    elif ext in IMAGE_EXT:
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError(f"Cannot read image: {path}")
        yield {"kind": "image", "content": img}

    else:
        raise ValueError(f"Unsupported file type: {ext}")