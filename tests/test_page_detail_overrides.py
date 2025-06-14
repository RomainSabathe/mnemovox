# ABOUTME: Tests for recording detail page enhancements with override display and re-transcribe modal
# ABOUTME: Verifies HTML contains current model/language display and re-transcribe button

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from src.audio_manager.app import create_app
from src.audio_manager.config import Config
from src.audio_manager.db import init_db, get_session, Recording


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create test client with temporary database and config."""
    # Create test config
    config = Config(
        monitored_directory=str(tmp_path / "incoming"),
        storage_path=str(tmp_path / "storage"),
        upload_temp_path=str(tmp_path / "uploads"),
        whisper_model="base.en",
        default_language="en",
        sample_rate=16000,
        max_concurrent_transcriptions=2,
        fts_enabled=True,
        items_per_page=20,
    )

    # Create directories
    (tmp_path / "incoming").mkdir()
    (tmp_path / "storage").mkdir()
    (tmp_path / "uploads").mkdir()

    # Initialize database
    db_path = str(tmp_path / "test.db")
    init_db(db_path, fts_enabled=True)

    # Create test app
    app = create_app(config, db_path)

    return TestClient(app)


def test_detail_page_shows_current_model_and_language(client, tmp_path):
    """Test that detail page displays current model and language settings."""
    # Create a test recording with overrides
    db_path = str(tmp_path / "test.db")
    session = get_session(db_path)

    recording = Recording(
        original_filename="test.wav",
        internal_filename="20231201_12345678.wav",
        storage_path="2023/12-01/20231201_12345678.wav",
        import_timestamp=datetime.now(),
        duration_seconds=30.0,
        audio_format="wav",
        sample_rate=16000,
        channels=1,
        file_size_bytes=1024,
        transcript_status="complete",
        transcript_text="Test transcript",
        transcript_language="en",
        transcription_model="small",
        transcription_language="fr",
    )

    session.add(recording)
    session.commit()
    recording_id = recording.id
    session.close()

    # Get the detail page
    response = client.get(f"/recordings/{recording_id}")
    assert response.status_code == 200

    html_content = response.text

    # Check that current model and language are displayed
    assert "Current Model:" in html_content
    assert "Current Language:" in html_content

    # Check that the override values are shown (not defaults)
    assert "small" in html_content  # Override model
    assert "fr" in html_content or "French" in html_content  # Override language


def test_detail_page_shows_global_defaults_when_no_overrides(client, tmp_path):
    """Test that detail page shows global defaults when no overrides are set."""
    # Create a test recording without overrides
    db_path = str(tmp_path / "test.db")
    session = get_session(db_path)

    recording = Recording(
        original_filename="test.wav",
        internal_filename="20231201_12345678.wav",
        storage_path="2023/12-01/20231201_12345678.wav",
        import_timestamp=datetime.now(),
        duration_seconds=30.0,
        audio_format="wav",
        sample_rate=16000,
        channels=1,
        file_size_bytes=1024,
        transcript_status="complete",
        transcript_text="Test transcript",
        transcript_language="en",
        transcription_model=None,  # No override
        transcription_language=None,  # No override
    )

    session.add(recording)
    session.commit()
    recording_id = recording.id
    session.close()

    # Get the detail page
    response = client.get(f"/recordings/{recording_id}")
    assert response.status_code == 200

    html_content = response.text

    # Check that current model and language are displayed
    assert "Current Model:" in html_content
    assert "Current Language:" in html_content

    # Check that the global defaults are shown
    assert "base.en" in html_content  # Global default model
    assert "en" in html_content or "English" in html_content  # Global default language


def test_detail_page_contains_retranscribe_button(client, tmp_path):
    """Test that detail page contains re-transcribe button."""
    # Create a test recording
    db_path = str(tmp_path / "test.db")
    session = get_session(db_path)

    recording = Recording(
        original_filename="test.wav",
        internal_filename="20231201_12345678.wav",
        storage_path="2023/12-01/20231201_12345678.wav",
        import_timestamp=datetime.now(),
        duration_seconds=30.0,
        audio_format="wav",
        sample_rate=16000,
        channels=1,
        file_size_bytes=1024,
        transcript_status="complete",
        transcript_text="Test transcript",
        transcript_language="en",
    )

    session.add(recording)
    session.commit()
    recording_id = recording.id
    session.close()

    # Get the detail page
    response = client.get(f"/recordings/{recording_id}")
    assert response.status_code == 200

    html_content = response.text

    # Check that re-transcribe button exists
    assert 'id="btn-retranscribe"' in html_content
    assert "Re-transcribe" in html_content


def test_detail_page_contains_retranscribe_modal(client, tmp_path):
    """Test that detail page contains the re-transcribe modal structure."""
    # Create a test recording
    db_path = str(tmp_path / "test.db")
    session = get_session(db_path)

    recording = Recording(
        original_filename="test.wav",
        internal_filename="20231201_12345678.wav",
        storage_path="2023/12-01/20231201_12345678.wav",
        import_timestamp=datetime.now(),
        duration_seconds=30.0,
        audio_format="wav",
        sample_rate=16000,
        channels=1,
        file_size_bytes=1024,
        transcript_status="complete",
        transcript_text="Test transcript",
        transcript_language="en",
    )

    session.add(recording)
    session.commit()
    recording_id = recording.id
    session.close()

    # Get the detail page
    response = client.get(f"/recordings/{recording_id}")
    assert response.status_code == 200

    html_content = response.text

    # Check that modal structure exists
    assert 'id="retranscribe-modal"' in html_content
    assert "Warning: this will overwrite the existing transcript" in html_content

    # Check that modal has the required form elements
    assert 'id="modal-model-select"' in html_content
    assert 'id="modal-language-select"' in html_content


def test_detail_page_includes_retranscribe_js(client, tmp_path):
    """Test that detail page includes the retranscribe JavaScript file."""
    # Create a test recording
    db_path = str(tmp_path / "test.db")
    session = get_session(db_path)

    recording = Recording(
        original_filename="test.wav",
        internal_filename="20231201_12345678.wav",
        storage_path="2023/12-01/20231201_12345678.wav",
        import_timestamp=datetime.now(),
        duration_seconds=30.0,
        audio_format="wav",
        sample_rate=16000,
        channels=1,
        file_size_bytes=1024,
        transcript_status="complete",
        transcript_text="Test transcript",
        transcript_language="en",
    )

    session.add(recording)
    session.commit()
    recording_id = recording.id
    session.close()

    # Get the detail page
    response = client.get(f"/recordings/{recording_id}")
    assert response.status_code == 200

    html_content = response.text

    # Check that retranscribe.js is included
    assert 'src="/static/js/retranscribe.js"' in html_content
