from fastapi import FastAPI
from sqlalchemy import text

from .db import DbSession
from .routers import auth, categories, images, jobs

app = FastAPI(title="Is it healthy? - Health API")
app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(jobs.router)
app.include_router(images.router)


@app.get("/health")
def health(db: DbSession):
    db.execute(text("select 1"))
    return {"status": "ok"}
