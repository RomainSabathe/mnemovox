# ABOUTME: Tests for API upload endpoint
# ABOUTME: Verifies file upload functionality and integration with ingestion pipeline

import pytest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from src.audio_manager.app import create_app
from src.audio_manager.config import Config
from src.audio_manager.db import init_db, get_session, Recording


def test_upload_valid_audio_file():
    """Test uploading a valid audio file returns 201 with JSON response."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create config
        config = Config(
            monitored_directory=str(tmp_path / "monitored"),
            storage_path=str(tmp_path / "storage"),
            upload_temp_path=str(tmp_path / "uploads"),
        )

        # Create directories
        config.monitored_directory = Path(config.monitored_directory)
        config.monitored_directory.mkdir(exist_ok=True)
        Path(config.storage_path).mkdir(parents=True, exist_ok=True)
        Path(config.upload_temp_path).mkdir(parents=True, exist_ok=True)

        # Initialize database
        db_path = str(tmp_path / "test.db")
        init_db(db_path)

        # Create app
        app = create_app(config, db_path)
        client = TestClient(app)

        # Create a test audio file
        test_file_content = b"fake wav content"

        # Upload the file
        response = client.post(
            "/api/recordings/upload",
            files={"file": ("test_audio.wav", test_file_content, "audio/wav")},
        )

        # Should return 201 Created with JSON response
        if response.status_code != 201:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
        assert response.status_code == 201
        response_data = response.json()
        assert "id" in response_data
        assert response_data["status"] == "pending"
        assert isinstance(response_data["id"], int)


def test_upload_invalid_file_extension():
    """Test uploading file with invalid extension returns 400 error."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create config
        config = Config(
            monitored_directory=str(tmp_path / "monitored"),
            storage_path=str(tmp_path / "storage"),
            upload_temp_path=str(tmp_path / "uploads"),
        )

        # Create directories
        Path(config.upload_temp_path).mkdir(parents=True, exist_ok=True)

        # Initialize database
        db_path = str(tmp_path / "test.db")
        init_db(db_path)

        # Create app
        app = create_app(config, db_path)
        client = TestClient(app)

        # Try to upload a non-audio file
        test_file_content = b"not an audio file"

        response = client.post(
            "/api/recordings/upload",
            files={"file": ("document.txt", test_file_content, "text/plain")},
        )

        # Should return 400 Bad Request
        assert response.status_code == 400
        response_data = response.json()
        assert "detail" in response_data
        assert "error" in response_data["detail"]
        assert "extension" in response_data["detail"]["error"].lower()


def test_upload_missing_file():
    """Test upload request without file returns 422 error."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create config
        config = Config(
            upload_temp_path=str(tmp_path / "uploads"),
        )

        # Initialize database
        db_path = str(tmp_path / "test.db")
        init_db(db_path)

        # Create app
        app = create_app(config, db_path)
        client = TestClient(app)

        # Try to upload without file
        response = client.post("/api/recordings/upload")

        # Should return 422 Unprocessable Entity
        assert response.status_code == 422


def test_upload_integration_with_database():
    """Integration test: verify uploaded file is processed and stored in database."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create config
        config = Config(
            monitored_directory=str(tmp_path / "monitored"),
            storage_path=str(tmp_path / "storage"),
            upload_temp_path=str(tmp_path / "uploads"),
        )

        # Create directories
        Path(config.monitored_directory).mkdir(exist_ok=True)
        Path(config.storage_path).mkdir(parents=True, exist_ok=True)
        Path(config.upload_temp_path).mkdir(parents=True, exist_ok=True)

        # Initialize database
        db_path = str(tmp_path / "test.db")
        init_db(db_path)

        # Create app
        app = create_app(config, db_path)
        client = TestClient(app)

        # Create a realistic test audio file (copy from test assets)
        test_asset_path = Path("tests/assets/this_is_a_test.wav")
        if test_asset_path.exists():
            with open(test_asset_path, "rb") as f:
                test_file_content = f.read()
        else:
            # Fallback to fake content
            test_file_content = b"fake wav content"

        # Upload the file
        response = client.post(
            "/api/recordings/upload",
            files={"file": ("integration_test.wav", test_file_content, "audio/wav")},
        )

        # Should succeed
        assert response.status_code == 201
        response_data = response.json()
        recording_id = response_data["id"]

        # Verify database record was created
        session = get_session(db_path)
        try:
            recording = (
                session.query(Recording).filter(Recording.id == recording_id).first()
            )
            assert recording is not None
            assert recording.original_filename == "integration_test.wav"
            assert recording.transcript_status == "pending"
            # File should have been moved to storage
            assert Path(recording.storage_path).exists()
        finally:
            session.close()


