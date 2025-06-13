# ABOUTME: Tests for GET/POST /api/settings endpoints
# ABOUTME: Validates retrieval and update of global transcription defaults
from fastapi.testclient import TestClient
import pytest
from src.audio_manager.app import create_app
from src.audio_manager.config import Config


@pytest.fixture
def client(tmp_path, monkeypatch):
    # isolate config.yaml in a temp cwd
    monkeypatch.chdir(tmp_path)
    config = Config()
    app = create_app(config, ":memory:")
    return TestClient(app)


def test_get_settings_defaults(client):
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["default_model"] == "base.en"
    assert data["default_language"] == "auto"


def test_post_valid_settings(client):
    payload = {"default_model": "small.en", "default_language": "fr"}
    response = client.post("/api/settings", json=payload)
    assert response.status_code == 200
    assert response.json() == payload
    # subsequent GET reflects changes
    get_resp = client.get("/api/settings")
    assert get_resp.json() == payload


@pytest.mark.parametrize(
    "payload, error_field",
    [
        ({}, "default_model"),
        ({"default_model": ""}, "default_model"),
        ({"default_language": ""}, "default_language"),
        ({"default_model": None, "default_language": "en"}, "default_model"),
        ({"default_model": "en", "default_language": None}, "default_language"),
        ({"unexpected": "value"}, "default_model"),
    ],
)
def test_post_invalid_settings(client, payload, error_field):
    response = client.post("/api/settings", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert error_field in data["detail"]["error"]
