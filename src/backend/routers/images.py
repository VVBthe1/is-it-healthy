from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile

from ..db import DbSession
from ..ocr import read_label
from ..schemas import MAX_INGREDIENTS_LENGTH, ImageJobCreated, OcrOut
from ..security import CurrentUser
from .jobs import queue_analysis

router = APIRouter(tags=["images"])

MIN_CONFIDENCE = 70


@router.post("/ocr", response_model=OcrOut)
def extract_text(file: UploadFile, user: CurrentUser):
    return read_label(file)


@router.post("/analyses/image", response_model=ImageJobCreated, status_code=202)
def create_image_analysis(file: UploadFile, background_tasks: BackgroundTasks, db: DbSession, user: CurrentUser):
    label = read_label(file)
    ingredients = (label["ingredients"] or "").strip()
    if not ingredients:
        raise HTTPException(status_code=422, detail="No ingredients list found in the image")
    if label["confidence"] < MIN_CONFIDENCE:
        raise HTTPException(status_code=422, detail="Image is too unclear; retake it or type the ingredients")
    if len(ingredients) > MAX_INGREDIENTS_LENGTH:
        raise HTTPException(status_code=422, detail="Ingredients text is too long")
    job = queue_analysis(ingredients, background_tasks, db, user)
    return {"job_id": job.id, "ingredients": ingredients, "confidence": label["confidence"]}
