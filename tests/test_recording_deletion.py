# ABOUTME: Tests for recording deletion functionality
# ABOUTME: Verifies DELETE /api/recordings/{id} endpoint removes database records and files

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


def test_delete_recording_success(test_app_with_recording):
    """Test successful deletion of a recording."""
    client, config, db_path, recording_id, audio_file_path = test_app_with_recording

    # Verify recording exists before deletion
    response = client.get(f"/api/recordings/{recording_id}")
    assert response.status_code == 200

    # Verify file exists before deletion
    assert audio_file_path.exists()

    # Delete the recording
    response = client.delete(f"/api/recordings/{recording_id}")

    # Should return 204 No Content on successful deletion
    assert response.status_code == 204

    # Verify recording is deleted from database
    response = client.get(f"/api/recordings/{recording_id}")
    assert response.status_code == 404

    # Verify file is deleted from filesystem
    assert not audio_file_path.exists()


def test_delete_recording_not_found(test_app_with_recording):
    """Test deletion of non-existent recording returns 404."""
    client, config, db_path, recording_id, audio_file_path = test_app_with_recording

    # Try to delete non-existent recording
    response = client.delete("/api/recordings/99999")

    assert response.status_code == 404
    assert "detail" in response.json()


def test_delete_recording_removes_from_fts(test_app_with_recording):
    """Test that deletion removes recording from FTS index."""
    client, config, db_path, recording_id, audio_file_path = test_app_with_recording

    # Verify recording is searchable before deletion
    response = client.get("/api/search?q=test")
    assert response.status_code == 200
    data = response.json()
    assert data["pagination"]["total"] > 0

    # Delete the recording
    response = client.delete(f"/api/recordings/{recording_id}")
    assert response.status_code == 204

    # Verify recording is no longer in search results
    response = client.get("/api/search?q=test")
    assert response.status_code == 200
    data = response.json()
    assert data["pagination"]["total"] == 0


def test_delete_recording_file_missing_still_deletes_database(test_app_with_recording):
    """Test that deletion works even if file is already missing."""
    client, config, db_path, recording_id, audio_file_path = test_app_with_recording

    # Remove the file manually
    audio_file_path.unlink()
    assert not audio_file_path.exists()

    # Delete the recording should still work
    response = client.delete(f"/api/recordings/{recording_id}")
    assert response.status_code == 204

    # Verify recording is deleted from database
    response = client.get(f"/api/recordings/{recording_id}")
    assert response.status_code == 404


def test_delete_recording_invalid_id_format(test_app_with_recording):
    """Test deletion with invalid ID format returns 422."""
    client, config, db_path, recording_id, audio_file_path = test_app_with_recording

    # Try to delete with invalid ID format
    response = client.delete("/api/recordings/not-a-number")

    assert response.status_code == 422  # Validation error


def test_delete_recording_negative_id(test_app_with_recording):
    """Test deletion with negative ID returns 404."""
    client, config, db_path, recording_id, audio_file_path = test_app_with_recording

    # Try to delete with negative ID
    response = client.delete("/api/recordings/-1")

    assert response.status_code == 404
    assert "detail" in response.json()


def test_delete_recording_zero_id(test_app_with_recording):
    """Test deletion with zero ID returns 404."""
    client, config, db_path, recording_id, audio_file_path = test_app_with_recording

    # Try to delete with zero ID
    response = client.delete("/api/recordings/0")

    assert response.status_code == 404
    assert "detail" in response.json()


def test_delete_recording_very_large_id(test_app_with_recording):
    """Test deletion with very large ID returns 404."""
    client, config, db_path, recording_id, audio_file_path = test_app_with_recording

    # Try to delete with very large ID
    response = client.delete("/api/recordings/999999999999")

    assert response.status_code == 404
    assert "detail" in response.json()


def test_delete_recording_twice_returns_404_second_time(test_app_with_recording):
    """Test that deleting the same recording twice returns 404 on second attempt."""
    client, config, db_path, recording_id, audio_file_path = test_app_with_recording

    # First deletion should succeed
    response = client.delete(f"/api/recordings/{recording_id}")
    assert response.status_code == 204

    # Second deletion should return 404
    response = client.delete(f"/api/recordings/{recording_id}")
    assert response.status_code == 404
    assert "detail" in response.json()


def test_delete_recording_with_special_filename_characters(test_app_with_recording):
    """Test deletion works with special characters in filename."""
    client, config, db_path, recording_id, audio_file_path = test_app_with_recording

    # Update recording with special characters in filename
    from mnemovox.db import get_session, Recording

    session = get_session(db_path)
    try:
        recording = session.query(Recording).filter_by(id=recording_id).first()
        recording.original_filename = "test file with spaces & special chars (123).wav"
        session.commit()
    finally:
        session.close()

    # Deletion should still work
    response = client.delete(f"/api/recordings/{recording_id}")
    assert response.status_code == 204

    # Verify deletion
    response = client.get(f"/api/recordings/{recording_id}")
    assert response.status_code == 404


def test_delete_recording_preserves_other_recordings(test_app_with_recording):
    """Test that deleting one recording doesn't affect others."""
    client, config, db_path, recording_id, audio_file_path = test_app_with_recording

    # Create a second recording
    from mnemovox.db import get_session, Recording, sync_fts
    from datetime import datetime

    # Create another fake audio file
    storage_path = Path(config.storage_path)
    second_audio_file = storage_path / "2025" / "07-20" / "second_recording.wav"
    second_audio_file.write_text("second fake audio content")

    session = get_session(db_path)
    try:
        second_recording = Recording(
            original_filename="second_recording.wav",
            internal_filename="second_recording_internal.wav",
            storage_path="2025/07-20/second_recording.wav",
            import_timestamp=datetime.now(),
            transcript_status="complete",
            transcript_text="This is a second test recording transcript.",
        )

        session.add(second_recording)
        session.commit()
        session.refresh(second_recording)
        second_recording_id = second_recording.id
        sync_fts(session, second_recording_id)
    finally:
        session.close()

    # Delete the first recording
    response = client.delete(f"/api/recordings/{recording_id}")
    assert response.status_code == 204

    # Verify first recording is deleted
    response = client.get(f"/api/recordings/{recording_id}")
    assert response.status_code == 404

    # Verify second recording still exists
    response = client.get(f"/api/recordings/{second_recording_id}")
    assert response.status_code == 200
    assert second_audio_file.exists()

    # Verify first file is deleted but second exists
    assert not audio_file_path.exists()
    assert second_audio_file.exists()
