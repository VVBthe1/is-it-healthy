import httpx
import pytest

from .conftest import FAKE_RESULT

PNG = ("label.png", b"fake-image-bytes", "image/png")
OCR_RESPONSE = {
    "text": "INGREDIENTS: Sugar, Salt\nNutrition information",
    "ingredients": "Sugar, Salt",
    "confidence": 87.5,
}


@pytest.fixture
def ocr_service(monkeypatch):
    calls = []

    def fake_post(url, files, timeout):
        calls.append(files["file"])
        return httpx.Response(200, json=OCR_RESPONSE)

    monkeypatch.setattr("src.backend.ocr.httpx.post", fake_post)
    return calls


def test_ocr_returns_text_for_review(client, auth_headers, ocr_service):
    response = client.post("/ocr", files={"file": PNG}, headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == OCR_RESPONSE
    assert ocr_service == [PNG]


def test_image_analysis_queues_job_with_extracted_ingredients(client, auth_headers, ocr_service):
    response = client.post("/analyses/image", files={"file": PNG}, headers=auth_headers)

    assert response.status_code == 202
    body = response.json()
    assert (body["ingredients"], body["confidence"]) == ("Sugar, Salt", 87.5)
    job = client.get(f"/jobs/{body['job_id']}", headers=auth_headers).json()
    assert (job["status"], job["result"]) == ("done", FAKE_RESULT)


def test_image_without_ingredients_returns_422(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "src.backend.ocr.httpx.post",
        lambda url, files, timeout: httpx.Response(200, json={**OCR_RESPONSE, "ingredients": None}),
    )

    response = client.post("/analyses/image", files={"file": PNG}, headers=auth_headers)

    assert response.status_code == 422
    assert response.json()["detail"] == "No ingredients list found in the image"


def test_low_confidence_image_returns_422(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "src.backend.ocr.httpx.post",
        lambda url, files, timeout: httpx.Response(200, json={**OCR_RESPONSE, "confidence": 55.1}),
    )

    response = client.post("/analyses/image", files={"file": PNG}, headers=auth_headers)

    assert response.status_code == 422
    assert "too unclear" in response.json()["detail"]


def test_unsupported_file_type_returns_415(client, auth_headers, ocr_service):
    response = client.post("/ocr", files={"file": ("label.pdf", b"%PDF", "application/pdf")}, headers=auth_headers)

    assert response.status_code == 415
    assert ocr_service == []


def test_too_large_image_returns_413(client, auth_headers, ocr_service, monkeypatch):
    monkeypatch.setattr("src.backend.ocr.MAX_UPLOAD_BYTES", 4)

    response = client.post("/ocr", files={"file": PNG}, headers=auth_headers)

    assert response.status_code == 413


def test_ocr_service_down_returns_503(client, auth_headers, monkeypatch):
    def down(url, files, timeout):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr("src.backend.ocr.httpx.post", down)

    assert client.post("/ocr", files={"file": PNG}, headers=auth_headers).status_code == 503


def test_unreadable_image_returns_422(client, auth_headers, monkeypatch):
    monkeypatch.setattr("src.backend.ocr.httpx.post", lambda url, files, timeout: httpx.Response(422))

    assert client.post("/ocr", files={"file": PNG}, headers=auth_headers).status_code == 422


def test_image_endpoints_require_a_token(client, ocr_service):
    assert client.post("/ocr", files={"file": PNG}).status_code == 401
    assert client.post("/analyses/image", files={"file": PNG}).status_code == 401
