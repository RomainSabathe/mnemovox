# ABOUTME: Database module for audio recordings metadata
# ABOUTME: Handles SQLite database initialization and session management

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
from pathlib import Path

Base = declarative_base()


class Recording(Base):
    """SQLAlchemy model for audio recordings metadata."""
    __tablename__ = 'recordings'
    
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
    transcript_status = Column(String, default='pending')  # pending, complete, error
    transcript_language = Column(String)
    transcript_text = Column(Text)
    transcript_segments = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


def init_db(db_path: str) -> None:
    """
    Initialize the database and create tables.
    
    Args:
        db_path: Path to the SQLite database file
    """
    # Ensure parent directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Create engine and tables
    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)


def get_session(db_path: str):
    """
    Get a SQLAlchemy session for the database.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        SQLAlchemy session object
    """
    engine = create_engine(f'sqlite:///{db_path}')
    Session = sessionmaker(bind=engine)
    return Session()