# ABOUTME: Tests for audio utilities module
# ABOUTME: Verifies audio metadata probing and filename generation

import pytest
import json
import time
from unittest.mock import patch, MagicMock
from src.audio_manager.audio_utils import probe_metadata, generate_internal_filename


def test_probe_metadata_success():
    """Test that probe_metadata parses ffprobe output correctly."""
    mock_ffprobe_output = {
        "streams": [
            {
                "codec_type": "audio",
                "duration": "123.456",
                "sample_rate": "44100",
                "channels": 2,
                "codec_name": "mp3"
            }
        ],
        "format": {
            "size": "5678901"
        }
    }
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            stdout=json.dumps(mock_ffprobe_output),
            stderr="",
            returncode=0
        )
        
        result = probe_metadata("/fake/path/test.mp3")
        
        assert result["duration"] == 123.456
        assert result["sample_rate"] == 44100
        assert result["channels"] == 2
        assert result["format"] == "mp3"
        assert result["file_size"] == 5678901
        
        # Verify ffprobe was called correctly
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "ffprobe" in args
        assert "-v" in args and "quiet" in args
        assert "-print_format" in args and "json" in args
        assert "/fake/path/test.mp3" in args


def test_probe_metadata_handles_ffprobe_error():
    """Test that probe_metadata handles ffprobe errors gracefully."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            stdout="",
            stderr="ffprobe: error message",
            returncode=1
        )
        
        result = probe_metadata("/fake/path/bad.mp3")
        
        assert result is None


def test_probe_metadata_handles_malformed_json():
    """Test that probe_metadata handles malformed JSON output."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            stdout="invalid json {",
            stderr="",
            returncode=0
        )
        
        result = probe_metadata("/fake/path/test.mp3")
        
        assert result is None


def test_probe_metadata_missing_stream_data():
    """Test that probe_metadata handles missing stream data."""
    mock_ffprobe_output = {
        "streams": [],
        "format": {"size": "1000"}
    }
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            stdout=json.dumps(mock_ffprobe_output),
            stderr="",
            returncode=0
        )
        
        result = probe_metadata("/fake/path/test.mp3")
        
        assert result is None


def test_generate_internal_filename_format():
    """Test that generated filename follows the correct format."""
    original_name = "my recording.mp3"
    
    # Mock time to get predictable timestamp
    with patch('time.time', return_value=1609459200.0):  # 2021-01-01 00:00:00 UTC
        filename = generate_internal_filename(original_name)
    
    # Should be: <timestamp>_<8-char-uuid>.mp3
    parts = filename.split('.')
    assert len(parts) == 2
    assert parts[1] == "mp3"  # extension preserved
    
    name_parts = parts[0].split('_')
    assert len(name_parts) == 2
    assert name_parts[0] == "1609459200"  # epoch timestamp
    assert len(name_parts[1]) == 8  # short UUID


def test_generate_internal_filename_uniqueness():
    """Test that generated filenames are unique."""
    original_name = "test.wav"
    
    filename1 = generate_internal_filename(original_name)
    filename2 = generate_internal_filename(original_name)
    
    assert filename1 != filename2
    
    # Both should have same extension
    assert filename1.endswith(".wav")
    assert filename2.endswith(".wav")


def test_generate_internal_filename_preserves_extension():
    """Test that file extensions are preserved correctly."""
    test_cases = [
        ("file.mp3", "mp3"),
        ("recording.wav", "wav"),
        ("audio.m4a", "m4a"),
        ("no_extension", ""),
        ("multiple.dots.mp3", "mp3")
    ]
    
    for original, expected_ext in test_cases:
        filename = generate_internal_filename(original)
        if expected_ext:
            assert filename.endswith(f".{expected_ext}")
        else:
            assert "." not in filename


def test_generate_internal_filename_timestamp_increases():
    """Test that timestamps in filenames increase over time."""
    filename1 = generate_internal_filename("test.mp3")
    time.sleep(0.01)  # Small delay
    filename2 = generate_internal_filename("test.mp3")
    
    timestamp1 = int(filename1.split('_')[0])
    timestamp2 = int(filename2.split('_')[0])
    
    assert timestamp2 >= timestamp1