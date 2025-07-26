# ABOUTME: Pipeline orchestration for ingestion and transcription
# ABOUTME: Coordinates async transcription processing with concurrency control

import asyncio
import logging
from pathlib import Path
from typing import List, Optional
from .config import Config
from .db import get_session, Recording, sync_fts
from .transcriber import transcribe_file

# Configure logging
logger = logging.getLogger(__name__)


class TranscriptionPipeline:
    """Orchestrates transcription processing with concurrency control."""

    def __init__(self, config: Config, db_path: str):
        """
        Initialize the transcription pipeline.

        Args:
            config: Application configuration
            db_path: Path to the database file
        """
        self.config = config
        self.db_path = db_path
        self.semaphore = asyncio.Semaphore(config.max_concurrent_transcriptions)

    async def process_pending_transcriptions(self):
        """Process all pending transcription records with concurrency control."""
        logger.info("Starting transcription pipeline processing")

        # Get all pending records
        pending_records = self._get_pending_records()

        if not pending_records:
            logger.info("No pending transcriptions found")
            return

        logger.info(f"Found {len(pending_records)} pending transcriptions")

        # Create tasks for each record with semaphore control
        tasks = [
            self._process_single_record(
                record_id,
                storage_path,
                db_model_override,
                db_language_override,
            )
            for record_id, storage_path, db_model_override, db_language_override in pending_records
        ]

        # Execute all tasks concurrently (with semaphore limiting)
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("Transcription pipeline processing completed")

    def _get_pending_records(self) -> List[tuple]:
        """
        Get all pending transcription records from the database.

        Returns:
            List of tuples: (record_id, storage_path, transcription_model_override, transcription_language_override)
        """
        session = get_session(self.db_path)

        try:
            records = (
                session.query(
                    Recording.id,
                    Recording.storage_path,
                    Recording.transcription_model,
                    Recording.transcription_language,
                )
                .filter(Recording.transcript_status == "pending")
                .all()
            )
            # Ensure records is a list of tuples, not Recording objects
            # The query above already returns tuples of (id, storage_path, model, lang)
            return records

        finally:
            session.close()

    async def _process_single_record(
        self,
        record_id: int,
        storage_path: str,
        db_model_override: Optional[str],
        db_language_override: Optional[str],
    ):
        """
        Process a single transcription record.

        Args:
            record_id: Database record ID.
            storage_path: Relative path to the audio file.
            db_model_override: Model override from DB, if any.
            db_language_override: Language override from DB, if any.
        """
        async with self.semaphore:
            logger.info(f"Processing transcription for record {record_id}")

            # Construct full path to audio file
            full_audio_path = Path(self.config.storage_path) / storage_path

            # Check if audio file exists
            if not full_audio_path.exists():
                logger.error(f"Audio file not found: {full_audio_path}")
                self._update_record_error(record_id)
                return

            try:
                # Determine model and language to use
                model_to_use = (
                    db_model_override
                    if db_model_override
                    else self.config.whisper_model
                )
                language_to_use = (
                    db_language_override
                    if db_language_override
                    else self.config.default_language
                )

                effective_language_param = (
                    language_to_use
                    if language_to_use and language_to_use.lower() != "auto"
                    else None
                )

                # Perform transcription (run in thread pool to avoid blocking)
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    transcribe_file,
                    str(full_audio_path),
                    model_to_use,
                    effective_language_param,
                )

                if result is None:
                    logger.error(f"Transcription failed for record {record_id}")
                    self._update_record_error(record_id)
                else:
                    full_text, segments, detected_language = result
                    logger.info(
                        f"Transcription completed for record {record_id}: {len(segments)} segments, lang: {detected_language}"
                    )
                    self._update_record_success(
                        record_id, full_text, segments, detected_language
                    )

            except Exception as e:
                logger.error(
                    f"Exception during transcription of record {record_id}: {e}"
                )
                self._update_record_error(record_id)

    def _update_record_success(
        self, record_id: int, full_text: str, segments: list, detected_language: str
    ):
        """
        Update database record with successful transcription results.

        Args:
            record_id: Database record ID.
            full_text: Complete transcribed text.
            segments: List of segment dictionaries.
            detected_language: Language detected by the model.
        """
        session = get_session(self.db_path)

        try:
            record = session.query(Recording).filter_by(id=record_id).first()
            if record:
                record.transcript_status = "complete"
                record.transcript_text = full_text
                record.transcript_segments = segments
                record.transcript_language = (
                    detected_language  # Use the language from transcription result
                )

                session.commit()

                # CRITICAL: Index in FTS for search functionality
                sync_fts(session, record_id)

                logger.info(
                    f"Updated record {record_id} with transcription results and FTS indexing"
                )
            else:
                logger.error(f"Record {record_id} not found for update")

        except Exception as e:
            logger.error(f"Failed to update record {record_id}: {e}")
            session.rollback()
        finally:
            session.close()

    def _update_record_error(self, record_id: int):
        """
        Update database record to mark transcription as failed.

        Args:
            record_id: Database record ID
        """
        session = get_session(self.db_path)

        try:
            record = session.query(Recording).filter_by(id=record_id).first()
            if record:
                record.transcript_status = "error"
                session.commit()
                logger.info(f"Marked record {record_id} as transcription error")
            else:
                logger.error(f"Record {record_id} not found for error update")

        except Exception as e:
            logger.error(f"Failed to update record {record_id} error status: {e}")
            session.rollback()
        finally:
            session.close()


async def process_pending_transcriptions(config: Config, db_path: str):
    """
    Convenience function to process pending transcriptions.

    Args:
        config: Application configuration
        db_path: Path to the database file
    """
    pipeline = TranscriptionPipeline(config, db_path)
    await pipeline.process_pending_transcriptions()
