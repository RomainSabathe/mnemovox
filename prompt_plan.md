For all these prompts, refer to **@spec.md** to understand the global context of what you
are building.

```text
PROMPT 1/8: Project Scaffold & Config Loader

Context:
  We are building “Audio Recording Manager” per spec.
  So far, we have only ran `uv init` and only have a miminal pyproject.toml. We need:
    - To extend pyproject.toml with dependencies: FastAPI, watchdog, faster-whisper, pytest, sqlalchemy
    - README.md stub
    - config.yaml sample in project root
    - A `config.py` that loads YAML, provides attributes:
        monitored_directory, storage_path, whisper_model, sample_rate, max_concurrent_transcriptions
    - Defaults if keys are missing.
Approach:
  - Begin with pytest tests in `tests/test_config.py` using tmp_path to write sample YAML and verify loader fields.
  - Then implement `config.py` to satisfy tests.
Request:
  Provide (1) `tests/test_config.py` and (2) `config.py`.
  Use only standard libraries + PyYAML.
  Ensure tests cover missing keys, bad types, and correct override.

End with:
  - All tests passing.
  - `config.py` exposing a `get_config()` function returning a dataclass or namespace.
```

---

```text
PROMPT 2/8: Database Schema & Initialization

Context:
  We have project scaffold and config.get_config().
  Next, implement DB support using SQLAlchemy (or raw sqlite3):
    Table `recordings` matches spec fields.
    Use SQLite; path from config.storage_path + "/metadata.db".
Steps:
  1. Write tests in `tests/test_db.py` to:
     - Initialize DB.
     - Inspect that `recordings` table exists with all columns.
  2. Implement `db.py`:
     - `init_db()` creates DB file and tables.
     - `get_session()` returns SQLAlchemy session (or raw connection).
Request:
  Provide `tests/test_db.py` and `db.py`.
  Wrap in functions for easy imports.
  Tests must pass on empty state.
```

---

```text
PROMPT 3/8: Audio Utilities (probe + filename)

Context:
  We need:
    - `audio_utils.probe_metadata(path: str) -> dict` using ffprobe CLI.
    - `audio_utils.generate_internal_filename(orig_name: str) -> str` producing "<timestamp>_<shortuuid>.<ext>".
Steps:
  1. tests in `tests/test_audio_utils.py`, mocking subprocess output for ffprobe JSON, checking fields.
  2. tests for filename generation pattern and uniqueness.
  3. Implement `audio_utils.py`.
Request:
  Provide tests then implementation.
  Use `subprocess.run` with `capture_output=True`.
  Use `uuid4().hex[:8]` for short uuid.
  Ensure epoch timestamp in seconds.
```

---

```text
PROMPT 4/8: Watcher & Ingestion Pipeline

Context:
  We have config, db, audio_utils.
  Now implement file system watcher:
    - Monitors config.monitored_directory.
    - On new .wav/.mp3/.m4a file:
       a. Copy to temp staging
       b. Call probe_metadata, generate internal_filename
       c. Move to storage_path/YYYY/MM-DD/…
       d. Insert record in DB with transcript_status="pending"
Approach:
  - Write tests in `tests/test_ingest.py` using pytest tmp_path: create a dummy .wav, run one iteration of handler, assert DB row and file moved.
  - Implement `watcher.py` using Watchdog Observer and Handler.
Request:
  Provide `tests/test_ingest.py` and `watcher.py`.
  Use dependency injection for config and db session.
  Ensure idempotency: skip unknown extensions.
```

---

```text
PROMPT 5/8: Transcription Module

Context:
  Now implement `transcriber.py`:
    - Function `transcribe_file(internal_path: str) -> (full_text: str, segments: list)`
    - Use faster-whisper local model from config.whisper_model.
Steps:
  1. tests in `tests/test_transcriber.py` mocking the whisper API call, returning two segments.
  2. implement `transcriber.py` with asynchronous call or sync wrapper.
Request:
  Provide tests + implementation.
  Segments are dicts with start, end, text, confidence.
  full_text = concatenation of texts with spaces.
```

---

```text
PROMPT 6/8: Orchestrate Ingestion → Transcription

Context:
  We have watcher triggering DB inserts, and transcriber.
  Now wire:
    - After insert with status “pending”, schedule transcription (e.g. via asyncio task).
    - On success, update that record’s transcript_status, transcript_text, transcript_segments, transcript_language.
    - On error, set transcript_status="error" and log.
Steps:
  1. Write integration test `tests/test_pipeline.py`: simulate ingestion of a file, then await transcription, assert DB updated.
  2. Implement `pipeline.py` orchestrating.
Request:
  Provide test + implementation.
  Use `asyncio` for concurrency, respect `max_concurrent_transcriptions`.
```

---

```text
PROMPT 7/8: FastAPI Backend & UI

Context:
  Now expose:
    - GET /recordings → list all (from DB), render Jinja `templates/list.html`
    - GET /recordings/{id} → show audio player (`<audio src="…">`) and full transcript.
Steps:
  1. tests in `tests/test_api.py` using FastAPI TestClient: ensure pages 200, expected content.
  2. Create `app.py` with FastAPI, mount static files if needed, configure JinjaTemplates.
  3. Provide `templates/list.html` and `templates/detail.html`.
Request:
  Provide tests, `app.py`, and templates.
  Ensure imports from previous modules for DB and config.
```

---

```text
PROMPT 8/8: CI & Integration Checks

Context:
  All components exist.
  We need a `pytest.ini`, GitHub Actions workflow `.github/workflows/ci.yml` to:
    - Install dependencies
    - Run `pytest --cov`
    - Report pass/fail
Approach:
  - Provide basic CI YAML for python 3.9+
  - Provide `pytest.ini` with markers.
Request:
  Provide both CI config files.
  Ensure on a fresh checkout tests pass.
```
