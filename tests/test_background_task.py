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

        # Define a base storage directory for this test
        test_storage_base_dir = tmp_path / "test_audio_storage"
        test_storage_base_dir.mkdir(parents=True, exist_ok=True)

        # Define a relative path for the audio file as it would be in the DB
        relative_audio_path_in_db = "audio_files/test_audio.wav"

        # Create the actual dummy audio file at its absolute location
        actual_audio_file_on_disk = test_storage_base_dir / relative_audio_path_in_db
        actual_audio_file_on_disk.parent.mkdir(parents=True, exist_ok=True)
        actual_audio_file_on_disk.write_bytes(b"dummy audio data")

        # Create a test recording in the database with a relative storage path
        session = get_session(db_path)
        try:
            recording = Recording(
                original_filename="test_audio.wav",
                internal_filename="test_internal.wav",
                storage_path=relative_audio_path_in_db,  # Store relative path
                import_timestamp=datetime.now(),
                duration_seconds=10.0,
                audio_format="wav",
                sample_rate=44100,
                channels=2,
                file_size_bytes=1000,
                transcript_status="pending",
                transcription_model="tiny",  # Override model
                transcription_language="fr",  # Override language
            )

            session.add(recording)
            session.commit()
            recording_id = recording.id
        finally:
            session.close()

        # Mock transcriber.transcribe_file to return known results including detected language
        mock_transcript_text = "Ceci est une transcription de test"
        mock_segments = [
            {"start": 0.0, "end": 2.0, "text": "Ceci est", "confidence": 0.9},
            {
                "start": 2.0,
                "end": 5.0,
                "text": "une transcription de test",
                "confidence": 0.8,
            },
        ]
        mock_detected_language = "fr"  # Should match the override
        mock_result = (mock_transcript_text, mock_segments, mock_detected_language)

        # Mock get_config to return a Config object with our test_storage_base_dir
        # and default model/language that are different from the overrides
        mock_app_config = Config(
            storage_path=str(test_storage_base_dir),
            monitored_directory=str(tmp_path / "monitored"),
            upload_temp_path=str(tmp_path / "uploads"),
            whisper_model="base.en",  # Default model
            default_language="en",  # Default language
            items_per_page=10,  # Dummy value
            fts_enabled=True,  # Dummy value
            max_concurrent_transcriptions=1,  # Dummy value
            sample_rate=16000,  # Dummy value
        )

        mock_transcribe_file_func = MagicMock(return_value=mock_result)
        with patch(
            "src.audio_manager.app.get_config", return_value=mock_app_config
        ), patch(
            "src.audio_manager.transcriber.transcribe_file", mock_transcribe_file_func
        ):
            # Run the background task
            run_transcription_task(recording_id, db_path)

        # Assert that transcribe_file was called with the correct absolute path, model, and language
        expected_model_override = "tiny"
        expected_language_override = "fr"
        mock_transcribe_file_func.assert_called_once_with(
            str(actual_audio_file_on_disk),  # path
            model_name=expected_model_override,  # overridden model
            language=expected_language_override,  # overridden language
        )

        # Verify database was updated
        session = get_session(db_path)
        try:
            recording = session.query(Recording).filter_by(id=recording_id).first()
            assert recording is not None
            assert recording.transcript_status == "complete"
            assert recording.transcript_text == mock_transcript_text
            assert recording.transcript_segments == mock_segments
            assert (
                recording.transcript_language == mock_detected_language
            )  # Check detected language from mock
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

        # For this test, we'll use an absolute path in the DB to ensure that logic is also handled.
        # The main test `test_run_transcription_updates_database` covers relative paths.
        absolute_storage_path = tmp_path / "audio.wav"
        absolute_storage_path.write_bytes(b"dummy audio for exception test")

        # Create a test recording
        session = get_session(db_path)
        try:
            recording = Recording(
                original_filename="test_audio.wav",
                internal_filename="test_internal.wav",
                storage_path=str(absolute_storage_path),  # Store absolute path
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
        # The transcribe_file mock now needs to account for the new signature if its side_effect is complex,
        # but for a simple Exception, it's fine.
        with patch(
            "src.audio_manager.transcriber.transcribe_file",
            side_effect=Exception("Transcription failed"),
        ), patch(
            "src.audio_manager.app.get_config",
            return_value=Config(
                storage_path=str(tmp_path),
                monitored_directory=str(tmp_path / "monitored"),
                upload_temp_path=str(tmp_path / "uploads"),
                whisper_model="base.en",
                default_language="en",
                items_per_page=10,
                fts_enabled=True,
                max_concurrent_transcriptions=1,
                sample_rate=16000,
            ),
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

        # Using an absolute path in DB for this test.
        absolute_storage_path_for_fts = tmp_path / "audio_for_fts.wav"
        absolute_storage_path_for_fts.write_bytes(b"dummy audio for fts test")

        # Create a test recording
        session = get_session(db_path)
        try:
            recording = Recording(
                original_filename="test_audio.wav",
                internal_filename="test_internal.wav",
                storage_path=str(absolute_storage_path_for_fts),  # Store absolute path
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
        mock_result_fts = ("Test transcript for FTS", [], "en")  # 3-tuple
        mock_sync_fts = MagicMock()

        with (
            patch(
                "src.audio_manager.transcriber.transcribe_file",
                return_value=mock_result_fts,
            ),
            patch("src.audio_manager.app.sync_fts", mock_sync_fts),
            patch(
                "src.audio_manager.app.get_config",
                return_value=Config(
                    storage_path=str(tmp_path),
                    monitored_directory=str(tmp_path / "monitored"),
                    upload_temp_path=str(tmp_path / "uploads"),
                    whisper_model="base.en",
                    default_language="en",
                    items_per_page=10,
                    fts_enabled=True,
                    max_concurrent_transcriptions=1,
                    sample_rate=16000,
                ),
            ),
        ):
            # Run the background task
            run_transcription_task(recording_id, db_path)

            # Verify sync_fts was called
            mock_sync_fts.assert_called_once()
            # Check that it was called with a session and the recording_id
            args = mock_sync_fts.call_args[0]
            assert args[1] == recording_id  # Second arg should be recording_id
