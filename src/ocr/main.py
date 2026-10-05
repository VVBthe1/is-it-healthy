import io

from fastapi import FastAPI, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel

from .extract import extract_ingredients
from .reader import read_text

app = FastAPI(title="OCR")


class OcrOut(BaseModel):
    text: str
    ingredients: str | None
    confidence: float


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ocr", response_model=OcrOut)
def ocr(file: UploadFile):
    try:
        image = Image.open(io.BytesIO(file.file.read()))
        image.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=422, detail="Not a readable image")
    text, confidence = read_text(image)
    return OcrOut(text=text, ingredients=extract_ingredients(text), confidence=confidence)
