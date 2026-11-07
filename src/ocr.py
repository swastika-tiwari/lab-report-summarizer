import cv2
import pytesseract

from config import TESSERACT_CMD, OCR_LANG
from src.ingest import load_pages
from src.preprocess import preprocess

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


def ocr_image(gray, mode="basic", psm=6):
    img = preprocess(gray, mode)
    # Tesseract drops characters touching the image edge; add a white margin
    img = cv2.copyMakeBorder(img, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=255)
    return pytesseract.image_to_string(img, lang=OCR_LANG, config=f"--oem 1 --psm {psm}")


def extract_text(path, mode="basic", psm=6):
    texts, kinds = [], []
    for page in load_pages(path):
        kinds.append(page["kind"])
        if page["kind"] == "text":
            texts.append(page["content"])
        else:
            texts.append(ocr_image(page["content"], mode, psm))
    return "\n".join(texts), kinds