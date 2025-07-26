#!/usr/bin/env python3
# ABOUTME: Main entry point for Audio Recording Manager
# ABOUTME: Starts the web server and file watcher

import asyncio
import sys
import uvicorn
from pathlib import Path
from threading import Thread

from mnemovox.config import get_config
from mnemovox.db import init_db
from mnemovox.app import create_app
from mnemovox.watcher import setup_watcher
from mnemovox.pipeline import process_pending_transcriptions


def run_watcher(config, db_path):
    """Run the file system watcher in a separate thread."""
    observer = setup_watcher(config, db_path)
    observer.start()

    try:
        while True:
            observer.join(1)
            if not observer.is_alive():
                break
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def run_transcription_pipeline(config, db_path):
    """Run periodic transcription processing."""

    async def periodic_transcription():
        while True:
            try:
                await process_pending_transcriptions(config, db_path)
            except Exception as e:
                print(f"Transcription pipeline error: {e}")

            # Wait 30 seconds before next check
            await asyncio.sleep(30)

    asyncio.run(periodic_transcription())


def main():
    """Main entry point."""
    print("🎵 Audio Recording Manager")
    print("Starting up...")

    # Load configuration
    config = get_config()
    print(f"📁 Monitoring: {config.monitored_directory}")
    print(f"💾 Storage: {config.storage_path}")
    print(f"🤖 Whisper model: {config.whisper_model}")

    # Initialize database
    db_path = Path(config.storage_path) / "metadata.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    init_db(str(db_path))
    print(f"🗄️ Database: {db_path}")

    # Create FastAPI app
    app = create_app(config, str(db_path))

    # Start file watcher in background thread
    watcher_thread = Thread(
        target=run_watcher, args=(config, str(db_path)), daemon=True
    )
    watcher_thread.start()
    print("👀 File watcher started")

    # Start transcription pipeline in background thread
    transcription_thread = Thread(
        target=run_transcription_pipeline, args=(config, str(db_path)), daemon=True
    )
    transcription_thread.start()
    print("🎤 Transcription pipeline started")

    print("🌐 Starting web server at http://127.0.0.1:8000")
    print("Press Ctrl+C to stop")

    try:
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        sys.exit(0)


if __name__ == "__main__":
    main()
