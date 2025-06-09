/**
 * Interactive Transcript Manager
 * Handles audio player synchronization with transcript segments
 */
class TranscriptManager {
    constructor(audioPlayerId, segments) {
        this.audioPlayer = document.getElementById(audioPlayerId);
        this.segments = segments || [];
        this.currentSegmentIndex = -1;
        this.autoScroll = true;
        
        // DOM elements
        this.transcriptText = document.getElementById('transcript-text');
        this.autoScrollCheckbox = document.getElementById('auto-scroll');
        this.jumpToCurrentButton = document.getElementById('jump-to-current');
        
        // Bind methods
        this.onTimeUpdate = this.onTimeUpdate.bind(this);
        this.onSegmentClick = this.onSegmentClick.bind(this);
        this.onPlaySegmentClick = this.onPlaySegmentClick.bind(this);
        this.onAutoScrollChange = this.onAutoScrollChange.bind(this);
        this.onJumpToCurrent = this.onJumpToCurrent.bind(this);
    }
    
    init() {
        if (!this.audioPlayer || !this.segments.length) {
            console.warn('TranscriptManager: Missing audio player or segments');
            return;
        }
        
        this.buildTranscript();
        this.setupEventListeners();
        this.setupSegmentButtons();
        
        console.log('TranscriptManager initialized with', this.segments.length, 'segments');
    }
    
    buildTranscript() {
        if (!this.transcriptText) return;
        
        // Build interactive transcript with clickable segments
        let transcriptHTML = '';
        
        this.segments.forEach((segment, index) => {
            const segmentClass = `transcript-segment`;
            const segmentId = `segment-${index}`;
            
            transcriptHTML += `<span class="${segmentClass}" 
                                    id="${segmentId}" 
                                    data-start="${segment.start}" 
                                    data-end="${segment.end}"
                                    data-index="${index}"
                                    title="Click to play from ${this.formatTime(segment.start)}">${segment.text}</span> `;
        });
        
        this.transcriptText.innerHTML = transcriptHTML;
        
        // Add click listeners to segments
        this.transcriptText.querySelectorAll('.transcript-segment').forEach(element => {
            element.addEventListener('click', this.onSegmentClick);
        });
    }
    
    setupEventListeners() {
        // Audio player time update
        this.audioPlayer.addEventListener('timeupdate', this.onTimeUpdate);
        
        // Auto-scroll checkbox
        if (this.autoScrollCheckbox) {
            this.autoScrollCheckbox.addEventListener('change', this.onAutoScrollChange);
        }
        
        // Jump to current button
        if (this.jumpToCurrentButton) {
            this.jumpToCurrentButton.addEventListener('click', this.onJumpToCurrent);
        }
    }
    
    setupSegmentButtons() {
        // Add click listeners to segment table play buttons
        document.querySelectorAll('.play-segment-btn').forEach(button => {
            button.addEventListener('click', this.onPlaySegmentClick);
        });
    }
    
    onTimeUpdate() {
        if (!this.audioPlayer) return;
        
        const currentTime = this.audioPlayer.currentTime;
        const newSegmentIndex = this.findCurrentSegmentIndex(currentTime);
        
        if (newSegmentIndex !== this.currentSegmentIndex) {
            this.updateCurrentSegment(newSegmentIndex);
        }
    }
    
    findCurrentSegmentIndex(currentTime) {
        for (let i = 0; i < this.segments.length; i++) {
            const segment = this.segments[i];
            if (currentTime >= segment.start && currentTime < segment.end) {
                return i;
            }
        }
        return -1;
    }
    
    updateCurrentSegment(newIndex) {
        // Remove previous highlights
        this.clearHighlights();
        
        // Update current segment index
        this.currentSegmentIndex = newIndex;
        
        if (newIndex >= 0) {
            // Highlight current segment in transcript
            const segmentElement = document.getElementById(`segment-${newIndex}`);
            if (segmentElement) {
                segmentElement.classList.add('playing');
                
                // Auto-scroll to current segment
                if (this.autoScroll) {
                    segmentElement.scrollIntoView({
                        behavior: 'smooth',
                        block: 'center'
                    });
                }
            }
            
            // Highlight current segment in table
            const segmentRows = document.querySelectorAll('.segment-row');
            if (segmentRows[newIndex]) {
                segmentRows[newIndex].classList.add('playing-segment');
            }
        }
    }
    
