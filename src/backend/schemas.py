from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.shared.db.app_models import JobStatus

MAX_INGREDIENTS_LENGTH = 5000


class Category(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    name: str
    parent_code: str | None = None


class CategoryDetail(Category):
    parent: Category | None = None
    children: list[Category] = []


class AnalysisIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    ingredients: str = Field(min_length=1, max_length=MAX_INGREDIENTS_LENGTH)


class JobCreated(BaseModel):
    job_id: UUID


class OcrOut(BaseModel):
    text: str
    ingredients: str | None
    confidence: float


class ImageJobCreated(JobCreated):
    ingredients: str
    confidence: float


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: JobStatus
    result: dict | None
    error: str | None
    created_at: datetime
    updated_at: datetime


class UserIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
