# ABOUTME: Tests for HTML detail page rendering and functionality
# ABOUTME: Verifies GET /recordings/{id} template rendering and interactive features

import pytest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from mnemovox.app import create_app
from mnemovox.config import Config
from mnemovox.db import init_db, get_session, Recording
from datetime import datetime


@pytest.fixture
def test_app_with_recordings():
    """Create test app with sample recordings for testing detail pages."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create config
        config = Config(
            monitored_directory=str(tmp_path / "monitored"),
            storage_path=str(tmp_path / "storage"),
            upload_temp_path=str(tmp_path / "uploads"),
            items_per_page=20,
        )

        # Create directories
        Path(config.storage_path).mkdir(parents=True, exist_ok=True)

        # Initialize database
        db_path = str(tmp_path / "test.db")
        init_db(db_path)

        # Create sample recordings
        session = get_session(db_path)
        try:
            now = datetime.now()

            # Recording with complete transcript and segments
            complete_recording = Recording(
                original_filename="complete_with_segments.wav",
                internal_filename="1609459200_complete_abcd1234.wav",
                storage_path="2021/01-01/1609459200_complete_abcd1234.wav",
                import_timestamp=now,
                duration_seconds=30.0,
                audio_format="wav",
                sample_rate=44100,
                channels=2,
                file_size_bytes=1536000,
                transcript_status="complete",
                transcript_language="en",
                transcript_text="Hello world. This is a test. Final segment here.",
                transcript_segments=[
                    {
                        "start": 0.0,
                        "end": 5.0,
                        "text": "Hello world.",
                        "confidence": 0.95,
                    },
                    {
                        "start": 5.0,
                        "end": 15.0,
                        "text": "This is a test.",
                        "confidence": 0.92,
                    },
                    {
                        "start": 15.0,
                        "end": 25.0,
                        "text": "Final segment here.",
                        "confidence": 0.88,
                    },
                ],
            )
            session.add(complete_recording)

            # Recording with pending transcript
            pending_recording = Recording(
                original_filename="pending_transcript.mp3",
                internal_filename="1609459200_pending_efgh5678.mp3",
                storage_path="2021/01-01/1609459200_pending_efgh5678.mp3",
                import_timestamp=now,
                duration_seconds=120.0,
                audio_format="mp3",
                sample_rate=22050,
                channels=1,
                file_size_bytes=1024000,
                transcript_status="pending",
            )
            session.add(pending_recording)

            # Recording with error transcript
            error_recording = Recording(
                original_filename="error_transcript.m4a",
                internal_filename="1609459200_error_ijkl9012.m4a",
                storage_path="2021/01-01/1609459200_error_ijkl9012.m4a",
                import_timestamp=now,
                duration_seconds=60.0,
                audio_format="m4a",
                sample_rate=48000,
                channels=2,
                file_size_bytes=2048000,
                transcript_status="error",
            )
            session.add(error_recording)

            # Recording with complete transcript but no segments
            no_segments_recording = Recording(
                original_filename="no_segments.wav",
                internal_filename="1609459200_noseg_mnop3456.wav",
                storage_path="2021/01-01/1609459200_noseg_mnop3456.wav",
                import_timestamp=now,
                duration_seconds=45.0,
                audio_format="wav",
                sample_rate=16000,
                channels=1,
                file_size_bytes=512000,
                transcript_status="complete",
                transcript_language="es",
                transcript_text="Transcript without segments.",
                transcript_segments=None,
            )
            session.add(no_segments_recording)

            session.commit()
        finally:
            session.close()

        # Create app
        app = create_app(config, db_path)
        client = TestClient(app)

        yield client, config, db_path


def test_detail_page_complete_transcript_with_segments(test_app_with_recordings):
    """Test detail page for recording with complete transcript and segments."""
    client, config, db_path = test_app_with_recordings

    response = client.get("/recordings/1")

    assert response.status_code == 200
    html = response.text

    # Check page title
    assert "complete_with_segments.wav" in html

    # Check metadata display
    assert "30.0 seconds" in html
    assert "WAV" in html
    assert "44100 Hz" in html
    assert "2" in html  # channels
    assert "1.5 MB" in html  # file size
    assert "EN" in html  # language

    # Check audio player
    assert 'id="audio-player"' in html
    assert "audio" in html
    assert "controls" in html
    assert "/audio/2021/01-01/1609459200_complete_abcd1234.wav" in html

    # Check interactive transcript elements
    assert "Interactive Transcript" in html
    assert 'id="transcript-text"' in html
    assert 'id="auto-scroll"' in html
    assert 'id="jump-to-current"' in html

    # Check segment table
    assert "Segment Details" in html
    assert "0.0s" in html  # start time
    assert "5.0s" in html  # end time
    assert "Hello world." in html
    assert "95%" in html  # confidence
    assert "play-segment-btn" in html

    # Check JavaScript inclusion
    assert "/static/js/transcript.js" in html
    assert "TranscriptManager" in html
    assert "segments" in html

    # Check back link
    assert "Back to All Recordings" in html


def test_detail_page_pending_transcript(test_app_with_recordings):
    """Test detail page for recording with pending transcript."""
    client, config, db_path = test_app_with_recordings

    response = client.get("/recordings/2")

    assert response.status_code == 200
    html = response.text

    # Check basic metadata
    assert "pending_transcript.mp3" in html
    assert "120.0 seconds" in html
    assert "MP3" in html

    # Check pending transcript display
    assert "Transcription in progress" in html
    assert "⏳" in html
    assert "Please check back in a few minutes" in html
    assert "Refresh Page" in html

    # Should not have interactive elements
    assert "Interactive Transcript" not in html
    assert "Segment Details" not in html
    assert "TranscriptManager" not in html


def test_detail_page_error_transcript(test_app_with_recordings):
    """Test detail page for recording with error transcript."""
    client, config, db_path = test_app_with_recordings

    response = client.get("/recordings/3")

    assert response.status_code == 200
    html = response.text

    # Check basic metadata
    assert "error_transcript.m4a" in html
    assert "60.0 seconds" in html
    assert "M4A" in html

    # Check error transcript display
    assert "Transcription failed" in html
    assert "❌" in html
    assert "corrupted, too long, or in an unsupported format" in html
    assert "Retry Transcription" in html

    # Should not have interactive elements
    assert "Interactive Transcript" not in html
    assert "Segment Details" not in html
    assert "TranscriptManager" not in html


def test_detail_page_complete_no_segments(test_app_with_recordings):
    """Test detail page for recording with transcript but no segments."""
    client, config, db_path = test_app_with_recordings

    response = client.get("/recordings/4")

    assert response.status_code == 200
    html = response.text

    # Check basic metadata
    assert "no_segments.wav" in html
    assert "45.0 seconds" in html
    assert "ES" in html  # language

    # Should show transcript but not interactive features
    assert "Interactive Transcript" in html
    assert "Transcript without segments." in html

    # Should not have segment table or interactive controls
    assert "Segment Details" not in html
    assert 'id="auto-scroll"' not in html
    assert 'id="jump-to-current"' not in html
    assert "▶ Play" not in html  # Play button text shouldn't be present


def test_detail_page_not_found(test_app_with_recordings):
    """Test detail page for non-existent recording."""
    client, config, db_path = test_app_with_recordings

    response = client.get("/recordings/999")

    assert response.status_code == 404


def test_detail_page_audio_mime_types(test_app_with_recordings):
    """Test that audio elements have correct MIME types."""
    client, config, db_path = test_app_with_recordings

    # Test WAV file
    response = client.get("/recordings/1")
    assert 'type="audio/wav"' in response.text

    # Test MP3 file
    response = client.get("/recordings/2")
    assert 'type="audio/mpeg"' in response.text

    # Test M4A file
    response = client.get("/recordings/3")
    assert 'type="audio/mp4"' in response.text


def test_detail_page_file_size_formatting(test_app_with_recordings):
    """Test that file sizes are formatted correctly."""
    client, config, db_path = test_app_with_recordings

    # Test MB formatting (1536000 bytes = 1.5 MB)
    response = client.get("/recordings/1")
    assert "1.5 MB" in response.text

    # Test KB formatting (1024000 bytes = 1000.0 KB, less than 1 MB threshold)
    response = client.get("/recordings/2")
    assert "1000.0 KB" in response.text

    # Test KB formatting (512000 bytes = 500.0 KB)
    response = client.get("/recordings/4")
    assert "500.0 KB" in response.text


def test_detail_page_css_classes(test_app_with_recordings):
    """Test that proper CSS classes are applied for styling."""
    client, config, db_path = test_app_with_recordings

    response = client.get("/recordings/1")
    html = response.text

    # Check CSS classes for interactive elements
    assert "transcript-interactive" in html
    assert "transcript-segment" in html
    assert "segment-row" in html
    assert "confidence" in html
    assert "playing" in html  # CSS for playing state

    # Check confidence level classes
    assert "confidence-high" in html
    assert "confidence-medium" in html


def test_detail_page_javascript_data(test_app_with_recordings):
    """Test that JavaScript receives correct segment data."""
    client, config, db_path = test_app_with_recordings

    response = client.get("/recordings/1")
    html = response.text

    # Check that segment data is passed to JavaScript
    assert '"start": 0.0' in html
    assert '"end": 5.0' in html
    assert '"text": "Hello world."' in html
    assert '"confidence": 0.95' in html

    # Check TranscriptManager initialization
    assert "new TranscriptManager('audio-player', segments)" in html
    assert "transcriptManager.init()" in html


def test_detail_page_segment_table_structure(test_app_with_recordings):
    """Test that segment table has proper structure and data."""
    client, config, db_path = test_app_with_recordings

    response = client.get("/recordings/1")
    html = response.text

    # Check table headers
    assert "<th>Start</th>" in html
    assert "<th>End</th>" in html
    assert "<th>Duration</th>" in html
    assert "<th>Text</th>" in html
    assert "<th>Confidence</th>" in html
    assert "<th>Actions</th>" in html

    # Check segment data attributes
    assert 'data-segment-start="0.0"' in html
    assert 'data-segment-end="5.0"' in html
    assert 'data-start="0.0"' in html  # play button data

    # Check duration calculation (5.0 - 0.0 = 5.0s)
    assert "5.0s" in html


def test_detail_page_responsive_design_elements(test_app_with_recordings):
    """Test that page includes responsive design elements."""
    client, config, db_path = test_app_with_recordings

    response = client.get("/recordings/1")
    html = response.text

    # Check responsive table wrapper
    assert "overflow-x: auto" in html

    # Check that the page has proper HTML structure from base template
    assert "<!DOCTYPE html>" in html
    assert '<html lang="en">' in html


def test_detail_page_navigation(test_app_with_recordings):
    """Test navigation elements on detail page."""
    client, config, db_path = test_app_with_recordings

    response = client.get("/recordings/1")
    html = response.text

    # Check back link
    assert 'href="/recordings"' in html
    assert "&larr; Back to All Recordings" in html

    # Check that it's styled properly
    assert "border-top: 1px solid #eee" in html
