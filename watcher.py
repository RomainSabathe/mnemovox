# ABOUTME: File system watcher for audio ingestion pipeline  
# ABOUTME: Monitors directory for new audio files and processes them

import shutil
import logging
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent
from audio_utils import probe_metadata, generate_internal_filename
from db import get_session, Recording
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IngestHandler(FileSystemEventHandler):
    """File system event handler for audio ingestion."""
    
    VALID_EXTENSIONS = {'.wav', '.mp3', '.m4a'}
    
    def __init__(self, config: Config, db_path: str):
        """
        Initialize the ingestion handler.
        
        Args:
            config: Application configuration
            db_path: Path to the database file
        """
        self.config = config
        self.db_path = db_path
        
    def on_created(self, event: FileCreatedEvent):
        """
        Handle file creation events.
        
        Args:
            event: File system event
        """
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        
        # Check if it's a valid audio file extension
        if file_path.suffix.lower() not in self.VALID_EXTENSIONS:
            logger.debug(f"Ignoring non-audio file: {file_path}")
            return
            
        # Check if file still exists (could have been moved already)
        if not file_path.exists():
            logger.debug(f"File no longer exists: {file_path}")
            return
            
        logger.info(f"Processing audio file: {file_path}")
        
        try:
            self._process_audio_file(file_path)
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
    
    def _process_audio_file(self, file_path: Path):
        """
        Process a single audio file: extract metadata, move to storage, create DB record.
        
        Args:
            file_path: Path to the audio file to process
        """
        # Extract metadata using ffprobe
        metadata = probe_metadata(str(file_path))
        if metadata is None:
            logger.warning(f"Could not extract metadata from {file_path}")
            return
            
        # Generate internal filename
        internal_filename = generate_internal_filename(file_path.name)
        
        # Create storage directory structure (YYYY/YYYY-MM-DD)
        now = datetime.now()
        date_dir = f"{now.year}/{now.strftime('%Y-%m-%d')}"
        storage_dir = Path(self.config.storage_path) / date_dir
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Destination path
        dest_path = storage_dir / internal_filename
        
        # Move file to storage
        shutil.move(str(file_path), str(dest_path))
        logger.info(f"Moved {file_path} to {dest_path}")
        
        # Create database record
        self._create_database_record(
            original_filename=file_path.name,
            internal_filename=internal_filename,
            storage_path=str(Path(date_dir) / internal_filename),
            metadata=metadata,
            import_timestamp=now
        )
        
    def _create_database_record(self, original_filename: str, internal_filename: str,
                              storage_path: str, metadata: dict, import_timestamp: datetime):
        """
        Create a database record for the processed audio file.
        
        Args:
            original_filename: Original filename
            internal_filename: Generated internal filename
            storage_path: Relative storage path
            metadata: Audio metadata dictionary
            import_timestamp: When the file was imported
        """
        session = get_session(self.db_path)
        
        try:
            recording = Recording(
                original_filename=original_filename,
                internal_filename=internal_filename,
                storage_path=storage_path,
                import_timestamp=import_timestamp,
                duration_seconds=metadata.get('duration'),
                audio_format=metadata.get('format'),
                sample_rate=metadata.get('sample_rate'),
                channels=metadata.get('channels'),
                file_size_bytes=metadata.get('file_size'),
                transcript_status='pending'
            )
            
            session.add(recording)
            session.commit()
            
            logger.info(f"Created database record for {internal_filename}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create database record: {e}")
            raise
        finally:
            session.close()


def setup_watcher(config: Config, db_path: str) -> Observer:
    """
    Set up file system watcher for the monitored directory.
    
    Args:
        config: Application configuration
        db_path: Path to the database file
        
    Returns:
        Configured watchdog Observer
    """
    # Ensure monitored directory exists
    monitored_path = Path(config.monitored_directory)
    monitored_path.mkdir(parents=True, exist_ok=True)
    
    # Create event handler
    event_handler = IngestHandler(config, db_path)
    
    # Set up observer
    observer = Observer()
    observer.schedule(
        event_handler,
        str(monitored_path),
        recursive=False
    )
    
    logger.info(f"Watcher configured for: {monitored_path}")
    return observer