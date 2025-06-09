/**
 * Search Manager for Audio Recording Search
 * Handles dynamic search functionality and UI interactions
 */
class SearchManager {
    constructor() {
        this.searchForm = null;
        this.searchInput = null;
        this.searchResults = null;
        this.currentQuery = '';
        this.searchTimeout = null;
        this.isLoading = false;
        
        // Configuration
        this.minQueryLength = 3;
        this.searchDelayMs = 500; // Delay before triggering search
    }
    
    init() {
        this.initializeElements();
        this.setupEventListeners();
        this.initializeExpandButtons();
        
        console.log('SearchManager initialized');
    }
    
    initializeElements() {
        this.searchForm = document.getElementById('search-form');
        this.searchInput = document.getElementById('search-input');
        this.searchResults = document.getElementById('search-results');
        
        if (!this.searchForm || !this.searchInput) {
            console.warn('SearchManager: Required elements not found');
            return;
        }
    }
    
    setupEventListeners() {
        if (!this.searchForm || !this.searchInput) return;
        
        // Form submission
        this.searchForm.addEventListener('submit', (e) => {
            this.handleFormSubmit(e);
        });
        
        // Real-time search as user types
        this.searchInput.addEventListener('input', (e) => {
            this.handleSearchInput(e);
        });
        
        // Clear search on escape
        this.searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.clearSearch();
            }
        });
        
        // Focus search input with Ctrl+K or Cmd+K
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                this.searchInput.focus();
                this.searchInput.select();
            }
        });
    }
    
    initializeExpandButtons() {
        const expandButtons = document.querySelectorAll('.expand-button');
        expandButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                this.toggleTranscript(e);
            });
        });
    }
    
    handleFormSubmit(e) {
        const query = this.searchInput.value.trim();
        
        if (query.length < this.minQueryLength) {
            e.preventDefault();
            this.showError(`Search query must be at least ${this.minQueryLength} characters long`);
            return;
        }
        
        // Allow form to submit normally for full page reload
        this.currentQuery = query;
    }
    
    handleSearchInput(e) {
        const query = e.target.value.trim();
        
        // Clear previous timeout
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }
        
        // Don't search if query is too short
        if (query.length < this.minQueryLength) {
            return;
        }
        
        // Debounce search
        this.searchTimeout = setTimeout(() => {
            this.performLiveSearch(query);
        }, this.searchDelayMs);
    }
    
    async performLiveSearch(query) {
        if (this.isLoading || query === this.currentQuery) {
            return;
        }
        
        this.currentQuery = query;
        this.isLoading = true;
        this.showLoadingState();
        
        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            
            if (!response.ok) {
                throw new Error(`Search failed: ${response.status}`);
            }
            
            const data = await response.json();
            this.updateSearchResults(data);
            
        } catch (error) {
            console.error('Search error:', error);
            this.showError('Search failed. Please try again.');
        } finally {
            this.isLoading = false;
            this.hideLoadingState();
        }
    }
    
    updateSearchResults(data) {
        if (!this.searchResults) {
            // If no results container, update URL for full page reload
            const url = new URL(window.location);
            url.searchParams.set('q', data.query);
            url.searchParams.set('page', '1');
            window.location.href = url.toString();
            return;
        }
        
        this.renderSearchResults(data);
        this.updatePageInfo(data);
    }
    
    renderSearchResults(data) {
        const resultsHtml = this.generateResultsHtml(data);
        this.searchResults.innerHTML = resultsHtml;
        
        // Re-initialize expand buttons for new results
        this.initializeExpandButtons();
        
        // Update browser history
        const url = new URL(window.location);
        url.searchParams.set('q', data.query);
        url.searchParams.set('page', '1');
        window.history.replaceState({}, '', url.toString());
    }
    
    generateResultsHtml(data) {
        if (!data.results || data.results.length === 0) {
            return this.generateNoResultsHtml(data.query);
        }
        
        let html = '';
        
        data.results.forEach(result => {
            html += `
                <div class="search-result-item" data-recording-id="${result.id}">
                    <div class="result-header">
                        <h3 class="result-filename">
                            <a href="/recordings/${result.id}" class="result-link">
                                ${this.escapeHtml(result.original_filename)}
                            </a>
                        </h3>
                        <div class="result-relevance">
                            <span class="relevance-score" title="Relevance Score">
                                ${result.relevance_score.toFixed(1)}
                            </span>
                        </div>
                    </div>
                    
                    <div class="result-excerpt">
                        ${result.excerpt}
                    </div>
                    
                    <div class="result-actions">
                        <a href="/recordings/${result.id}" class="action-link view-link">
                            📄 View Details
                        </a>
                        ${result.transcript_text ? `
                        <button class="action-button expand-button" data-recording-id="${result.id}">
                            📖 Show Full Transcript
                        </button>
                        ` : ''}
                    </div>
                    
                    ${result.transcript_text ? `
                    <div class="result-full-transcript" id="transcript-${result.id}" style="display: none;">
                        <div class="transcript-header">
                            <strong>Full Transcript:</strong>
                        </div>
                        <div class="transcript-content">
                            ${this.escapeHtml(result.transcript_text)}
                        </div>
                    </div>
                    ` : ''}
                </div>
            `;
        });
        
        return html;
    }
    
    generateNoResultsHtml(query) {
        return `
            <div class="no-results">
                <div class="no-results-icon">🔍</div>
                <h3>No results found</h3>
                <p>No recordings match your search for <strong>"${this.escapeHtml(query)}"</strong></p>
                <div class="no-results-suggestions">
                    <p>Try:</p>
                    <ul>
                        <li>Using different keywords</li>
                        <li>Checking for typos</li>
                        <li>Using more general terms</li>
                        <li>Searching for content that appears in transcript text</li>
                    </ul>
                </div>
            </div>
        `;
    }
    
    updatePageInfo(data) {
        // Update page title
        document.title = `Search: ${data.query} - Audio Recording Manager`;
        
        // Update search query info if it exists
        const queryInfo = document.querySelector('.search-query-info');
        if (queryInfo) {
            const resultCount = data.pagination.total;
            let infoText = `Searching for: <strong>"${this.escapeHtml(data.query)}"</strong>`;
            if (resultCount > 0) {
                infoText += ` - Found ${resultCount} result${resultCount !== 1 ? 's' : ''}`;
            }
            queryInfo.innerHTML = infoText;
        }
    }
    
    toggleTranscript(e) {
        const button = e.target;
        const recordingId = button.dataset.recordingId;
        const transcript = document.getElementById(`transcript-${recordingId}`);
        
        if (!transcript) return;
        
        const isVisible = transcript.style.display !== 'none';
        
        if (isVisible) {
            transcript.style.display = 'none';
            button.textContent = '📖 Show Full Transcript';
        } else {
            transcript.style.display = 'block';
            button.textContent = '📖 Hide Full Transcript';
            
            // Scroll to transcript smoothly
            transcript.scrollIntoView({
                behavior: 'smooth',
                block: 'nearest'
            });
        }
    }
    
    showLoadingState() {
        const button = this.searchForm.querySelector('.search-button');
        if (button) {
            button.disabled = true;
            button.innerHTML = '<span class="search-icon">⏳</span><span class="search-text">Searching...</span>';
        }
    }
    
    hideLoadingState() {
        const button = this.searchForm.querySelector('.search-button');
        if (button) {
            button.disabled = false;
            button.innerHTML = '<span class="search-icon">🔍</span><span class="search-text">Search</span>';
        }
    }
    
    showError(message) {
        // Create or update error message
        let errorElement = document.querySelector('.search-error');
        
        if (!errorElement) {
            errorElement = document.createElement('div');
            errorElement.className = 'search-error';
            errorElement.style.cssText = `
                background: #f8d7da;
                color: #721c24;
                padding: 10px 15px;
                border-radius: 6px;
                margin-top: 10px;
                border: 1px solid #f5c6cb;
            `;
            
            this.searchForm.appendChild(errorElement);
        }
        
        errorElement.textContent = message;
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            if (errorElement.parentNode) {
                errorElement.parentNode.removeChild(errorElement);
            }
        }, 5000);
    }
    
    clearSearch() {
        this.searchInput.value = '';
        this.currentQuery = '';
        
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }
        
        // Clear any error messages
        const errorElement = document.querySelector('.search-error');
        if (errorElement) {
            errorElement.parentNode.removeChild(errorElement);
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Public API methods
    focusSearch() {
        if (this.searchInput) {
            this.searchInput.focus();
            this.searchInput.select();
        }
    }
    
    setQuery(query) {
        if (this.searchInput) {
            this.searchInput.value = query;
            this.currentQuery = query;
        }
    }
    
    getQuery() {
        return this.searchInput ? this.searchInput.value.trim() : '';
    }
}

// Utility functions for search result processing
function highlightSearchTerms(text, searchTerms) {
    if (!text || !searchTerms) return text;
    
    let highlightedText = text;
    const terms = Array.isArray(searchTerms) ? searchTerms : [searchTerms];
    
    terms.forEach(term => {
        const regex = new RegExp(`(${escapeRegex(term)})`, 'gi');
        highlightedText = highlightedText.replace(regex, '<mark>$1</mark>');
    });
    
    return highlightedText;
}

function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function truncateText(text, maxLength = 200) {
    if (!text || text.length <= maxLength) return text;
    
    const truncated = text.substring(0, maxLength);
    const lastSpace = truncated.lastIndexOf(' ');
    
    if (lastSpace > maxLength * 0.8) {
        return truncated.substring(0, lastSpace) + '...';
    }
    
    return truncated + '...';
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        SearchManager,
        highlightSearchTerms,
        truncateText
    };
}