# ABOUTME: Database module for audio recordings metadata
# ABOUTME: Handles SQLite database initialization and session management

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    JSON,
    text,
)
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.sql import func
from pathlib import Path
from typing import Any


class Base(DeclarativeBase):
    pass


class Recording(Base):
    """SQLAlchemy model for audio recordings metadata."""

    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    original_filename = Column(String, nullable=False)
    internal_filename = Column(String, nullable=False, unique=True)
    storage_path = Column(String, nullable=False)
    import_timestamp = Column(DateTime, nullable=False)
    duration_seconds = Column(Float)
    audio_format = Column(String)
    sample_rate = Column(Integer)
    channels = Column(Integer)
    file_size_bytes = Column(Integer)
    transcript_status = Column(String, default="pending")  # pending, complete, error
    transcript_language = Column(String)
    transcript_text = Column(Text)
    transcript_segments = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


def init_db(db_path: str, fts_enabled: bool = True) -> None:
    """
    Initialize the database and create tables.

    Args:
        db_path: Path to the SQLite database file
        fts_enabled: Whether to create FTS5 virtual table for search
    """
    # Ensure parent directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # Create engine and tables
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)

    # Create FTS5 virtual table if enabled
    if fts_enabled:
        with engine.connect() as conn:
            conn.execute(
                text(
                    """
                CREATE VIRTUAL TABLE IF NOT EXISTS recordings_fts USING fts5(
                    original_filename,
                    transcript_text
                )
                """
                )
            )
            conn.commit()


def get_session(db_path: str) -> Any:
    """
    Get a SQLAlchemy session for the database.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        SQLAlchemy session object
    """
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    return Session()


def sync_fts(session: Any, recording_id: int) -> None:
    """
    Sync a recording's data to the FTS table for search.

    Args:
        session: SQLAlchemy session
        recording_id: ID of the recording to sync
    """
    # Get the recording data
    recording = session.query(Recording).filter(Recording.id == recording_id).first()
    if not recording:
        return

    # Handle null transcript text
    transcript_text = recording.transcript_text or ""

    # Delete existing FTS entry if it exists
    session.execute(
        text("DELETE FROM recordings_fts WHERE rowid = :recording_id"),
        {"recording_id": recording_id},
    )

    # Insert/update FTS entry
    session.execute(
        text(
            "INSERT INTO recordings_fts(rowid, original_filename, transcript_text) VALUES (:recording_id, :filename, :transcript)"
        ),
        {
            "recording_id": recording_id,
            "filename": recording.original_filename,
            "transcript": transcript_text,
        },
    )

    session.commit()
