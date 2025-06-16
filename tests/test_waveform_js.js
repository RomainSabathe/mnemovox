// ABOUTME: Tests for the waveform display logic.
// ABOUTME: Mocks WaveSurfer.js to verify initialization and event handling.

/**
 * @jest-environment jsdom
 */

const WaveformManager = require('../static/js/waveform.js');

// Mock WaveSurfer.js
const mockWaveSurfer = {
    load: jest.fn(),
    playPause: jest.fn(),
    on: jest.fn(),
    destroy: jest.fn(),
};

global.WaveSurfer = {
    create: jest.fn().mockReturnValue(mockWaveSurfer),
};

describe('WaveformManager', () => {
    let waveformManager;

    const html = `
        <div id="waveform"></div>
        <audio id="audio-player" src="/audio/test.mp3"></audio>
        <button id="btn-play-pause"></button>
        <span id="current-time">0:00</span>
        <span id="total-time">0:00</span>
    `;

    beforeEach(() => {
        document.body.innerHTML = html;
        
        // Clear all mocks before each test
        jest.clearAllMocks();

        // Mock requestAnimationFrame
        global.requestAnimationFrame = jest.fn();
    });

    test('should initialize and create a WaveSurfer instance', () => {
        waveformManager = new WaveformManager('#waveform', '#audio-player');
        waveformManager.init();

        expect(WaveSurfer.create).toHaveBeenCalledTimes(1);
        expect(WaveSurfer.create).toHaveBeenCalledWith(expect.objectContaining({
            container: document.querySelector('#waveform'),
            media: document.querySelector('#audio-player'),
        }));
    });

    test('should not initialize if waveform container is missing', () => {
        document.body.innerHTML = `<audio id="audio-player" src="/audio/test.mp3"></audio>`;
        waveformManager = new WaveformManager('#waveform', '#audio-player');
        waveformManager.init();
        expect(WaveSurfer.create).not.toHaveBeenCalled();
    });

    test('should not initialize if media element is missing', () => {
        document.body.innerHTML = `<div id="waveform"></div>`;
        waveformManager = new WaveformManager('#waveform', '#audio-player');
        waveformManager.init();
        expect(WaveSurfer.create).not.toHaveBeenCalled();
    });

    test('should set up event listeners on WaveSurfer instance', () => {
        waveformManager = new WaveformManager('#waveform', '#audio-player');
        waveformManager.init();

        expect(mockWaveSurfer.on).toHaveBeenCalledWith('play', expect.any(Function));
        expect(mockWaveSurfer.on).toHaveBeenCalledWith('pause', expect.any(Function));
        expect(mockWaveSurfer.on).toHaveBeenCalledWith('audioprocess', expect.any(Function));
        expect(mockWaveSurfer.on).toHaveBeenCalledWith('ready', expect.any(Function));
    });

    test('should hook up play/pause button', () => {
        waveformManager = new WaveformManager('#waveform', '#audio-player');
        waveformManager.init();

        const playPauseButton = document.getElementById('btn-play-pause');
        playPauseButton.click();

        expect(mockWaveSurfer.playPause).toHaveBeenCalledTimes(1);
    });

    test('should update play/pause button text on play/pause events', () => {
        waveformManager = new WaveformManager('#waveform', '#audio-player');
        waveformManager.init();
        const playPauseButton = document.getElementById('btn-play-pause');

        // Find the 'play' event handler and call it
        const playHandler = mockWaveSurfer.on.mock.calls.find(call => call[0] === 'play')[1];
        playHandler();
        expect(playPauseButton.textContent).toBe('Pause');

        // Find the 'pause' event handler and call it
        const pauseHandler = mockWaveSurfer.on.mock.calls.find(call => call[0] === 'pause')[1];
        pauseHandler();
        expect(playPauseButton.textContent).toBe('Play');
    });

    test('should update time displays on audioprocess and ready events', () => {
        waveformManager = new WaveformManager('#waveform', '#audio-player');
        waveformManager.init();
        const currentTimeEl = document.getElementById('current-time');
        const totalTimeEl = document.getElementById('total-time');

        // Simulate 'ready' event
        const readyHandler = mockWaveSurfer.on.mock.calls.find(call => call[0] === 'ready')[1];
        readyHandler(123.456); // duration
        expect(totalTimeEl.textContent).toBe('2:03');

        // Simulate 'audioprocess' event
        const audioprocessHandler = mockWaveSurfer.on.mock.calls.find(call => call[0] === 'audioprocess')[1];
        audioprocessHandler(65.432); // currentTime
        expect(currentTimeEl.textContent).toBe('1:05');
    });

    test('formatTime utility should correctly format seconds', () => {
        // This is a private method, but we can test it indirectly or expose it for testing
        // For now, let's create an instance and call it.
        waveformManager = new WaveformManager('#waveform', '#audio-player');
        expect(waveformManager.formatTime(0)).toBe('0:00');
        expect(waveformManager.formatTime(59)).toBe('0:59');
        expect(waveformManager.formatTime(60)).toBe('1:00');
        expect(waveformManager.formatTime(61)).toBe('1:01');
        expect(waveformManager.formatTime(123.456)).toBe('2:03');
        expect(waveformManager.formatTime(3600)).toBe('60:00'); // It doesn't handle hours, which is fine for most recordings.
    });
});
