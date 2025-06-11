For all these prompts, refer to **@spec.md** to understand the global context of what you
are building.

# Phase 1

```text
PROMPT 1/8: Project Scaffold & Config Loader ✅ COMPLETED

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
PROMPT 2/8: Database Schema & Initialization ✅ COMPLETED

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
PROMPT 3/8: Audio Utilities (probe + filename) ✅ COMPLETED

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
PROMPT 4/8: Watcher & Ingestion Pipeline ✅ COMPLETED

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
PROMPT 5/8: Transcription Module ✅ COMPLETED

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
PROMPT 6/8: Orchestrate Ingestion → Transcription ✅ COMPLETED

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
PROMPT 7/8: FastAPI Backend & UI ✅ COMPLETED

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
PROMPT 8/8: CI & Integration Checks ✅ COMPLETED

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

# Phase 2

```text
PROMPT A/8: Config & FTS Setup ✅ COMPLETED

Context:
  We’ve completed Phase 1. Now Phase 2 needs:
    - config.yaml keys: upload_temp_path, fts_enabled, items_per_page
    - DB init creates FTS5 table `recordings_fts`
    - Helper `sync_fts(recording_id)`

Steps:
  1. Write `tests/test_config_phase2.py` covering loading new keys & defaults.
  2. Update `config.py` for new fields.
  3. Write `tests/test_db_fts.py` verifying:
     - `init_db()` creates `recordings_fts` when fts_enabled
     - `sync_fts()` populates FTS table for a sample recording row
  4. Implement `db.py` changes:
     - In `init_db()`: execute `CREATE VIRTUAL TABLE ...` if enabled
     - Add `sync_fts(session, recording_id)`

Deliver:
  - `tests/test_config_phase2.py`
  - Updated `config.py`
  - `tests/test_db_fts.py`
  - Updated `db.py`
```

---

```text
PROMPT B/8: API Upload Endpoint ✅ COMPLETED

Context:
  Phase 2 requires web upload:
    - POST /api/recordings/upload
    - Use config.upload_temp_path then existing ingestion logic

Steps:
  1. Write `tests/test_api_upload.py` using TestClient:
     - Valid audio → 201 JSON { id, status:"pending" }
     - Invalid ext → 400 JSON { error }
  2. In `app.py`, add `@app.post("/api/recordings/upload")`:
     - Accept `file: UploadFile`
     - Validate extension
     - Save to `upload_temp_path/<uuid>_<orig>`
     - Call existing `ingest_file(path)`
     - Return JSON
  3. Write integration test asserting DB row inserted and file moved.

Deliver:
  - `tests/test_api_upload.py`
  - Updated `app.py` (upload handler)
```

---

```text
PROMPT C/8: Listings & Pagination ✅ COMPLETED

Context:
  We need:
    - GET `/api/recordings?page=&per_page=`
    - GET `/recordings` HTML page (first page server-rendered)

Steps:
  1. Write `tests/test_api_list.py`: default & boundary pagination.
  2. Implement API route in `app.py`.
  3. Create `templates/recordings_list.html` rendering initial page of recordings.
  4. Write `tests/test_page_list.py` asserting HTML response and presence of recordings data.

Deliver:
  - `tests/test_api_list.py`
  - Updated `app.py` (list endpoint)
  - `templates/recordings_list.html`
  - `tests/test_page_list.py`
```

---

```text
PROMPT D/8: Detail Page & Interactive Transcript ✅ COMPLETED

Context:
  Phase 2 UI: detail page + JS-driven transcript.

Steps:
  1. Write `tests/test_api_detail.py` for:
     - GET `/api/recordings/{id}`
     - GET `/api/recordings/{id}/segments`
  2. Implement these API handlers in `app.py`.
  3. Create `templates/recording_detail.html` with:
     - `<audio id="player">`
     - `<div id="transcript"></div>`
     - `<script src="/static/js/transcript.js"></script>`
  4. Write `js/transcript.js` (skeleton) and `tests/test_transcript_js.js` for its `buildTranscript()` function.
  5. Write `tests/test_page_detail.py` ensuring page loads and includes player & script tag.

Deliver:
  - `tests/test_api_detail.py`
  - Updated `app.py`
  - `templates/recording_detail.html`
  - `static/js/transcript.js`
  - `tests/test_transcript_js.js`
  - `tests/test_page_detail.py`
