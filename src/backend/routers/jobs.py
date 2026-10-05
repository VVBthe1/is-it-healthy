import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException

from src.shared.db.app_models import Job

from ..analysis import run_analysis
from ..db import DbSession
from ..schemas import AnalysisIn, JobCreated, JobOut
from ..security import CurrentUser

router = APIRouter(tags=["jobs"])


def queue_analysis(text: str, background_tasks: BackgroundTasks, db: DbSession, user: CurrentUser) -> Job:
    job = Job(input_text=text, user_id=user.id)
    db.add(job)
    db.commit()
    background_tasks.add_task(run_analysis, job.id)
    return job


@router.post("/analyses", response_model=JobCreated, status_code=202)
def create_analysis(payload: AnalysisIn, background_tasks: BackgroundTasks, db: DbSession, user: CurrentUser):
    job = queue_analysis(payload.ingredients, background_tasks, db, user)
    return {"job_id": job.id}


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: uuid.UUID, db: DbSession, user: CurrentUser):
    job = db.get(Job, job_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job
