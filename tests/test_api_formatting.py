"""
Tests for formatting API endpoint.
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
                transcript_text="um, this is like, a test transcript, you know, with filler words and, uh, poor grammar.",
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


class TestFormattingAPI:
    """Test cases for formatting API endpoint."""

    @patch("mnemovox.app.format_recording")
    def test_format_success(self, mock_format, test_app_with_recording):
        """Test successful formatting request."""
        client = test_app_with_recording

        response = client.post("/api/recordings/1/format")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["status"] == "queued"
        assert "formatting" in data["message"]

        # Verify background task was added
        mock_format.assert_called_once()

    def test_format_recording_not_found(self, test_app_with_recording):
        """Test formatting with non-existent recording."""
        client = test_app_with_recording

        response = client.post("/api/recordings/999/format")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Recording not found"

    @patch("mnemovox.app.format_recording")
    def test_format_no_transcript(self, mock_format, test_app_with_recording):
        """Test formatting with recording without completed transcript."""
        client = test_app_with_recording

        response = client.post("/api/recordings/2/format")

        assert response.status_code == 400
        data = response.json()
        assert "completed transcript" in data["detail"]

        # Verify background task was not added
        mock_format.assert_not_called()

    @patch("mnemovox.app.format_recording")
    def test_format_incomplete_transcript(self, mock_format, test_app_with_recording):
        """Test formatting with recording with incomplete transcript."""
        client = test_app_with_recording

        # This test uses recording 2 which has pending transcript status
        response = client.post("/api/recordings/2/format")

        assert response.status_code == 400
        data = response.json()
        assert "completed transcript" in data["detail"]

        # Verify background task was not added
        mock_format.assert_not_called()
