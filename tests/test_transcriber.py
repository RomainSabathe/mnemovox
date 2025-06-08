# ABOUTME: Tests for transcription module
# ABOUTME: Verifies faster-whisper integration and transcription functionality

import pytest
from unittest.mock import patch, MagicMock
from src.audio_manager.transcriber import transcribe_file


def test_transcribe_file_success():
    """Test successful transcription with faster-whisper."""
    # Mock transcription segments
    mock_segments = [
        MagicMock(
            start=0.0,
            end=2.5,
            text="Hello, this is a test.",
            confidence=0.95
        ),
        MagicMock(
            start=2.5,
            end=5.0,
            text="This is the second segment.",
            confidence=0.87
        )
    ]
    
    # Mock whisper model and transcribe method
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (mock_segments, {"language": "en"})
    
    with patch('src.audio_manager.transcriber.WhisperModel', return_value=mock_model):
        full_text, segments = transcribe_file("/fake/path/audio.wav", "base.en")
        
        # Check full text concatenation
        expected_text = "Hello, this is a test. This is the second segment."
        assert full_text == expected_text
        
        # Check segments structure
        assert len(segments) == 2
        
        assert segments[0]["start"] == 0.0
        assert segments[0]["end"] == 2.5
        assert segments[0]["text"] == "Hello, this is a test."
        assert segments[0]["confidence"] == 0.95
        
        assert segments[1]["start"] == 2.5
        assert segments[1]["end"] == 5.0
        assert segments[1]["text"] == "This is the second segment."
        assert segments[1]["confidence"] == 0.87
        
        # Verify model was created with correct parameters
        from src.audio_manager.transcriber import WhisperModel
        WhisperModel.assert_called_once_with("base.en")
        
        # Verify transcribe was called with correct path
        mock_model.transcribe.assert_called_once_with("/fake/path/audio.wav")


def test_transcribe_file_empty_segments():
    """Test transcription with no segments returned."""
    mock_segments = []
    
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (mock_segments, {"language": "en"})
    
    with patch('src.audio_manager.transcriber.WhisperModel', return_value=mock_model):
        full_text, segments = transcribe_file("/fake/path/empty.wav", "base.en")
        
        assert full_text == ""
        assert segments == []


def test_transcribe_file_single_segment():
    """Test transcription with single segment."""
    mock_segments = [
        MagicMock(
            start=0.0,
            end=3.2,
            text="Single segment audio file.",
            confidence=0.92
        )
    ]
    
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (mock_segments, {"language": "en"})
    
    with patch('src.audio_manager.transcriber.WhisperModel', return_value=mock_model):
        full_text, segments = transcribe_file("/fake/path/single.wav", "small")
        
        assert full_text == "Single segment audio file."
        assert len(segments) == 1
        assert segments[0]["text"] == "Single segment audio file."
        assert segments[0]["confidence"] == 0.92


def test_transcribe_file_handles_whisper_exception():
    """Test that transcription handles faster-whisper exceptions gracefully."""
    mock_model = MagicMock()
    mock_model.transcribe.side_effect = Exception("Whisper model error")
    
    with patch('src.audio_manager.transcriber.WhisperModel', return_value=mock_model):
        result = transcribe_file("/fake/path/error.wav", "base.en")
        
        assert result is None


def test_transcribe_file_handles_model_creation_error():
    """Test that transcription handles model creation errors gracefully."""
    with patch('src.audio_manager.transcriber.WhisperModel', side_effect=Exception("Model load error")):
        result = transcribe_file("/fake/path/audio.wav", "invalid-model")
        
        assert result is None


def test_transcribe_file_with_different_models():
    """Test transcription with different whisper models."""
    mock_segments = [
        MagicMock(start=0.0, end=1.0, text="Test", confidence=0.9)
    ]
    
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (mock_segments, {"language": "fr"})
    
    # Test with different model sizes
    for model_name in ["tiny", "base", "small", "medium", "large-v2"]:
        with patch('src.audio_manager.transcriber.WhisperModel', return_value=mock_model):
            full_text, segments = transcribe_file("/fake/path/audio.wav", model_name)
            
            assert full_text == "Test"
            assert len(segments) == 1


def test_transcribe_file_preserves_segment_timing():
    """Test that segment timing information is preserved correctly."""
    mock_segments = [
        MagicMock(start=1.25, end=3.75, text="First", confidence=0.88),
        MagicMock(start=4.0, end=7.33, text="Second", confidence=0.93),
        MagicMock(start=8.1, end=10.5, text="Third", confidence=0.91)
    ]
    
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (mock_segments, {"language": "en"})
    
    with patch('src.audio_manager.transcriber.WhisperModel', return_value=mock_model):
        full_text, segments = transcribe_file("/fake/path/timing.wav", "base.en")
        
        # Check timing precision is maintained
        assert segments[0]["start"] == 1.25
        assert segments[0]["end"] == 3.75
        assert segments[1]["start"] == 4.0
        assert segments[1]["end"] == 7.33
        assert segments[2]["start"] == 8.1
        assert segments[2]["end"] == 10.5
        
        # Check full text concatenation
        assert full_text == "First Second Third"


def test_transcribe_file_handles_missing_confidence():
    """Test transcription when confidence is missing from segments."""
    mock_segments = [
        MagicMock(start=0.0, end=2.0, text="No confidence", spec=['start', 'end', 'text'])
    ]
    # Remove confidence attribute
    del mock_segments[0].confidence
    
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (mock_segments, {"language": "en"})
    
    with patch('src.audio_manager.transcriber.WhisperModel', return_value=mock_model):
        full_text, segments = transcribe_file("/fake/path/no_conf.wav", "base.en")
        
        assert full_text == "No confidence"
        assert segments[0]["confidence"] is None