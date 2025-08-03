# Task 7: OpenRouter Integration Implementation Plan

## Overview
Adding OpenRouter API support to enable LLM-powered processing of recordings for tasks like summarization, style rewriting, date extraction, and chapter identification.

## Architecture Analysis ✅

**FastAPI Application Structure**:
- Entry point: `main.py` creates FastAPI app via `mnemovox/app.py:create_app()`
- Native async support throughout with `async def` endpoints
- Background tasks using FastAPI's `BackgroundTasks` 
- Dependency injection pattern for database sessions
- Template rendering with Jinja2 for web interface

**Configuration System**:
- YAML-based config in `mnemovox/config.py` with `@dataclass Config`
- Environment variable pattern not currently used but easily extensible
- Atomic config saving with validation in `save_config()`

**Database Models**:
- SQLAlchemy ORM with `Recording` model containing `transcript_text` field
- FTS5 search already implemented for transcript search
- Session management pattern via `get_session(db_path)` dependency

**API Patterns**:
- RESTful endpoints: `/api/recordings`, `/api/recordings/{id}`
- Background processing via `background_tasks.add_task()` 
- JSON responses with proper HTTP status codes
- Structured logging with `logging.getLogger(__name__)`

**Dependencies**: 
- `httpx` already available (dev dependency)
- FastAPI native async support
- Existing background task infrastructure

## Implementation Plan

### Phase 1: Architecture Analysis ✅
- [x] Examine current FastAPI app structure and patterns
- [x] Review YAML configuration system and dataclass pattern  
- [x] Check database models and Recording.transcript_text field
- [x] Confirm async support and background task infrastructure

### Phase 2: Core Infrastructure (MVP)
- [ ] **OpenRouter API Client** (`mnemovox/openrouter.py`)
  - Async HTTP client using `httpx` (already in dev dependencies)
  - Handle authentication with `OPENROUTER_API_KEY` env var via `os.getenv()`
  - Basic request/response handling with structured error handling
  - Support configurable model and parameters

- [ ] **Configuration Extension** 
  - Extend existing `Config` dataclass in `mnemovox/config.py`:
    - `openrouter_model: str = "gpt-3.5-turbo"` (default model)
    - `openrouter_base_url: str = "https://openrouter.ai/api/v1"` 
  - Use `os.getenv("OPENROUTER_API_KEY")` pattern (no YAML storage for secrets)

### Phase 3: Prompt Management System
- [ ] **Prompt Templates Module** (`mnemovox/prompts.py`)
  - Define structured prompt templates
  - Start with summarization prompt that uses `<summarization>` tags
  - Design for extensibility (future: rewriting, date extraction, etc.)

### Phase 3: LLM Processing Engine (MVP)
- [ ] **Simple Async Recording Processor** (`mnemovox/llm_processor.py`)
  - Async function: `async def summarize_recording(recording_id: int, db_path: str)`
  - Get recording from database, extract `transcript_text` field
  - Combine raw transcription + prompt template + task
  - Direct call to OpenRouter API (no queuing for MVP)
  - Parse LLM responses (extract content from `<summarization>` XML tags)
  - Use existing `logging.getLogger(__name__)` pattern for structured logging
  - Basic error handling (API failures, parsing issues, timeouts)

### Phase 4: FastAPI Integration (MVP)
- [ ] **API Endpoint**
  - Create `/api/recordings/{recording_id}/summarize` POST endpoint
  - Follow existing patterns: `async def`, `session=Depends(get_db_session)`
  - Use `background_tasks.add_task()` for async processing like transcription
  - Return JSON response with task status (similar to retranscription endpoint)
  - Integrate with existing error handling and logging patterns

- [ ] **Testing**
  - Unit tests for async OpenRouter client (follow existing `test_*.py` patterns)
  - Integration tests with mock API responses
  - Test prompt parsing and error scenarios  
  - Test async processing flow with background tasks

## Technical Decisions (MVP)

1. **FastAPI Integration**: Use existing async patterns, background tasks, and dependency injection
2. **Configuration Pattern**: Extend existing `Config` dataclass, use `os.getenv()` for API key
3. **Database Integration**: Use `Recording.transcript_text` field, existing session management
4. **HTTP Client**: Use `httpx` (already in dev dependencies) for async OpenRouter calls
5. **XML Tags for Output Parsing**: Using `<summarization>` tags for reliable extraction
6. **Logging Strategy**: Use existing `logging.getLogger(__name__)` pattern for structured logging
7. **Error Handling**: Follow existing patterns from transcription endpoints
8. **Testing**: Follow existing test patterns in `tests/test_*.py` files

## Future Enhancements (Post-MVP)

- **Rate Limiting**: Queue-based system to manage API costs and respect rate limits
- **Advanced Error Handling**: Retry logic with exponential backoff
- **Monitoring**: Metrics/monitoring for API usage and costs
- **Database Storage**: Move from logging to database storage for results

## Requirements (from Jesse)

1. **Configuration**: API key stored in `OPENROUTER_API_KEY` environment variable
2. **Input Format**: Send raw transcription text to LLM
3. **Output**: Log summarization results for now (database storage later)
4. **Model Strategy**: Single model for all tasks initially
5. **Rate Limiting**: Implement rate limiting/queuing for cost management
6. **Processing**: Async processing required

## Next Steps
Ready to proceed with Phase 1 (architecture analysis) to understand the current codebase structure, then implement the OpenRouter integration following the updated plan.

## Architecture Analysis Results ✅

**Key Findings**:
- FastAPI app with native async support and background tasks already implemented
- YAML config system with dataclass pattern easily extensible
- `httpx` already available in dev dependencies  
- Recording model has `transcript_text` field ready for LLM processing
- Existing logging, error handling, and testing patterns to follow

**Updated MVP Approach**:
- Leverage existing FastAPI async infrastructure (no new queue system needed)
- Extend existing config dataclass and use env vars for API key
- Follow established patterns for endpoints, background tasks, and testing
- Direct OpenRouter API calls using existing async patterns

## Implementation Ready ✅
Architecture analysis complete. Plan updated to leverage existing FastAPI patterns and infrastructure.