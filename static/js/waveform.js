// ABOUTME: Manages the wavesurfer.js audio waveform display.
// ABOUTME: Initializes WaveSurfer, handles playback controls, and syncs with the audio element.

class WaveformManager {
    constructor(containerSelector, mediaSelector) {
        this.container = document.querySelector(containerSelector);
        this.mediaElement = document.querySelector(mediaSelector);
        this.wavesurfer = null;
        this.playPauseButton = document.getElementById('btn-play-pause');
        this.currentTimeEl = document.getElementById('current-time');
        this.totalTimeEl = document.getElementById('total-time');
    }

    init() {
        if (!this.container || !this.mediaElement) {
            console.warn('WaveformManager: container or media element not found. Aborting initialization.');
            return;
        }

        // Hide the original audio player controls
        this.mediaElement.controls = false;

        this.wavesurfer = WaveSurfer.create({
            container: this.container,
            media: this.mediaElement,
            waveColor: '#ddd',
            progressColor: '#007bff',
            barWidth: 2,
            barGap: 1,
            barRadius: 2,
            height: 100,
            responsive: true,
        });

        this.setupEventListeners();
    }

    setupEventListeners() {
        if (!this.wavesurfer) return;

        // Play/Pause button
        if (this.playPauseButton) {
            this.playPauseButton.addEventListener('click', () => {
                this.wavesurfer.playPause();
            });
        }

        // Update button text on play/pause
        this.wavesurfer.on('play', () => {
            if (this.playPauseButton) this.playPauseButton.textContent = 'Pause';
        });

        this.wavesurfer.on('pause', () => {
            if (this.playPauseButton) this.playPauseButton.textContent = 'Play';
        });

        // Update current time display
        this.wavesurfer.on('audioprocess', (currentTime) => {
            if (this.currentTimeEl) this.currentTimeEl.textContent = this.formatTime(currentTime);
        });

        // Set total time on ready
        this.wavesurfer.on('ready', (duration) => {
            if (this.totalTimeEl) this.totalTimeEl.textContent = this.formatTime(duration);
        });
    }

    formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // The audio player element is used by both the waveform and the transcript manager.
    // The waveform manager will now control playback.
    const waveformManager = new WaveformManager('#waveform', '#audio-player');
    waveformManager.init();
});

// Export for testing purposes
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WaveformManager;
}
