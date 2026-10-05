import uuid

from sqlalchemy import func, select

from src.ai_engine.agents.graph import run
from src.shared.db.app_models import Job, JobStatus
from src.shared.db.models import User

from .db import SessionLocal


def run_analysis(job_id: uuid.UUID) -> None:
    with SessionLocal.begin() as session:
        job = session.get(Job, job_id)
        job.status = JobStatus.RUNNING
        input_text = job.input_text

    result, error = None, None
    try:
        result = run(input_text)
        status = JobStatus.DONE
    except Exception as e:
        status = JobStatus.FAILED
        error = str(e)

    with SessionLocal.begin() as session:
        job = session.get(Job, job_id)
        job.status = status
        job.result = result
        job.error = error
