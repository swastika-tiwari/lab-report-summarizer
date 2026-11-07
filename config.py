import platform

TESSERACT_CMD = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if platform.system() == "Windows" else "tesseract"
)

OCR_DPI = 300
OCR_CONFIG = "--oem 1 --psm 6"
OCR_LANG = "eng"          # use "eng+hin" if you installed Hindi data

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"
OLLAMA_TIMEOUT = 120