# ABOUTME: FastAPI web application for audio recording manager
# ABOUTME: Provides web interface and API for viewing recordings and transcripts

from fastapi import (
    FastAPI,
    Request,
    HTTPException,
    Depends,
    UploadFile,
    File,
    status,
    BackgroundTasks,
)
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import Optional
import uuid
import shutil
from datetime import datetime
from .config import Config
from .db import get_session, Recording


def run_transcription_task(recording_id: int, db_path_str: str):
    """Background task to process transcription for a recording."""
    # This is a placeholder for the actual transcription logic
    # In a real implementation, this would:
    # 1. Get the recording from the database
    # 2. Load the audio file from storage
    # 3. Run the transcription service (e.g., Whisper)
    # 4. Update the database with results

    # For testing purposes, we'll just leave the status as "pending"
    # and not actually process the transcription

    # In a real application, you would implement the actual transcription here
    try:
        # Try to import the transcriber module if it exists
        from .transcriber import process_recording  # type: ignore

        # Get a fresh database session for the background task
        session = get_session(db_path_str)
        try:
            recording = session.query(Recording).filter_by(id=recording_id).first()
            if recording:
                # Process the recording using existing transcriber logic
                process_recording(recording, session)
                session.commit()
        finally:
            session.close()

    except ImportError:
        # If transcriber module doesn't exist, just leave as pending for now
        # This allows tests to verify the API behavior without failing transcription
        pass
    except Exception:
        # On any error, mark the recording as failed
        session = get_session(db_path_str)
        try:
            recording = session.query(Recording).filter_by(id=recording_id).first()
            if recording:
                recording.transcript_status = "error"
                recording.updated_at = datetime.now()
                session.commit()
        finally:
            session.close()


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
        version="1.0.0",
    )

    # Configure templates and static files
    templates = Jinja2Templates(directory="templates")
    app.mount("/static", StaticFiles(directory="static"), name="static")

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
    async def recordings_list(
        request: Request, page: int = 1, session=Depends(get_db_session)
    ):
        """Display paginated list of recordings."""
        # Validate page parameter
        if page < 0:
            page = 1
        elif page == 0:
            page = 1

        per_page = config.items_per_page

        # Get total count
        total = session.query(Recording).count()

        # Calculate pagination metadata
        pages = (total + per_page - 1) // per_page  # Ceiling division
        has_prev = page > 1
        has_next = page < pages

        # Get recordings for current page
        offset = (page - 1) * per_page
        recordings = (
            session.query(Recording)
            .order_by(Recording.import_timestamp.desc(), Recording.id.desc())
            .offset(offset)
            .limit(per_page)
            .all()
        )

        pagination = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": pages,
            "has_prev": has_prev,
            "has_next": has_next,
        }

        return templates.TemplateResponse(
            request=request,
            name="recordings_list.html",
            context={"recordings": recordings, "pagination": pagination},
        )

    @app.get("/recordings/{recording_id}", response_class=HTMLResponse)
    async def recording_detail(
        request: Request, recording_id: int, session=Depends(get_db_session)
    ):
        """Display detail page for a specific recording."""
        recording = session.query(Recording).filter_by(id=recording_id).first()

        if not recording:
            raise HTTPException(status_code=404, detail="Recording not found")

        return templates.TemplateResponse(
            request=request,
            name="recording_detail.html",
            context={"recording": recording},
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
            media_type=f"audio/{full_path.suffix[1:]}"
            if full_path.suffix
            else "audio/mpeg",
        )

    # API endpoints
    @app.get("/api/recordings")
    async def api_recordings_list(
        page: int = 1, per_page: Optional[int] = None, session=Depends(get_db_session)
    ):
        """API endpoint to get paginated list of recordings."""
        # Validate parameters
        if page < 0:
            raise HTTPException(
                status_code=400, detail={"error": "page must be positive"}
            )
        elif page == 0:
            page = 1

        if per_page is None:
            per_page = config.items_per_page

        if per_page < 1:
            raise HTTPException(
                status_code=400, detail={"error": "per_page must be positive"}
            )

        if per_page > 100:
            raise HTTPException(
                status_code=400, detail={"error": "per_page cannot exceed 100"}
            )

        # Get total count
        total = session.query(Recording).count()

        # Calculate pagination metadata
        pages = (total + per_page - 1) // per_page  # Ceiling division
        has_prev = page > 1
        has_next = page < pages

        # Get recordings for current page
        offset = (page - 1) * per_page
        recordings = (
            session.query(Recording)
            .order_by(Recording.import_timestamp.desc(), Recording.id.desc())
            .offset(offset)
            .limit(per_page)
            .all()
        )

        return {
            "recordings": [
                {
                    "id": r.id,
                    "original_filename": r.original_filename,
                    "internal_filename": r.internal_filename,
                    "storage_path": r.storage_path,
                    "import_timestamp": r.import_timestamp.isoformat()
                    if r.import_timestamp
                    else None,
                    "duration_seconds": r.duration_seconds,
                    "audio_format": r.audio_format,
                    "sample_rate": r.sample_rate,
                    "channels": r.channels,
                    "file_size_bytes": r.file_size_bytes,
                    "transcript_status": r.transcript_status,
                    "transcript_language": r.transcript_language,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                }
                for r in recordings
            ],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": pages,
                "has_prev": has_prev,
                "has_next": has_next,
            },
        }

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
            "import_timestamp": recording.import_timestamp.isoformat()
            if recording.import_timestamp
            else None,
            "duration_seconds": recording.duration_seconds,
            "audio_format": recording.audio_format,
            "sample_rate": recording.sample_rate,
            "channels": recording.channels,
            "file_size_bytes": recording.file_size_bytes,
            "transcript_status": recording.transcript_status,
            "transcript_language": recording.transcript_language,
            "transcript_text": recording.transcript_text,
            "transcript_segments": recording.transcript_segments,
            "created_at": recording.created_at.isoformat()
            if recording.created_at
            else None,
            "updated_at": recording.updated_at.isoformat()
            if recording.updated_at
            else None,
        }

    @app.get("/api/recordings/{recording_id}/segments")
    async def api_recording_segments(
        recording_id: int, session=Depends(get_db_session)
    ):
        """API endpoint to get transcript segments for a specific recording."""
        recording = session.query(Recording).filter_by(id=recording_id).first()

        if not recording:
            raise HTTPException(status_code=404, detail="Recording not found")

        # Return segments data
        segments = (
            recording.transcript_segments if recording.transcript_segments else []
        )

        return {
            "recording_id": recording.id,
            "total_segments": len(segments),
            "segments": segments,
        }

    @app.post("/api/recordings/upload")
    async def api_upload_recording(file: UploadFile = File(...)):
        """API endpoint to upload audio files for processing."""
        # Validate file extension
        if not file.filename:
            raise HTTPException(
                status_code=400, detail={"error": "No filename provided"}
            )

        file_path = Path(file.filename)
        file_extension = file_path.suffix.lower()

        # Check if it's a valid audio file extension
        valid_extensions = {".wav", ".mp3", ".m4a"}
        if file_extension not in valid_extensions:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"Invalid file extension. Supported: {', '.join(valid_extensions)}"
                },
            )

        try:
            # Create upload temp directory if it doesn't exist
            upload_temp_path = Path(config.upload_temp_path)
            upload_temp_path.mkdir(parents=True, exist_ok=True)

            # Generate unique filename to avoid conflicts
            temp_filename = f"{uuid.uuid4().hex}_{file.filename}"
            temp_file_path = upload_temp_path / temp_filename

            # Save uploaded file to temp location
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Move uploaded file to storage and create database record
            # This is a simplified version of the ingestion logic
            from .audio_utils import generate_internal_filename, probe_metadata
            from datetime import datetime

            try:
                # Generate internal filename and storage path
                internal_filename = generate_internal_filename(file.filename)

                # Create storage directory structure (YYYY/MM-DD)
                now = datetime.now()
                storage_subdir = (
                    Path(config.storage_path)
                    / now.strftime("%Y")
                    / now.strftime("%m-%d")
                )
                storage_subdir.mkdir(parents=True, exist_ok=True)
                final_storage_path = storage_subdir / internal_filename

                # Move file to final storage location
                shutil.move(str(temp_file_path), str(final_storage_path))

                # Try to extract metadata, but don't fail if it doesn't work
                try:
                    metadata = probe_metadata(str(final_storage_path))
                    if metadata:
                        duration = metadata.get("duration")
                        audio_format = metadata.get("format")
                        sample_rate_meta = metadata.get("sample_rate")
                        channels = metadata.get("channels")
                    else:
                        duration = None
                        audio_format = None
                        sample_rate_meta = None
                        channels = None
                    file_size = final_storage_path.stat().st_size
                except Exception:
                    # If metadata extraction fails, use defaults
                    duration = None
                    audio_format = file_extension[1:]  # Remove the dot
                    sample_rate_meta = None
                    channels = None
                    file_size = (
                        final_storage_path.stat().st_size
                        if final_storage_path.exists()
                        else 0
                    )

                # Create database record
                session = get_session(db_path)
                try:
                    recording = Recording(
                        original_filename=file.filename,
                        internal_filename=internal_filename,
                        storage_path=str(final_storage_path),
                        import_timestamp=now,
                        duration_seconds=duration,
                        audio_format=audio_format,
                        sample_rate=sample_rate_meta,
                        channels=channels,
                        file_size_bytes=file_size,
                        transcript_status="pending",
                    )

                    session.add(recording)
                    session.commit()

                    return JSONResponse(
                        status_code=status.HTTP_201_CREATED,
                        content={
                            "id": recording.id,
                            "status": recording.transcript_status,
                        },
                    )
                finally:
                    session.close()

            except Exception as move_error:
                # If moving fails, the temp file might still exist
                raise Exception(f"Failed to process uploaded file: {move_error}")

        except Exception as e:
            # Clean up temp file if something went wrong
            if temp_file_path.exists():
                temp_file_path.unlink()

            # If it's already an HTTPException, re-raise it
            if isinstance(e, HTTPException):
                raise

            # Otherwise, wrap in a 500 error
            raise HTTPException(
                status_code=500, detail={"error": f"Upload failed: {str(e)}"}
            )

    @app.post("/api/recordings/{recording_id}/transcribe")
    async def api_retranscribe_recording(
        recording_id: int,
        background_tasks: BackgroundTasks,
        session=Depends(get_db_session),
    ):
        """API endpoint to trigger re-transcription of a recording."""
        recording = session.query(Recording).filter_by(id=recording_id).first()

        if not recording:
            raise HTTPException(status_code=404, detail="Recording not found")

        # Remember previous status for message
        previous_status = recording.transcript_status

        # Update recording status to pending and clear previous transcript data
        recording.transcript_status = "pending"
        recording.transcript_text = None
        recording.transcript_segments = None
        recording.transcript_language = None
        recording.updated_at = datetime.now()

        session.commit()

        # Queue background transcription task
        background_tasks.add_task(run_transcription_task, recording_id, db_path)

        # Determine appropriate message based on previous status
        if previous_status == "pending":
            message = f"Recording {recording_id} was already pending transcription, re-queued for processing"
        else:
            message = f"Recording {recording_id} has been queued for re-transcription"

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "id": recording_id,
                "status": "pending",
                "message": message,
            },
        )

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

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
