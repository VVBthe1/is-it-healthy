import os

import pytesseract
from PIL import Image, ImageFilter, ImageOps

OCR_LANG = os.environ.get("OCR_LANG", "eng")
MIN_WIDTH = 2400
TESSERACT_CONFIG = "--psm 4"


def preprocess(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image).convert("L")
    if image.width < MIN_WIDTH:
        scale = MIN_WIDTH / image.width
        image = image.resize((MIN_WIDTH, round(image.height * scale)), Image.Resampling.LANCZOS)
    image = ImageOps.autocontrast(image, cutoff=2)
    return image.filter(ImageFilter.SHARPEN)


def read_text(image: Image.Image) -> tuple[str, float]:
    data = pytesseract.image_to_data(
        preprocess(image), lang=OCR_LANG, config=TESSERACT_CONFIG, output_type=pytesseract.Output.DICT
    )
    lines: dict[tuple[int, int, int], list[str]] = {}
    confidences = []
    for i, word in enumerate(data["text"]):
        confidence = float(data["conf"][i])
        if not word.strip() or confidence < 0:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append(word)
        confidences.append(confidence)
    text = "\n".join(" ".join(words) for words in lines.values())
    mean = sum(confidences) / len(confidences) if confidences else 0.0
    return text, round(mean, 1)