```

---

```text
PROMPT E/8: Re-transcription Endpoint ✅ COMPLETED

Context:
  We need manual re-transcription trigger:
    - POST `/api/recordings/{id}/transcribe` → sets status pending + enqueues job

Steps:
  1. Write `tests/test_api_retranscribe.py`:
     - POST valid id → 200 {id, status:"pending"} & DB status updated
     - POST invalid id → 404
  2. In `app.py`, add handler using `BackgroundTasks`:
     - Update DB
     - `background_tasks.add_task(run_transcription, id)`
  3. Write integration test verifying job enqueued (mock BackgroundTasks) and DB change.

Deliver:
  - `tests/test_api_retranscribe.py`
  - Updated `app.py`
```

---

```text
PROMPT F/8: Search API & UI ✅ COMPLETED

Context:
  Implement full-text search:
    - GET `/api/search?q=&page=&per_page=`
    - GET `/search` page with form + JS

Steps:
  1. Write `tests/test_api_search.py`:
     - q < 3 → 400
     - Valid q → JSON hits with excerpt
  2. Implement API using `session.execute("SELECT ... FROM recordings_fts ...")`.
  3. Create `templates/search.html` with form and `<div id="results">`
  4. Write `static/js/search.js` + `tests/test_search_js.js` testing `renderSearchResults()`.
  5. Write `tests/test_page_search.py` for HTML `/search?q=...`.

Deliver:
  - `tests/test_api_search.py`
  - Updated `app.py`
  - `templates/search.html`
  - `static/js/search.js`
  - `tests/test_search_js.js`
  - `tests/test_page_search.py`
```

---

```text
PROMPT G/8: Background Task Orchestration ✅ COMPLETED

Context:
  Tie ingestion & re-transcription into background tasks

Steps:
  1. Write `tests/test_background_task.py` mocking `transcriber.transcribe_file`
     - Ensure `run_transcription(id)` updates DB status/text/segments
  2. In `pipeline.py` or `app.py`, implement `run_transcription(recording_id)`:
     - Load path from DB, call `transcribe_file()`, update DB, sync FTS
     - Exception → status="error"
  3. Wire BackgroundTasks usage in both upload & retranscribe handlers.

Deliver:
  - `tests/test_background_task.py`
  - `pipeline.py` (or update in `app.py`)
```

---

```text
PROMPT H/8: Testing & CI Updates ✅ COMPLETED

Context:
  Phase 2 adds new tests & static assets

Steps:
  1. Update `pytest.ini` to include `tests/*_phase2.py` and js tests.
  2. Create `.github/workflows/ci.yml`:
     - Python 3.9+
     - Install deps
     - Run `pytest --cov`
  3. Add/update `README.md` section “Phase 2 Setup & Usage”.

Deliver:
  - Updated `pytest.ini`
  - `.github/workflows/ci.yml`
  - Updated `README.md`
```

# Phase 2.5

---

```text
PROMPT A/6: DB Migration & Model Update

Context:
  We have Phase 1 & 2 done. Now add per-recording overrides.
  Use SQLite and SQLAlchemy.

Steps:
  1. Create `tests/test_db_migration.py`:
     - Apply migration script `migrations/002_add_overrides.py`
     - Inspect sqlite_master → table `recordings` has columns `transcription_model`, `transcription_language`
  2. Write `migrations/002_add_overrides.py`:
     - SQL: ALTER TABLE recordings ADD COLUMN transcription_model VARCHAR NULL;
     - Same for transcription_language.
  3. Update `db.py` Recording model:
     - Add `transcription_model: Optional[str]`
     - Add `transcription_language: Optional[str]`
  4. Ensure existing tests for ingestion & transcription still pass.

Deliver:
  - `tests/test_db_migration.py`
  - `migrations/002_add_overrides.py`
  - Updated `db.py`
```

---

```text
PROMPT B/6: Config Manager Load & Save

Context:
  Extend `config.py` to support saving globals back to YAML.

Steps:
  1. Write `tests/test_config_save.py`:
     - Given a temp `config.yml` with known defaults
     - Load via `get_config()`, modify `default_model`, `default_language`
     - Call `save_config()` → file on disk updated
     - Reload `get_config()` → returns updated defaults
     - Test invalid YAML causing save error → raises exception
  2. Implement in `config.py`:
     - Add `save_config(changes: dict)` that:
       • Reads existing YAML
       • Merges `changes`
       • Writes back (atomic write)
       • Updates in-memory config object
  3. Ensure existing config tests still pass.

