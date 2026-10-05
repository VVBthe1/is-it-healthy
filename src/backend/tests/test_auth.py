import uuid
from datetime import datetime, timedelta, timezone

import jwt

from src.backend.config import settings

from .conftest import PASSWORD

EMAIL = "asha@example.com"


def register(client, email=EMAIL, password=PASSWORD):
    return client.post("/auth/register", json={"email": email, "password": password})


def token_for(client, email=EMAIL, password=PASSWORD):
    return client.post("/auth/token", data={"username": email, "password": password})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_register_returns_201_without_password(client):
    response = register(client)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == EMAIL
    assert "password" not in body and "hashed_password" not in body


def test_register_duplicate_email_returns_409(client):
    register(client)

    assert register(client).status_code == 409


def test_register_rejects_bad_email_and_short_password(client):
    assert register(client, email="not-an-email").status_code == 422
    assert register(client, password="short").status_code == 422


def test_login_returns_bearer_token(client):
    register(client)

    response = token_for(client)

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_login_wrong_password_and_unknown_email_return_same_401(client):
    register(client)

    wrong_password = token_for(client, password="wrong-password")
    unknown_email = token_for(client, email="nobody@example.com")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_me_returns_current_user(client, auth_headers):
    response = client.get("/auth/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["email"] == EMAIL


def test_me_without_token_returns_401(client):
    assert client.get("/auth/me").status_code == 401


def test_me_with_tampered_token_returns_401(client, auth_headers):
    token = auth_headers["Authorization"].removeprefix("Bearer ")
    tampered = token[:-2] + ("AA" if token[-2:] != "AA" else "BB")

    response = client.get("/auth/me", headers=bearer(tampered))

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_with_expired_token_returns_401(client):
    user_id = register(client).json()["id"]
    expired = jwt.encode(
        {"sub": user_id, "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.jwt_secret,
        algorithm="HS256",
    )

    assert client.get("/auth/me", headers=bearer(expired)).status_code == 401


def test_me_with_token_for_deleted_user_returns_401(client):
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        settings.jwt_secret,
        algorithm="HS256",
    )

    assert client.get("/auth/me", headers=bearer(token)).status_code == 401
