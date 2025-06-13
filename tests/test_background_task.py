# ABOUTME: Tests for background task orchestration between ingestion and transcription
# ABOUTME: Verifies that background tasks properly update DB status, text, segments, and sync FTS

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.audio_manager.config import Config
from src.audio_manager.db import init_db, get_session, Recording
from src.audio_manager.app import create_app, run_transcription_task
from fastapi.testclient import TestClient
from datetime import datetime


def test_run_transcription_updates_database():
    """Test that run_transcription(id) updates DB status/text/segments."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_path = str(tmp_path / "test.db")

        # Initialize database
        init_db(db_path, fts_enabled=True)

        # Create a test recording in the database
        session = get_session(db_path)
        try:
            # Create storage directory and dummy audio file
            storage_path = tmp_path / "audio.wav"
            storage_path.write_bytes(b"dummy audio")

            recording = Recording(
                original_filename="test_audio.wav",
                internal_filename="test_internal.wav",
                storage_path=str(storage_path),
                import_timestamp=datetime.now(),
                duration_seconds=10.0,
                audio_format="wav",
                sample_rate=44100,
                channels=2,
                file_size_bytes=1000,
                transcript_status="pending",
            )

            session.add(recording)
            session.commit()
            recording_id = recording.id
        finally:
            session.close()

        # Mock transcriber.transcribe_file to return known results
        mock_result = (
            "This is a test transcript",
            [
                {"start": 0.0, "end": 2.0, "text": "This is", "confidence": 0.9},
                {
                    "start": 2.0,
                    "end": 5.0,
                    "text": "a test transcript",
                    "confidence": 0.8,
                },
            ],
        )

        with patch(
            "src.audio_manager.transcriber.transcribe_file", return_value=mock_result
        ):
            # Run the background task
            run_transcription_task(recording_id, db_path)

        # Verify database was updated
        session = get_session(db_path)
        try:
            recording = session.query(Recording).filter_by(id=recording_id).first()
            assert recording is not None
            assert recording.transcript_status == "complete"
            assert recording.transcript_text == "This is a test transcript"
            assert recording.transcript_segments == mock_result[1]
            assert recording.transcript_language == "en"
            assert recording.updated_at is not None
        finally:
            session.close()


def test_run_transcription_handles_exception():
    """Test that run_transcription sets status='error' on exception."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_path = str(tmp_path / "test.db")

        # Initialize database
        init_db(db_path, fts_enabled=True)

        # Create a test recording
        session = get_session(db_path)
        try:
            storage_path = tmp_path / "audio.wav"
            storage_path.write_bytes(b"dummy audio")

            recording = Recording(
                original_filename="test_audio.wav",
                internal_filename="test_internal.wav",
                storage_path=str(storage_path),
                import_timestamp=datetime.now(),
                duration_seconds=10.0,
                audio_format="wav",
                sample_rate=44100,
                channels=2,
                file_size_bytes=1000,
                transcript_status="pending",
            )

            session.add(recording)
            session.commit()
            recording_id = recording.id
        finally:
            session.close()

        # Mock transcriber to raise an exception
        with patch(
            "src.audio_manager.transcriber.transcribe_file",
            side_effect=Exception("Transcription failed"),
        ):
            # Run the background task
            run_transcription_task(recording_id, db_path)

        # Verify status was set to error
        session = get_session(db_path)
        try:
            recording = session.query(Recording).filter_by(id=recording_id).first()
            assert recording is not None
            assert recording.transcript_status == "error"
            assert recording.updated_at is not None
        finally:
            session.close()


def test_background_task_wired_in_upload():
    """Test that upload endpoint triggers background transcription task."""
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
        Path(config.upload_temp_path).mkdir(parents=True, exist_ok=True)

        # Initialize database
        db_path = str(tmp_path / "test.db")
        init_db(db_path, fts_enabled=True)

        # Create app
        app = create_app(config, db_path)

        # Mock the background task runner to track calls
        mock_add_task = MagicMock()

        with patch("fastapi.BackgroundTasks.add_task", mock_add_task):
            client = TestClient(app)

            # Upload a file
            response = client.post(
                "/api/recordings/upload",
                files={"file": ("test.wav", b"fake audio", "audio/wav")},
            )

            assert response.status_code == 201

            # Verify background task was added
            mock_add_task.assert_called_once()
            args = mock_add_task.call_args[0]
            assert args[0] == run_transcription_task  # First arg is the function
            assert isinstance(args[1], int)  # Second arg is recording_id
            assert args[2] == db_path  # Third arg is db_path


def test_background_task_wired_in_retranscribe():
    """Test that retranscribe endpoint triggers background task."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create config
        config = Config(
            monitored_directory=str(tmp_path / "monitored"),
            storage_path=str(tmp_path / "storage"),
            upload_temp_path=str(tmp_path / "uploads"),
        )

        # Initialize database and create test recording
        db_path = str(tmp_path / "test.db")
        init_db(db_path, fts_enabled=True)

        session = get_session(db_path)
        try:
            recording = Recording(
                original_filename="existing.wav",
                internal_filename="existing_internal.wav",
                storage_path=str(tmp_path / "existing.wav"),
                import_timestamp=datetime.now(),
                duration_seconds=10.0,
                audio_format="wav",
                sample_rate=44100,
                channels=2,
                file_size_bytes=1000,
                transcript_status="complete",
                transcript_text="old transcript",
            )

            session.add(recording)
            session.commit()
            recording_id = recording.id
        finally:
            session.close()

        # Create app
        app = create_app(config, db_path)

        # Mock the background task runner
        mock_add_task = MagicMock()

        with patch("fastapi.BackgroundTasks.add_task", mock_add_task):
            client = TestClient(app)

            # Trigger retranscription
            response = client.post(f"/api/recordings/{recording_id}/transcribe")

            assert response.status_code == 200

            # Verify background task was added
            mock_add_task.assert_called_once()
            args = mock_add_task.call_args[0]
            assert args[0] == run_transcription_task
            assert args[1] == recording_id
            assert args[2] == db_path


def test_background_task_syncs_fts():
    """Test that background task calls sync_fts after successful transcription."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_path = str(tmp_path / "test.db")

        # Initialize database
        init_db(db_path, fts_enabled=True)

        # Create a test recording
        session = get_session(db_path)
        try:
            storage_path = tmp_path / "audio.wav"
            storage_path.write_bytes(b"dummy audio")

            recording = Recording(
                original_filename="test_audio.wav",
                internal_filename="test_internal.wav",
                storage_path=str(storage_path),
                import_timestamp=datetime.now(),
                duration_seconds=10.0,
                audio_format="wav",
                sample_rate=44100,
                channels=2,
                file_size_bytes=1000,
                transcript_status="pending",
            )

            session.add(recording)
            session.commit()
            recording_id = recording.id
        finally:
            session.close()

        # Mock transcriber and sync_fts
        mock_result = ("Test transcript", [])
        mock_sync_fts = MagicMock()

        with (
            patch(
                "src.audio_manager.transcriber.transcribe_file",
                return_value=mock_result,
            ),
            patch("src.audio_manager.app.sync_fts", mock_sync_fts),
        ):
            # Run the background task
            run_transcription_task(recording_id, db_path)

            # Verify sync_fts was called
            mock_sync_fts.assert_called_once()
            # Check that it was called with a session and the recording_id
            args = mock_sync_fts.call_args[0]
            assert args[1] == recording_id  # Second arg should be recording_id
