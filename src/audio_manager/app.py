# ABOUTME: FastAPI web application for audio recording manager
# ABOUTME: Provides web interface and API for viewing recordings and transcripts

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import List, Optional
from .config import Config
from .db import get_session, Recording


def create_app(config: Config, db_path: str) -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Args:
        config: Application configuration
        db_path: Path to the database file
        
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="Audio Recording Manager",
        description="Self-hosted audio recording manager with automatic transcription",
        version="1.0.0"
    )
    
    # Configure templates
    templates = Jinja2Templates(directory="templates")
    
    # Dependency to get database session
    def get_db_session():
        session = get_session(db_path)
        try:
            yield session
        finally:
            session.close()
    
    @app.get("/", response_class=RedirectResponse)
    async def root():
        """Redirect root to recordings list."""
        return RedirectResponse(url="/recordings", status_code=302)
    
    @app.get("/recordings", response_class=HTMLResponse)
    async def recordings_list(request: Request, session=Depends(get_db_session)):
        """Display list of all recordings."""
        recordings = session.query(Recording).order_by(Recording.import_timestamp.desc()).all()
        
        return templates.TemplateResponse(
            request=request,
            name="list.html",
            context={"recordings": recordings}
        )
    
    @app.get("/recordings/{recording_id}", response_class=HTMLResponse)
    async def recording_detail(request: Request, recording_id: int, session=Depends(get_db_session)):
        """Display detail page for a specific recording."""
        recording = session.query(Recording).filter_by(id=recording_id).first()
        
        if not recording:
            raise HTTPException(status_code=404, detail="Recording not found")
        
        return templates.TemplateResponse(
            request=request,
            name="detail.html",
            context={"recording": recording}
        )
    
    @app.get("/audio/{path:path}")
    async def serve_audio(path: str):
        """Serve audio files from storage."""
        full_path = Path(config.storage_path) / path
        
        if not full_path.exists() or not full_path.is_file():
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        # Basic security check - ensure path is within storage directory
        try:
            full_path.resolve().relative_to(Path(config.storage_path).resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return FileResponse(
            path=str(full_path),
            media_type=f"audio/{full_path.suffix[1:]}" if full_path.suffix else "audio/mpeg"
        )
    
    # API endpoints
    @app.get("/api/recordings", response_model=List[dict])
    async def api_recordings_list(session=Depends(get_db_session)):
        """API endpoint to get list of all recordings."""
        recordings = session.query(Recording).order_by(Recording.import_timestamp.desc()).all()
        
        return [
            {
                "id": r.id,
                "original_filename": r.original_filename,
                "internal_filename": r.internal_filename,
                "storage_path": r.storage_path,
                "import_timestamp": r.import_timestamp.isoformat() if r.import_timestamp else None,
                "duration_seconds": r.duration_seconds,
                "audio_format": r.audio_format,
                "sample_rate": r.sample_rate,
                "channels": r.channels,
                "file_size_bytes": r.file_size_bytes,
                "transcript_status": r.transcript_status,
                "transcript_language": r.transcript_language,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None
            }
            for r in recordings
        ]
    
    @app.get("/api/recordings/{recording_id}")
    async def api_recording_detail(recording_id: int, session=Depends(get_db_session)):
        """API endpoint to get detailed information about a specific recording."""
        recording = session.query(Recording).filter_by(id=recording_id).first()
        
        if not recording:
            raise HTTPException(status_code=404, detail="Recording not found")
        
        return {
            "id": recording.id,
            "original_filename": recording.original_filename,
            "internal_filename": recording.internal_filename,
            "storage_path": recording.storage_path,
            "import_timestamp": recording.import_timestamp.isoformat() if recording.import_timestamp else None,
            "duration_seconds": recording.duration_seconds,
            "audio_format": recording.audio_format,
            "sample_rate": recording.sample_rate,
            "channels": recording.channels,
            "file_size_bytes": recording.file_size_bytes,
            "transcript_status": recording.transcript_status,
            "transcript_language": recording.transcript_language,
            "transcript_text": recording.transcript_text,
            "transcript_segments": recording.transcript_segments,
            "created_at": recording.created_at.isoformat() if recording.created_at else None,
            "updated_at": recording.updated_at.isoformat() if recording.updated_at else None
        }
    
    return app


# Entry point for running the application
if __name__ == "__main__":
    import uvicorn
    from .config import get_config
    from .db import init_db
    
    # Load configuration
    config = get_config()
    
    # Initialize database
    db_path = Path(config.storage_path) / "metadata.db"
    init_db(str(db_path))
    
    # Create and run the app
    app = create_app(config, str(db_path))
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )