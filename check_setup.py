import sys

def check(name, fn):
    try:
        print(f"[ OK ] {name}: {fn()}")
    except Exception as e:
        print(f"[FAIL] {name}: {e}")

def python_ver():
    assert sys.version_info >= (3, 10), "Need Python 3.10+"
    return sys.version.split()[0]

def libs():
    import fitz, cv2, numpy, pandas, requests, streamlit, pytesseract
    return f"PyMuPDF {fitz.__doc__.split()[1]}, OpenCV {cv2.__version__}"

def tesseract():
    import pytesseract
    from config import TESSERACT_CMD
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    return str(pytesseract.get_tesseract_version())

def ocr_roundtrip():
    import cv2, numpy as np, pytesseract
    from config import TESSERACT_CMD
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    img = np.full((120, 600), 255, dtype=np.uint8)
    cv2.putText(img, "Hemoglobin 11.2 g/dL", (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 1.3, 0, 3)
    text = pytesseract.image_to_string(img).strip()
    assert "11" in text, f"OCR read: {text!r}"
    return f"read {text!r}"

def ollama():
    import requests
    from config import OLLAMA_MODEL
    r = requests.get("http://localhost:11434/api/tags", timeout=5)
    names = [m["name"] for m in r.json().get("models", [])]
    assert any(OLLAMA_MODEL.split(":")[0] in n for n in names), \
        f"Model not pulled. Installed: {names}"
    return f"running, models: {names}"

check("Python", python_ver)
check("Libraries", libs)
check("Tesseract", tesseract)
check("OCR round-trip", ocr_roundtrip)
check("Ollama", ollama) 