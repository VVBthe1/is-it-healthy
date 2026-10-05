import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR.parents[1] / ".env")
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

from src.backend.db import engine  # noqa: E402
from src.backend.main import app  # noqa: E402

PASSWORD = "correct-horse-battery"
FAKE_RESULT = {"is_healthy": True}


@pytest.fixture(autouse=True)
def fake_graph(monkeypatch):
    monkeypatch.setattr("src.backend.analysis.run", lambda text: FAKE_RESULT)


@pytest.fixture(scope="session", autouse=True)
def migrate():
    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE app.jobs, app.users"))


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def login(client):
    def _login(email="asha@example.com", password=PASSWORD):
        client.post("/auth/register", json={"email": email, "password": password})
        response = client.post("/auth/token", data={"username": email, "password": password})
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _login


@pytest.fixture
def auth_headers(login):
    return login()