def test_upload_multiple_file_types():
    """Test uploading different valid audio file types."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create config
        config = Config(
            monitored_directory=str(tmp_path / "monitored"),
            storage_path=str(tmp_path / "storage"),
            upload_temp_path=str(tmp_path / "uploads"),
        )

        # Create directories
        Path(config.monitored_directory).mkdir(exist_ok=True)
        Path(config.storage_path).mkdir(parents=True, exist_ok=True)
        Path(config.upload_temp_path).mkdir(parents=True, exist_ok=True)

        # Initialize database
        db_path = str(tmp_path / "test.db")
        init_db(db_path)

        # Create app
        app = create_app(config, db_path)
        client = TestClient(app)

        # Test different audio file extensions
        test_files = [
            ("test.wav", "audio/wav"),
            ("test.mp3", "audio/mpeg"),
            ("test.m4a", "audio/mp4"),
        ]

        for filename, content_type in test_files:
            test_file_content = b"fake audio content"

            response = client.post(
                "/api/recordings/upload",
                files={"file": (filename, test_file_content, content_type)},
            )

            assert response.status_code == 201, f"Failed for {filename}"
            response_data = response.json()
            assert "id" in response_data
            assert response_data["status"] == "pending"


@pytest.mark.integration
def test_upload_real_audio_file_with_metadata():
    """Integration test: upload real audio file and verify metadata extraction."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create config
        config = Config(
            monitored_directory=str(tmp_path / "monitored"),
            storage_path=str(tmp_path / "storage"),
            upload_temp_path=str(tmp_path / "uploads"),
        )

        # Create directories
        Path(config.monitored_directory).mkdir(exist_ok=True)
        Path(config.storage_path).mkdir(parents=True, exist_ok=True)
        Path(config.upload_temp_path).mkdir(parents=True, exist_ok=True)

        # Initialize database
        db_path = str(tmp_path / "test.db")
        init_db(db_path)

        # Create app
        app = create_app(config, db_path)
        client = TestClient(app)

        # Load real audio file
        test_audio_path = Path(__file__).parent / "assets" / "this_is_a_test.wav"
        assert test_audio_path.exists(), f"Test audio file not found: {test_audio_path}"

        with open(test_audio_path, "rb") as f:
            test_file_content = f.read()

        # Upload the real audio file
        response = client.post(
            "/api/recordings/upload",
            files={"file": ("real_audio_test.wav", test_file_content, "audio/wav")},
        )

        # Should succeed
        assert response.status_code == 201
        response_data = response.json()
        recording_id = response_data["id"]

        # Verify database record was created with real metadata
        session = get_session(db_path)
        try:
            recording = (
                session.query(Recording).filter(Recording.id == recording_id).first()
            )
            assert recording is not None
            assert recording.original_filename == "real_audio_test.wav"
            assert recording.transcript_status == "pending"

            # Verify file was moved to storage with correct structure
            storage_path = Path(recording.storage_path)
            assert storage_path.exists()
            assert storage_path.name.endswith(".wav")

            # Verify real metadata was extracted
            assert recording.duration_seconds is not None
            assert recording.duration_seconds > 0
            assert recording.audio_format is not None
            assert recording.sample_rate is not None
            assert recording.channels is not None
            assert recording.file_size_bytes is not None
            assert recording.file_size_bytes > 0

            # Verify reasonable values for the test audio file
            assert 0.5 <= recording.duration_seconds <= 10.0
            assert recording.channels in [1, 2]  # mono or stereo
            assert 8000 <= recording.sample_rate <= 96000

            # File size should match original
            assert recording.file_size_bytes == len(test_file_content)

        finally:
            session.close()
