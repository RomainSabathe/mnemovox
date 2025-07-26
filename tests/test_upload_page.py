# ABOUTME: Tests for upload page endpoints both GET and POST
# ABOUTME: Verifies /recordings/upload form display and file upload functionality

import pytest
import tempfile
import io
from pathlib import Path
from fastapi.testclient import TestClient
from mnemovox.app import create_app
from mnemovox.config import Config
from mnemovox.db import init_db


@pytest.fixture
def test_app_upload():
    """Create test app for upload functionality testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create config
        config = Config(
            monitored_directory=str(tmp_path / "monitored"),
            storage_path=str(tmp_path / "storage"),
            upload_temp_path=str(tmp_path / "uploads"),
            items_per_page=10,
        )

        # Create directories
        Path(config.storage_path).mkdir(parents=True, exist_ok=True)
        Path(config.upload_temp_path).mkdir(parents=True, exist_ok=True)

        # Initialize database
        db_path = str(tmp_path / "test.db")
        init_db(db_path)

        # Create app
        app = create_app(config, db_path)
        client = TestClient(app)

        yield client, config, db_path


def test_upload_page_get(test_app_upload):
    """Test that GET /recordings/upload shows upload form."""
    client, config, db_path = test_app_upload

    response = client.get("/recordings/upload")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")

    html = response.text

    # Check basic HTML structure
    assert "<!DOCTYPE html>" in html
    assert "<title>" in html

    # Check for upload form
    assert "<form" in html
    assert 'enctype="multipart/form-data"' in html
    assert 'method="post"' in html
    assert 'type="file"' in html
    assert "accept=" in html  # Should accept audio files

    # Check for file input
    assert 'name="file"' in html

    # Check for submit button
    assert 'type="submit"' in html or "Upload" in html


def test_upload_page_post_valid_file(test_app_upload):
    """Test POST /recordings/upload with valid audio file."""
    client, config, db_path = test_app_upload

    # Create a fake WAV file
    fake_wav_content = b"RIFF" + b"\x00" * 40 + b"WAVE" + b"\x00" * 100
    file_data = io.BytesIO(fake_wav_content)

    response = client.post(
        "/recordings/upload", files={"file": ("test.wav", file_data, "audio/wav")}
    )

    # Should redirect to recordings list or show success page
    assert response.status_code in [200, 302]

    if response.status_code == 302:
        # Check redirect location
        assert "location" in response.headers
        assert "/recordings" in response.headers["location"]


def test_upload_page_post_invalid_file(test_app_upload):
    """Test POST /recordings/upload with invalid file type."""
    client, config, db_path = test_app_upload

    # Create a fake text file
    fake_txt_content = b"This is not an audio file"
    file_data = io.BytesIO(fake_txt_content)

    response = client.post(
        "/recordings/upload", files={"file": ("test.txt", file_data, "text/plain")}
    )

    # Should return error (either 400 or show form with error)
    assert response.status_code in [200, 400]

    if response.status_code == 200:
        # If showing form again, should contain error message
        html = response.text
        assert "error" in html.lower() or "invalid" in html.lower()


def test_upload_page_post_no_file(test_app_upload):
    """Test POST /recordings/upload with no file provided."""
    client, config, db_path = test_app_upload

    response = client.post("/recordings/upload")

    # Should return error or show form with error
    assert response.status_code in [200, 400, 422]

    if response.status_code == 200:
        html = response.text
        assert "error" in html.lower() or "required" in html.lower()


def test_upload_storage_path_format(test_app_upload):
    """Test that uploaded files have correct storage path format for transcription."""
    client, config, db_path = test_app_upload

    # Create a fake WAV file (basic but invalid for transcription)
    fake_wav_content = b"RIFF" + b"\x00" * 40 + b"WAVE" + b"\x00" * 100
    file_data = io.BytesIO(fake_wav_content)

    response = client.post(
        "/recordings/upload", files={"file": ("test_path.wav", file_data, "audio/wav")}
    )

    # Should redirect successfully even if transcription fails later
    assert response.status_code in [200, 302]

    # Check the database record has correct storage path
    from mnemovox.db import get_session, Recording

    session = get_session(db_path)
    try:
        recording = (
            session.query(Recording)
            .filter_by(original_filename="test_path.wav")
            .first()
        )
        assert recording is not None

        # The storage path should not contain duplication
        storage_path = recording.storage_path
        print(f"Storage path: {storage_path}")
        print(f"Config storage path: {config.storage_path}")

        # Storage path should now be relative (like "2025/07-20/filename.wav")
        # NOT absolute (like "/tmp/xxx/storage/2025/07-20/filename.wav")
        from pathlib import Path

        assert not Path(
            storage_path
        ).is_absolute(), f"Storage path should be relative: {storage_path}"

        # The file should exist when combined with the base storage path
        full_path = Path(config.storage_path) / storage_path
        assert full_path.exists(), f"File not found at combined path: {full_path}"

        # Verify the stored path matches the expected pattern: YYYY/MM-DD/filename
        import re

        pattern = r"^\d{4}/\d{2}-\d{2}/.+\.wav$"
        assert re.match(
            pattern, storage_path
        ), f"Storage path doesn't match expected pattern: {storage_path}"

    finally:
        session.close()
