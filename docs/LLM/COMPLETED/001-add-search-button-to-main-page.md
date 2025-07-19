# Current Task: Add Search Button to Main Page

## Task Description
Task #1 from TODO.md: The app has a search functionality that can be accessed with the /search endpoint. However, there is no button on the main page (`/`, `templates/recordings_list.html`) to access it. Add a button or a link to go to the search page. Find a suitable location for the button or link.

## Analysis
- The search functionality already exists at `/search` endpoint
- The main page is at `/` which renders `templates/recordings_list.html`
- I need to examine the current template to understand the layout and find a suitable location for the search button/link
- This is a simple frontend addition - no backend changes needed

## Investigation Plan
1. Examine the current `templates/recordings_list.html` template
2. Check the app.py to understand the search endpoint structure
3. Find the most appropriate location for the search button/link in the UI
4. Implement the button/link with proper styling to match existing design

## Implementation Plan
1. Read the current recordings_list.html template
2. Read the app.py to understand the search endpoint
3. Add a search button/link in an appropriate location (likely near the top of the page)
4. Ensure the styling matches the existing design
5. Test that the link works properly

## Expected Outcome
Users will be able to navigate from the main recordings list page to the search page easily via a visible button or link.