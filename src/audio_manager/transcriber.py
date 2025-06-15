# ABOUTME: Transcription module using faster-whisper
# ABOUTME: Handles audio file transcription with segment-level details

import logging
from typing import Any, Dict, List, Optional, Tuple

from faster_whisper import WhisperModel

# Configure logging
logger = logging.getLogger(__name__)


def transcribe_file(
    file_path: str, model_name: str = "base.en", language: Optional[str] = None
) -> Optional[Tuple[str, List[Dict[str, Any]], str]]:
    """
    Transcribe an audio file using faster-whisper.

    Args:
        file_path: Path to the audio file to transcribe.
        model_name: Whisper model to use (e.g., "base.en", "small", "large-v2").
        language: Language code (e.g., "en", "fr") or None for auto-detection.
                  "auto" will also be treated as None for auto-detection.

    Returns:
        Tuple of (full_text, segments, detected_language) or None if transcription fails.
        - full_text: Concatenated text from all segments.
        - segments: List of segment dictionaries with start, end, text, confidence.
        - detected_language: Language code detected by the model.
    """
    try:
        log_language = (
            language if language and language.lower() != "auto" else "auto-detect"
        )
        logger.info(
            f"Starting transcription of {file_path} with model {model_name}, language: {log_language}"
        )

        # Load the Whisper model (force CPU to avoid GPU issues in testing)
        model = WhisperModel(model_name, device="cpu")

        # Prepare transcription arguments
        transcribe_kwargs = {}
        if language and language.lower() != "auto":
            transcribe_kwargs["language"] = language

        # Transcribe the audio file
        segments_generator, info = model.transcribe(file_path, **transcribe_kwargs)
        detected_language = info.language

        # Process segments
        segments = []
        text_parts = []

        for segment in segments_generator:
            # Extract segment information
            segment_dict = {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "confidence": getattr(segment, "confidence", None),
            }

            segments.append(segment_dict)
            text_parts.append(segment.text)

        # Concatenate all text with spaces
        full_text = " ".join(text_parts)

        logger.info(
            f"Transcription completed: {len(segments)} segments, {len(full_text)} characters. Detected language: {detected_language}"
        )
        logger.info(f"{full_text=}")

        return full_text, segments, detected_language

    except Exception as e:
        logger.error(
            f"Transcription failed for {file_path} (model: {model_name}, lang: {language}): {e}",
            exc_info=True,
        )
        return None