Deliver:
  - `tests/test_config_save.py`
  - Updated `config.py`
```

---

```text
PROMPT C/6: API Settings Endpoints

Context:
  Expose GET/POST `/api/settings` to read & write global transcription defaults.

Steps:
  1. Write `tests/test_api_settings.py` using FastAPI TestClient:
     - GET `/api/settings` → 200 + JSON `{ default_model, default_language }`
     - POST valid JSON → 200 + same JSON, underlying `config.yml` updated
     - POST invalid model/language → 400 + `{ error }`
  2. In `app.py`, add:
     - `@app.get("/api/settings")` → returns `get_config().defaults`
     - `@app.post("/api/settings")` → validates input, calls `save_config()`, returns updated
  3. Mock filesystem writes in tests to avoid side effects.

Deliver:
  - `tests/test_api_settings.py`
  - Updated `app.py`
```

---

```text
PROMPT D/6: Frontend Settings Page

Context:
  Build `/settings` HTML + JS to manage global defaults.

Steps:
  1. Write `tests/test_page_settings.py`:
     - GET `/settings` → 200 + HTML contains `<form id="settings-form">` with selects pre-selected
  2. Create `templates/settings.html`:
     - Extends base
     - Form with two `<select>` for `default_model` & `default_language`
     - `<div id="toast"></div>`
     - Includes `<script src="/static/js/settings.js">`
  3. Write `static/js/settings.js` and `tests/test_settings_js.js`:
     - On submit, fetch POST `/api/settings`, show success/error toast
  4. Ensure style & UX minimal but functional.

Deliver:
  - `tests/test_page_settings.py`
  - `templates/settings.html`
  - `static/js/settings.js`
  - `tests/test_settings_js.js`
```

---

```text
PROMPT E/6: Detail Page Enhancements & Re-transcribe Modal

Context:
  Extend detail page to show overrides and modal.

Steps:
  1. Write `tests/test_page_detail_overrides.py`:
     - GET `/recordings/{id}` → HTML contains “Current Model:” and “Current Language:”
     - Contains `<button id="btn-retranscribe">`
  2. Update `templates/recording_detail.html`:
     - Display override columns or global defaults
     - Add `btn-retranscribe`, modal skeleton `<div id="retranscribe-modal">` hidden
     - Include `<script src="/static/js/retranscribe.js">`
  3. Write `static/js/retranscribe.js` + `tests/test_retranscribe_js.js`:
     - On click, show modal, pre-fill selects with current values
     - On modal submit, POST `/api/recordings/{id}/transcribe` with `{model,language}`
     - On success, close modal, refresh transcript container; on error, show toast
  4. Write `tests/test_api_retranscribe_override.py`:
     - POST valid override → 200/202, DB columns updated
     - POST invalid → 400; non-existent id → 404

Deliver:
  - `tests/test_page_detail_overrides.py`
  - `templates/recording_detail.html`
  - `static/js/retranscribe.js`
  - `tests/test_retranscribe_js.js`
  - `tests/test_api_retranscribe_override.py`
  - Updated `/api/recordings/{id}/transcribe` in `app.py`
```

---

```text
PROMPT F/6: Waveform Display Integration

Context:
  Add wavesurfer.js waveform to detail page.

Steps:
  1. Write `tests/test_page_detail_waveform.py`:
     - GET `/recordings/{id}` → HTML contains `<div id="waveform"></div>` and `<script src="https://unpkg.com/wavesurfer.js"></script>`
     - Also includes `<script src="/static/js/waveform.js">`
  2. Create `static/js/waveform.js` and `tests/test_waveform_js.js`:
     - JS to instantiate `WaveSurfer.create({ container:'#waveform', ... })` and `load(audioUrl)`
     - Hook play/pause button `#btn-play` to `ws.playPause()`
  3. Update `templates/recording_detail.html` to include waveform container and play/pause controls.
  4. Verify end-to-end via TestClient + manual.

Deliver:
  - `tests/test_page_detail_waveform.py`
  - `static/js/waveform.js`
  - `tests/test_waveform_js.js`
  - Updated `templates/recording_detail.html`
```
