from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from ..schemas import Category, CategoryDetail
from ...shared.db.models import FoodCategory, code_sort_key

from ..db import DbSession

router = APIRouter(prefix="/categories", tags=["categories"])

@router.get("", response_model=list[Category])
def list_categories(db: DbSession, search: str | None = None, limit: int = Query(50, ge=1, le=200)):
    stmt = select(FoodCategory)
    if search:
        stmt = stmt.where(FoodCategory.name.ilike(f"%{search}%"))

    stmt = stmt.order_by(code_sort_key(FoodCategory.code)).limit(limit)
    return db.scalars(stmt).all()

@router.get("/{code}", response_model=CategoryDetail)
def get_category(code: str, db: DbSession):
    category = db.get(
        FoodCategory,
        code,
        options=[joinedload(FoodCategory.parent), selectinload(FoodCategory.children)],
    )
    if category is None:
        raise HTTPException(status_code=404, detail=f"Category {code} not found")
    return category
