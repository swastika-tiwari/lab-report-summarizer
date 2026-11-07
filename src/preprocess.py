import cv2
import numpy as np

MIN_WIDTH = 1800    # upscale smaller images (text too tiny for Tesseract)
MAX_WIDTH = 3000    # downscale huge phone photos (slow, no accuracy gain)


def resize_to_range(gray):
    h, w = gray.shape
    if w < MIN_WIDTH:
        s = MIN_WIDTH / w
        return cv2.resize(gray, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
    if w > MAX_WIDTH:
        s = MAX_WIDTH / w
        return cv2.resize(gray, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    return gray


def normalize_illumination(gray):
    """Remove shadows and uneven lighting: divide by an estimate of the background."""
    bg = cv2.dilate(gray, np.ones((9, 9), np.uint8))     # erases thin text strokes
    bg = cv2.GaussianBlur(bg, (0, 0), sigmaX=gray.shape[1] / 25)
    bg = np.maximum(bg, 1)
    return cv2.divide(gray, bg, scale=255)


def estimate_skew(gray, max_angle=10.0, step=0.25):
    """Return the rotation (degrees) that makes text rows most horizontal."""
    h, w = gray.shape
    s = 800 / w
    small = cv2.resize(gray, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    bw = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    sh, sw = bw.shape
    center = (sw / 2, sh / 2)

    best_angle, best_score = 0.0, -1.0
    for angle in np.arange(-max_angle, max_angle + step, step):
        M = cv2.getRotationMatrix2D(center, float(angle), 1.0)
        rot = cv2.warpAffine(bw, M, (sw, sh), flags=cv2.INTER_NEAREST)
        proj = rot.sum(axis=1, dtype=np.float64)
        score = float(np.sum(np.diff(proj) ** 2))
        if score > best_score:
            best_angle, best_score = float(angle), score
    return best_angle


def rotate(gray, angle):
    if abs(angle) < 0.2:
        return gray
    h, w = gray.shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderValue=255)

def remove_table_lines(gray):
    """Erase long vertical lines (table borders). A border touching the first
    letter of a row makes Tesseract drop that letter."""
    bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    h = gray.shape[0]
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(40, h // 25)))
    lines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, kernel)
    lines = cv2.dilate(lines, np.ones((3, 3), np.uint8))
    out = gray.copy()
    out[lines > 0] = 255
    return out

def preprocess(gray, mode="basic"):
    """
    none  : image as is
    basic : resize + fix lighting + deskew            (grayscale output)
    full  : basic + light blur + Otsu black/white     (binary output)
    """
    if mode == "none":
        return gray
    gray = resize_to_range(gray)
    gray = normalize_illumination(gray)
    gray = rotate(gray, estimate_skew(gray))
    gray = remove_table_lines(gray)
    if mode == "full":
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    return gray