    clearHighlights() {
        // Clear transcript highlights
        document.querySelectorAll('.transcript-segment').forEach(element => {
            element.classList.remove('active', 'playing');
        });
        
        // Clear table highlights
        document.querySelectorAll('.segment-row').forEach(row => {
            row.classList.remove('current-segment', 'playing-segment');
        });
    }
    
    onSegmentClick(event) {
        const element = event.target;
        const startTime = parseFloat(element.dataset.start);
        
        if (!isNaN(startTime) && this.audioPlayer) {
            this.audioPlayer.currentTime = startTime;
            
            // Highlight clicked segment temporarily
            this.clearHighlights();
            element.classList.add('active');
            
            // Play if not already playing
            if (this.audioPlayer.paused) {
                this.audioPlayer.play().catch(console.error);
            }
        }
    }
    
    onPlaySegmentClick(event) {
        const button = event.target;
        const startTime = parseFloat(button.dataset.start);
        
        if (!isNaN(startTime) && this.audioPlayer) {
            this.audioPlayer.currentTime = startTime;
            
            // Play the audio
            this.audioPlayer.play().catch(console.error);
            
            // Update button text temporarily
            const originalText = button.textContent;
            button.textContent = '⏸ Playing';
            button.style.backgroundColor = '#dc3545';
            
            setTimeout(() => {
                button.textContent = originalText;
                button.style.backgroundColor = '#28a745';
            }, 1000);
        }
    }
    
    onAutoScrollChange(event) {
        this.autoScroll = event.target.checked;
    }
    
    onJumpToCurrent() {
        if (this.currentSegmentIndex >= 0) {
            const segmentElement = document.getElementById(`segment-${this.currentSegmentIndex}`);
            if (segmentElement) {
                segmentElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
            }
        }
    }
    
    formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }
    
    // Public API methods
    seekToSegment(segmentIndex) {
        if (segmentIndex >= 0 && segmentIndex < this.segments.length) {
            const segment = this.segments[segmentIndex];
            this.audioPlayer.currentTime = segment.start;
        }
    }
    
    getCurrentSegment() {
        return this.currentSegmentIndex >= 0 ? this.segments[this.currentSegmentIndex] : null;
    }
    
    toggleAutoScroll() {
        this.autoScroll = !this.autoScroll;
        if (this.autoScrollCheckbox) {
            this.autoScrollCheckbox.checked = this.autoScroll;
        }
    }
}

// Utility functions for transcript interaction
function buildTranscript(segments) {
    return segments.map(segment => segment.text).join(' ');
}

function renderSearchResults(segments, query) {
    if (!query) return segments;
    
    const lowerQuery = query.toLowerCase();
    return segments.filter(segment => 
        segment.text.toLowerCase().includes(lowerQuery)
    );
}

function exportTranscript(segments, format = 'text') {
    switch (format) {
        case 'srt':
            return exportSRT(segments);
        case 'vtt':
            return exportVTT(segments);
        case 'json':
            return JSON.stringify(segments, null, 2);
        default:
            return segments.map(segment => segment.text).join('\n\n');
    }
}

function exportSRT(segments) {
    return segments.map((segment, index) => {
        const start = formatSRTTime(segment.start);
        const end = formatSRTTime(segment.end);
        return `${index + 1}\n${start} --> ${end}\n${segment.text}\n`;
    }).join('\n');
}

function exportVTT(segments) {
    let vtt = 'WEBVTT\n\n';
    segments.forEach(segment => {
        const start = formatVTTTime(segment.start);
        const end = formatVTTTime(segment.end);
        vtt += `${start} --> ${end}\n${segment.text}\n\n`;
    });
    return vtt;
}

function formatSRTTime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 1000);
    
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')},${ms.toString().padStart(3, '0')}`;
}

function formatVTTTime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = (seconds % 60).toFixed(3);
    
    if (hours > 0) {
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.padStart(6, '0')}`;
    } else {
        return `${minutes.toString().padStart(2, '0')}:${secs.padStart(6, '0')}`;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        TranscriptManager,
        buildTranscript,
        renderSearchResults,
        exportTranscript
    };
}