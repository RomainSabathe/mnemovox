# Task 8: Implement Title Assessment and Formatting LLM Tasks

## Problem Analysis

The existing OpenRouter integration (Task 7) provides a solid foundation with:
- Generic `process_recording_with_llm()` function that can handle any task
- Template-based prompt system with XML tag parsing
- Proper error handling and logging
- API endpoint pattern for triggering LLM tasks

Task 8 requires extending this system with two new LLM processing tasks:
1. **Title Assessment**: Generate appropriate titles for recordings
2. **Formatting**: Fix spelling, grammar, sentence structure, and add section breaks

## Implementation Plan

### 1. Extend Prompt Templates (prompts.py)

Add two new prompt templates following the existing pattern:

**Title Assessment Prompt:**
- Input: transcript text
- Output: 2-3 title suggestions (no rationales)
- XML tags: Multiple `<title>` tags
- Focus on: main topic identification, brevity, descriptiveness
- Special parsing: Extract all `<title>` tags (custom parsing method needed)

**Formatting Prompt:**
- Input: transcript text  
- Output: cleaned and formatted text
- XML tag: `<formatted_text>`
- Focus on: spelling/grammar correction, sentence structure, paragraph breaks, section headers

### 2. Implement Processing Functions (llm_processor.py)

Create specific functions similar to `summarize_recording()`:
- `assess_title_recording(recording_id, db_path)` - logs all title suggestions
- `format_recording(recording_id, db_path)` - logs formatted text

Both will leverage the existing generic `process_recording_with_llm()` function and follow the async background task pattern.

### 3. Add API Endpoints (app.py)

Following the existing `/api/recordings/{recording_id}/summarize` pattern:
- `POST /api/recordings/{recording_id}/assess-title`
- `POST /api/recordings/{recording_id}/format`

Both will use FastAPI background tasks for async processing.

### 4. Testing Strategy

Extend existing test coverage:
- Unit tests for new prompt templates (test_openrouter.py)
- Integration tests for new API endpoints (new test files)
- Test prompt formatting and response parsing

## Detailed Implementation

### Title Assessment Prompt Design

The prompt should be comprehensive and specific as requested:

```
You are an expert at analyzing audio transcriptions and creating appropriate titles. 
Based on the following transcription, suggest 2-3 potential titles that accurately 
represent the main content and would be useful for organizing and searching.

Guidelines:
- Titles should be concise (5-10 words maximum)
- Focus on the main topic or purpose of the recording
- Consider the context and setting if evident
- Avoid generic titles like "Recording" or "Audio Note"
- If the content has multiple distinct topics, reflect the primary focus

Transcription to analyze:
{transcript_text}

Please provide your title suggestions using multiple <title> tags:

<title>First title suggestion</title>
<title>Second title suggestion</title>
<title>Third title suggestion</title>
```

### Formatting Prompt Design

```
You are an expert editor specializing in cleaning up audio transcriptions.  
Improve the following transcription by fixing spelling mistakes, correcting grammar, 
improving sentence structure, and organizing the content into clear sections.

Tasks to perform:
- Fix spelling errors and typos
- Correct grammatical mistakes
- Improve sentence structure and flow
- Remove filler words and false starts (um, uh, like, you know)
- Add appropriate punctuation
- Break content into logical paragraphs
- Add section headers if the content covers multiple distinct topics
- Preserve the original meaning and tone
- Maintain first-person perspective if present

Original transcription:
{transcript_text}

Please provide the formatted version within <formatted_text> tags:

<formatted_text>
Your cleaned and formatted transcription here
</formatted_text>
```

## Implementation Decisions

**Storage Strategy**: Following the existing pattern, all results will be logged to stdout only. No database changes needed - this allows for prompt iteration and testing before finalizing storage approach.

**Title Handling**: All title suggestions will be logged. Future implementation will allow default selection + user choice.

**Formatting Scope**: Formatted text will be logged only, preserving original transcripts unchanged.

**API Pattern**: Following existing async pattern with FastAPI background tasks, matching the summarization endpoint.

## Next Steps

1. Implement the prompt templates
2. Add the processing functions  
3. Create API endpoints
4. Write comprehensive tests
5. Update documentation

The existing infrastructure makes this implementation straightforward - we're essentially extending a proven pattern with new prompt templates.
