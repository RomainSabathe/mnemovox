# ABOUTME: Integration tests for complete recording deletion workflow
# ABOUTME: Tests both frontend templates and backend API for deletion functionality

import tempfile
from pathlib import Path
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from mnemovox.app import create_app
from mnemovox.config import Config
from mnemovox.db import Recording, get_session, init_db


@pytest.fixture
def test_app_with_recording():
    """Create test app with a sample recording for deletion testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create config
        config = Config(
            storage_path=str(tmp_path / "storage"),
            items_per_page=10,
        )

        # Create directories
        storage_path = Path(config.storage_path)
        storage_path.mkdir(parents=True, exist_ok=True)

        # Create a fake audio file
        audio_file_path = storage_path / "2025" / "07-20" / "test_recording.wav"
        audio_file_path.parent.mkdir(parents=True, exist_ok=True)
        audio_file_path.write_text("fake audio content")

        # Initialize database
        db_path = str(tmp_path / "test.db")
        init_db(db_path)

        # Create test recording
        session = get_session(db_path)
        try:
            recording = Recording(
                original_filename="test_recording.wav",
                internal_filename="test_recording_internal.wav",
                storage_path="2025/07-20/test_recording.wav",
                import_timestamp=datetime.now(),
                transcript_status="complete",
                transcript_text="This is a test recording transcript.",
            )

            session.add(recording)
            session.commit()
            session.refresh(recording)  # Get the ID
            recording_id = recording.id

            # Setup FTS index
            from mnemovox.db import sync_fts

            sync_fts(session, recording_id)

        finally:
            session.close()

        # Create app
        app = create_app(config, db_path)
        client = TestClient(app)

        yield client, config, db_path, recording_id, audio_file_path


def test_recordings_list_page_has_delete_button(test_app_with_recording):
    """Test that recordings list page contains delete button with correct onclick handler."""
    client, config, db_path, recording_id, audio_file_path = test_app_with_recording

    # Get the recordings list page
    response = client.get("/recordings")
    assert response.status_code == 200
    html = response.text

    # Should contain delete button
    assert "Delete" in html
    assert "deleteRecording" in html
    assert f"deleteRecording({recording_id}," in html
    assert "test_recording.wav" in html

    # Should contain confirmation dialog
    assert "Are you sure you want to delete" in html


def test_recording_detail_page_has_delete_button(test_app_with_recording):
    """Test that recording detail page contains delete button with correct onclick handler."""
    client, config, db_path, recording_id, audio_file_path = test_app_with_recording

    # Get the recording detail page
    response = client.get(f"/recordings/{recording_id}")
    assert response.status_code == 200
    html = response.text

    # Should contain delete button
    assert "🗑️ Delete Recording" in html
    assert "deleteRecordingDetail" in html
    assert f"deleteRecordingDetail({recording_id}," in html
    assert "test_recording.wav" in html

    # Should contain confirmation dialog
    assert "Are you sure you want to delete" in html


def test_complete_delete_workflow_from_list_page(test_app_with_recording):
    """Test complete deletion workflow starting from recordings list."""
    client, config, db_path, recording_id, audio_file_path = test_app_with_recording

    # Verify recording exists on list page
    response = client.get("/recordings")
    assert response.status_code == 200
    assert "test_recording.wav" in response.text

    # Verify file exists
    assert audio_file_path.exists()

    # Delete via API (simulating frontend JavaScript call)
    delete_response = client.delete(f"/api/recordings/{recording_id}")
    assert delete_response.status_code == 204

    # Verify recording no longer appears on list page
    response = client.get("/recordings")
    assert response.status_code == 200
    assert "test_recording.wav" not in response.text

    # Verify file is deleted
    assert not audio_file_path.exists()


def test_complete_delete_workflow_from_detail_page(test_app_with_recording):
    """Test complete deletion workflow starting from detail page."""
    client, config, db_path, recording_id, audio_file_path = test_app_with_recording

    # Verify recording detail page works
    response = client.get(f"/recordings/{recording_id}")
    assert response.status_code == 200
    assert "test_recording.wav" in response.text

    # Verify file exists
    assert audio_file_path.exists()

    # Delete via API (simulating frontend JavaScript call)
    delete_response = client.delete(f"/api/recordings/{recording_id}")
    assert delete_response.status_code == 204

    # Verify detail page returns 404
    response = client.get(f"/recordings/{recording_id}")
    assert response.status_code == 404

    # Verify file is deleted
    assert not audio_file_path.exists()


def test_delete_button_javascript_functions_exist(test_app_with_recording):
    """Test that the required JavaScript functions are present in templates."""
    client, config, db_path, recording_id, audio_file_path = test_app_with_recording

    # Check recordings list page
    response = client.get("/recordings")
    assert response.status_code == 200
    list_html = response.text

    # Should contain deleteRecording function
    assert "function deleteRecording" in list_html
    assert "fetch(`/api/recordings/${recordingId}`" in list_html
    assert "method: 'DELETE'" in list_html
    assert "window.location.reload()" in list_html

    # Check recording detail page
    response = client.get(f"/recordings/{recording_id}")
    assert response.status_code == 200
    detail_html = response.text

    # Should contain deleteRecordingDetail function
    assert "function deleteRecordingDetail" in detail_html
    assert "fetch(`/api/recordings/${recordingId}`" in detail_html
    assert "method: 'DELETE'" in detail_html
    assert "window.location.href = '/recordings'" in detail_html


def test_delete_buttons_styling_and_confirmation(test_app_with_recording):
    """Test that delete buttons have proper styling and confirmation dialogs."""
    client, config, db_path, recording_id, audio_file_path = test_app_with_recording

    # Check recordings list page styling
    response = client.get("/recordings")
    list_html = response.text

    # Delete button should have red styling
    assert "background-color: #dc3545" in list_html
    assert "color: white" in list_html

    # Should have confirmation with filename
    assert "confirm(" in list_html
    assert "This action cannot be undone" in list_html

    # Check recording detail page styling
    response = client.get(f"/recordings/{recording_id}")
    detail_html = response.text

    # Delete button should have red styling and emoji
    assert "🗑️ Delete Recording" in detail_html
    assert "background-color: #dc3545" in detail_html
    assert "color: white" in detail_html
