"""
Integration tests for summarization API endpoint.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import patch

from mnemovox.app import create_app
from mnemovox.config import Config
from mnemovox.db import Recording, init_db, get_session


@pytest.fixture
def test_app_with_recording():
    """Create test app with a sample recording."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create config
        config = Config(
            monitored_directory=str(tmp_path / "monitored"),
            storage_path=str(tmp_path / "storage"),
            upload_temp_path=str(tmp_path / "uploads"),
        )

        # Create directories
        Path(config.storage_path).mkdir(parents=True, exist_ok=True)

        # Initialize database
        db_path = str(tmp_path / "test.db")
        init_db(db_path)

        # Add a test recording with transcript
        session = get_session(db_path)
        try:
            recording = Recording(
                original_filename="test.wav",
                internal_filename="test_internal.wav",
                storage_path="test/path.wav",
                import_timestamp=datetime.now(),
                transcript_status="complete",
                transcript_text="This is a test transcript with some content to summarize.",
            )
            session.add(recording)
            session.commit()

            # Add recording without transcript
            recording2 = Recording(
                original_filename="test2.wav",
                internal_filename="test2_internal.wav",
                storage_path="test2/path.wav",
                import_timestamp=datetime.now(),
                transcript_status="pending",
                transcript_text=None,
            )
            session.add(recording2)
            session.commit()
        finally:
            session.close()

        app = create_app(config, db_path)
        yield TestClient(app)


def test_summarize_recording_success(test_app_with_recording):
    """Test successful recording summarization request."""
    client = test_app_with_recording

    # Mock the summarization task to avoid actual API call
    with patch("mnemovox.app.summarize_recording") as mock_summarize:
        response = client.post("/api/recordings/1/summarize")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["status"] == "queued"
        assert "queued for summarization" in data["message"]

        # Verify background task was called with correct parameters
        mock_summarize.assert_called_once()
        call_args = mock_summarize.call_args[0]
        assert call_args[0] == 1  # recording_id
        assert call_args[1].endswith("test.db")  # db_path


def test_summarize_recording_not_found(test_app_with_recording):
    """Test summarization request for non-existent recording."""
    client = test_app_with_recording

    response = client.post("/api/recordings/999/summarize")

    assert response.status_code == 404
    assert response.json()["detail"] == "Recording not found"


def test_summarize_recording_no_transcript(test_app_with_recording):
    """Test summarization request for recording without transcript."""
    client = test_app_with_recording

    # Use the second recording that was added without transcript
    response = client.post("/api/recordings/2/summarize")

    assert response.status_code == 400
    assert "must have completed transcript" in response.json()["detail"]
