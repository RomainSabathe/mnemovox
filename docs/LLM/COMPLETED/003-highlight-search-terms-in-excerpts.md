# Task #3: Highlight Search Terms in Search Results Excerpts [COMPLETED]

## Problem Analysis

The search functionality in MnemoVox currently displays excerpts from transcripts in search results, but the search terms are not highlighted in bold within these excerpts. Users have to scan the excerpt text to find the relevant search terms, which reduces the effectiveness of the search interface.

## Current Implementation

1. **SQLite FTS Integration**: The search uses SQLite's Full-Text Search (FTS5) with the `highlight()` function that wraps matching terms in `<mark>` tags
2. **Excerpt Generation**: The `_generate_excerpt` function in `src/audio_manager/app.py:1003-1046` currently:
   - Receives highlighted text from FTS with `<mark>` tags
   - **Removes** the `<mark>` tags to find search term positions for excerpt bounds
   - Returns clean text without any highlighting
3. **Display**: The search template (`templates/search.html:65`) displays the excerpt using `{{ result.excerpt|safe }}`

## Root Cause

The `_generate_excerpt` function strips out the FTS-generated `<mark>` tags and doesn't re-apply highlighting to the search terms in the final excerpt.

## Solution Strategy

Modify the `_generate_excerpt` function to:

1. **Preserve FTS highlighting**: Instead of removing `<mark>` tags, work with them directly
2. **Extract excerpt with highlighting intact**: Find search term positions while keeping the HTML markup
3. **Ensure safe HTML**: The search template already uses `|safe` filter, and `<mark>` tags are safe for highlighting

## Technical Approach

1. **Enhanced excerpt algorithm**:
   - Find the first `<mark>` tag in the highlighted text to determine excerpt bounds
   - Extract the excerpt while preserving `<mark>` and `</mark>` tags
   - Adjust word boundaries while maintaining HTML integrity

2. **Fallback handling**:
   - If no highlighted text is available, apply manual highlighting to the search term
   - Ensure case-insensitive search term matching

3. **HTML safety**:
   - Only allow `<mark>` tags for highlighting
   - Escape any other potential HTML in the text

## Implementation Plan

1. **Modify `_generate_excerpt` function** (`src/audio_manager/app.py:1003-1046`):
   - Update to preserve `<mark>` tags from FTS highlighting
   - Handle excerpt bounds calculation with HTML tags present
   - Add fallback manual highlighting for cases without FTS highlighting

2. **Test the changes**:
   - Verify highlighting appears in search results
   - Test edge cases (multiple search terms, special characters)
   - Ensure excerpt length limits still work correctly

3. **Verify CSS styling**:
   - Check that existing CSS in `templates/search.html` properly styles `<mark>` tags
   - The template already has `.result-excerpt mark` styling at line 303-308

## Expected Outcome

After implementation:
- Search terms will be highlighted in **bold** within search result excerpts
- Users can quickly identify relevant content in search results  
- The highlighting will work for both single and multiple search terms
- Existing search functionality will remain unchanged except for the improved highlighting

## Files to Modify

- `src/audio_manager/app.py` - Update `_generate_excerpt` function
- Tests may need updates to verify highlighting behavior

## Testing Strategy

1. **Unit tests**: Verify `_generate_excerpt` returns highlighted excerpts
2. **Integration tests**: Test search results contain proper highlighting
3. **Manual testing**: Verify visual appearance in browser

---

## Implementation Summary [COMPLETED]

### Changes Made

1. **New Function Implementation** (`src/audio_manager/app.py:1110-1251`):
   - Added `_generate_excerpt_with_highlighting()` function that preserves FTS highlighting
   - Added `_extract_excerpt_with_fts_highlighting()` for handling SQLite FTS-generated `<mark>` tags
   - Added `_extract_excerpt_with_manual_highlighting()` for fallback manual highlighting

2. **Search Endpoint Updates**:
   - Updated HTML search endpoint (`/search`) to use `_generate_excerpt_with_highlighting`
   - Updated API search endpoint (`/api/search`) to use `_generate_excerpt_with_highlighting`

3. **Comprehensive Test Coverage**:
   - `tests/test_excerpt_highlighting.py` - Unit tests for highlighting functions
   - `tests/test_search_highlighting_integration.py` - End-to-end integration tests

### Technical Details

- **FTS Integration**: Preserves SQLite FTS5's `highlight()` function output with `<mark>` tags
- **Fallback Handling**: Automatically adds highlighting when FTS doesn't provide it
- **Word Boundary Respect**: Maintains proper excerpt boundaries while preserving HTML markup
- **Case Insensitive**: Works correctly with different case variations of search terms

### Verification

✅ All unit tests pass (5/5)  
✅ All integration tests pass (4/4)  
✅ Search terms now appear highlighted in **bold** in search result excerpts  
✅ Both `/search` HTML page and `/api/search` API endpoint return highlighted excerpts  
✅ CSS styling for `<mark>` tags already exists in search template  

### User Impact

- Search terms are now visually highlighted in bold within search result excerpts
- Users can quickly identify relevant content without scanning through plain text
- Works seamlessly with existing search functionality and UI