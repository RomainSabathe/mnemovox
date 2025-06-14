// ABOUTME: Jest tests for retranscribe.js modal functionality
// ABOUTME: Tests modal display, form submission, and error handling

/**
 * @jest-environment jsdom
 */

// Mock HTML structure for testing
const html = `
<div id="retranscribe-modal" style="display: none;">
    <div class="modal-content">
        <h3>Re-transcribe Recording</h3>
        <p>Warning: this will overwrite the existing transcript.</p>
        <div class="modal-form">
            <label for="modal-model-select">Model:</label>
            <select id="modal-model-select">
                <option value="tiny">Tiny</option>
                <option value="base">Base</option>
                <option value="small">Small</option>
            </select>
            
            <label for="modal-language-select">Language:</label>
            <select id="modal-language-select">
                <option value="auto">Auto Detect</option>
                <option value="en">English</option>
                <option value="fr">French</option>
            </select>
        </div>
        <div class="modal-buttons">
            <button id="modal-cancel-btn">Cancel</button>
            <button id="modal-submit-btn">Re-transcribe</button>
        </div>
    </div>
</div>
<button id="btn-retranscribe">Re-transcribe</button>
`;

describe("RetranscribeModal", () => {
    let modal;
    
    beforeEach(() => {
        document.body.innerHTML = html;
        
        // Mock fetch
        global.fetch = jest.fn();
        
        // Mock window.location
        delete window.location;
        window.location = { 
            pathname: '/recordings/123',
            reload: jest.fn()
        };
        
        // Load the RetranscribeModal class
        const RetranscribeModal = require("../static/js/retranscribe.js");
        
        // Create modal instance
        modal = new RetranscribeModal(123);
    });
    
    afterEach(() => {
        jest.clearAllMocks();
        document.body.innerHTML = '';
    });
    
    test("modal initializes with correct elements", () => {
        expect(modal.recordingId).toBe(123);
        expect(modal.modal).toBeTruthy();
        expect(modal.modelSelect).toBeTruthy();
        expect(modal.languageSelect).toBeTruthy();
        expect(modal.submitButton).toBeTruthy();
        expect(modal.cancelButton).toBeTruthy();
    });
    
    test("showModal displays modal and prevents body scroll", () => {
        modal.showModal();
        
        expect(modal.modal.style.display).toBe('block');
        expect(document.body.style.overflow).toBe('hidden');
    });
    
    test("hideModal hides modal and restores body scroll", () => {
        modal.showModal();
        modal.hideModal();
        
        expect(modal.modal.style.display).toBe('none');
        expect(document.body.style.overflow).toBe('');
    });
    
    test("clicking open button shows modal", () => {
        const openButton = document.getElementById('btn-retranscribe');
        openButton.click();
        
        expect(modal.modal.style.display).toBe('block');
    });
    
    test("clicking cancel button hides modal", () => {
        modal.showModal();
        modal.cancelButton.click();
        
        expect(modal.modal.style.display).toBe('none');
    });
    
    test("submitRetranscribe sends correct API request", async () => {
        // Setup form values
        modal.modelSelect.value = 'small';
        modal.languageSelect.value = 'fr';
        
        // Mock successful response
        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ id: 123, status: 'pending' })
        });
        
        await modal.submitRetranscribe();
        
        expect(global.fetch).toHaveBeenCalledWith('/api/recordings/123/transcribe', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                model: 'small',
                language: 'fr'
            })
        });
    });
    
    test("submitRetranscribe shows error for empty fields", async () => {
        // Leave fields empty
        modal.modelSelect.value = '';
        modal.languageSelect.value = '';
        
        await modal.submitRetranscribe();
        
        // Should not make API call
        expect(global.fetch).not.toHaveBeenCalled();
        
        // Should show error
        const errorElement = modal.modal.querySelector('.modal-error');
        expect(errorElement).toBeTruthy();
        expect(errorElement.textContent).toContain('Please select both model and language');
    });
    
    test("submitRetranscribe handles API error response", async () => {
        modal.modelSelect.value = 'small';
        modal.languageSelect.value = 'fr';
        
        // Mock error response
        global.fetch.mockResolvedValueOnce({
            ok: false,
            json: async () => ({ error: 'Invalid model' })
        });
        
        await modal.submitRetranscribe();
        
        const errorElement = modal.modal.querySelector('.modal-error');
        expect(errorElement).toBeTruthy();
        expect(errorElement.textContent).toContain('Invalid model');
    });
    
    test("submitRetranscribe handles network error", async () => {
        modal.modelSelect.value = 'small';
        modal.languageSelect.value = 'fr';
        
        // Mock network error
        global.fetch.mockRejectedValueOnce(new Error('Network error'));
        
        await modal.submitRetranscribe();
        
        const errorElement = modal.modal.querySelector('.modal-error');
        expect(errorElement).toBeTruthy();
        expect(errorElement.textContent).toContain('Network error');
    });
    
    test("setSubmitButtonLoading disables button and changes text", () => {
        modal.setSubmitButtonLoading(true);
        
        expect(modal.submitButton.disabled).toBe(true);
        expect(modal.submitButton.textContent).toBe('Processing...');
        
        modal.setSubmitButtonLoading(false);
        
        expect(modal.submitButton.disabled).toBe(false);
        expect(modal.submitButton.textContent).toBe('Re-transcribe');
    });
    
    test("successful submission shows toast and reloads page", async () => {
        modal.modelSelect.value = 'small';
        modal.languageSelect.value = 'fr';
        
        // Mock successful response
        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ id: 123, status: 'pending' })
        });
        
        // Mock setTimeout
        jest.useFakeTimers();
        
        await modal.submitRetranscribe();
        
        // Check that modal is hidden
        expect(modal.modal.style.display).toBe('none');
        
        // Check that toast is created
        const toast = document.querySelector('.success-toast');
        expect(toast).toBeTruthy();
        expect(toast.textContent).toContain('Re-transcription started successfully');
        
        // Fast-forward timers and check page reload
        jest.advanceTimersByTime(2000);
        expect(window.location.reload).toHaveBeenCalled();
        
        jest.useRealTimers();
    });
});
