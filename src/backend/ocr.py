import httpx
from fastapi import HTTPException, UploadFile

from .config import settings

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
OCR_TIMEOUT = 60


def read_upload(file: UploadFile) -> bytes:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Upload a JPEG, PNG or WebP image")
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image is larger than 10 MB")
    return content


def read_label(file: UploadFile) -> dict:
    content = read_upload(file)
    try:
        response = httpx.post(
            f"{settings.ocr_url}/ocr",
            files={"file": (file.filename or "label", content, file.content_type)},
            timeout=OCR_TIMEOUT,
        )
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="OCR service unavailable")
    if response.status_code == 422:
        raise HTTPException(status_code=422, detail="Not a readable image")
    if response.is_error:
        raise HTTPException(status_code=502, detail="OCR service failed")
    return response.json()
