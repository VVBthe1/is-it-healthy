from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import exists, select

from src.shared.db.app_models import User

from ..db import DbSession
from ..schemas import Token, UserIn, UserOut
from ..security import CurrentUser, create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserIn, db: DbSession):
    if db.scalar(select(exists().where(User.email == payload.email))):
        raise HTTPException(status_code=409, detail="Email already taken")
    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    return user


@router.post("/token", response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession):
    user = db.scalar(select(User).where(User.email == form.username))
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"})
    return Token(access_token=create_access_token(str(user.id)), token_type="bearer")


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user
