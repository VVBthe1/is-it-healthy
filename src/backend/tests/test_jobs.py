import uuid

from .conftest import FAKE_RESULT


def create_job(client, headers, ingredients="sugar, salt, INS 211"):
    return client.post("/analyses", json={"ingredients": ingredients}, headers=headers)


def test_create_analysis_returns_202_with_job_id(client, auth_headers):
    response = create_job(client, auth_headers)

    assert response.status_code == 202
    uuid.UUID(response.json()["job_id"])


def test_job_is_done_after_background_task(client, auth_headers):
    job_id = create_job(client, auth_headers).json()["job_id"]

    response = client.get(f"/jobs/{job_id}", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == job_id
    assert body["status"] == "done"
    assert body["result"] == FAKE_RESULT
    assert body["error"] is None


def test_job_fails_when_analysis_raises(client, auth_headers, monkeypatch):
    def broken(text):
        raise RuntimeError("ollama is down")

    monkeypatch.setattr("src.backend.analysis.run", broken)
    job_id = create_job(client, auth_headers).json()["job_id"]

    body = client.get(f"/jobs/{job_id}", headers=auth_headers).json()

    assert (body["status"], body["result"], body["error"]) == ("failed", None, "ollama is down")


def test_unknown_job_returns_404(client, auth_headers):
    response = client.get(f"/jobs/{uuid.uuid4()}", headers=auth_headers)

    assert response.status_code == 404


def test_invalid_job_id_returns_422(client, auth_headers):
    response = client.get("/jobs/not-a-uuid", headers=auth_headers)

    assert response.status_code == 422


def test_empty_ingredients_returns_422(client, auth_headers):
    response = create_job(client, auth_headers, ingredients="   ")

    assert response.status_code == 422


def test_missing_body_returns_422(client, auth_headers):
    response = client.post("/analyses", headers=auth_headers)

    assert response.status_code == 422


def test_jobs_require_a_token(client, auth_headers):
    job_id = create_job(client, auth_headers).json()["job_id"]

    assert client.post("/analyses", json={"ingredients": "sugar"}).status_code == 401
    assert client.get(f"/jobs/{job_id}").status_code == 401


def test_other_users_job_returns_404(client, login):
    owner = login("owner@example.com")
    other = login("other@example.com")
    job_id = create_job(client, owner).json()["job_id"]

    assert client.get(f"/jobs/{job_id}", headers=other).status_code == 404
