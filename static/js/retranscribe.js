// ABOUTME: JavaScript for re-transcribe modal functionality on recording detail page
// ABOUTME: Handles modal display, form submission, and API communication for transcription overrides

class RetranscribeModal {
    constructor(recordingId) {
        this.recordingId = recordingId;
        this.modal = null;
        this.modelSelect = null;
        this.languageSelect = null;
        this.submitButton = null;
        this.cancelButton = null;
        this.isSubmitting = false;
        
        this.init();
    }
    
    init() {
        this.modal = document.getElementById('retranscribe-modal');
        this.modelSelect = document.getElementById('modal-model-select');
        this.languageSelect = document.getElementById('modal-language-select');
        this.submitButton = document.getElementById('modal-submit-btn');
        this.cancelButton = document.getElementById('modal-cancel-btn');
        
        if (!this.modal || !this.modelSelect || !this.languageSelect) {
            console.warn('RetranscribeModal: Required elements not found');
            return;
        }
        
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Open modal button
        const openButton = document.getElementById('btn-retranscribe');
        if (openButton) {
            openButton.addEventListener('click', () => this.showModal());
        }
        
        // Cancel button
        if (this.cancelButton) {
            this.cancelButton.addEventListener('click', () => this.hideModal());
        }
        
        // Submit button
        if (this.submitButton) {
            this.submitButton.addEventListener('click', () => this.submitRetranscribe());
        }
        
        // Close modal when clicking outside
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.hideModal();
            }
        });
        
        // Close modal on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal.style.display === 'block') {
                this.hideModal();
            }
        });
    }
    
    showModal() {
        if (!this.modal) return;
        
        this.modal.style.display = 'block';
        document.body.style.overflow = 'hidden'; // Prevent background scrolling
        
        // Focus on the first select element
        if (this.modelSelect) {
            this.modelSelect.focus();
        }
    }
    
    hideModal() {
        if (!this.modal) return;
        
        this.modal.style.display = 'none';
        document.body.style.overflow = ''; // Restore scrolling
        this.clearError();
    }
    
    async submitRetranscribe() {
        if (this.isSubmitting) return;
        
        const model = this.modelSelect.value;
        const language = this.languageSelect.value;
        
        if (!model || !language) {
            this.showError('Please select both model and language');
            return;
        }
        
        this.isSubmitting = true;
        this.setSubmitButtonLoading(true);
        this.clearError();
        
        try {
            const response = await fetch(`/api/recordings/${this.recordingId}/transcribe`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    model: model,
                    language: language
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.hideModal();
                this.showSuccessToast('Re-transcription started successfully. The page will refresh shortly.');
                
                // Refresh the page after a short delay to show the updated status
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            } else {
                this.showError(data.error || 'Failed to start re-transcription');
            }
        } catch (error) {
            console.error('Re-transcription error:', error);
            this.showError('Network error. Please try again.');
        } finally {
            this.isSubmitting = false;
            this.setSubmitButtonLoading(false);
        }
    }
    
    setSubmitButtonLoading(loading) {
        if (!this.submitButton) return;
        
        if (loading) {
            this.submitButton.disabled = true;
            this.submitButton.textContent = 'Processing...';
        } else {
            this.submitButton.disabled = false;
            this.submitButton.textContent = 'Re-transcribe';
        }
    }
    
    showError(message) {
        let errorElement = this.modal.querySelector('.modal-error');
        
        if (!errorElement) {
            errorElement = document.createElement('div');
            errorElement.className = 'modal-error';
            errorElement.style.cssText = `
                background: #f8d7da;
                color: #721c24;
                padding: 10px;
                border-radius: 4px;
                margin-bottom: 15px;
                border: 1px solid #f5c6cb;
            `;
            
            // Insert before the form buttons
            const buttonsContainer = this.modal.querySelector('.modal-buttons');
            if (buttonsContainer) {
                buttonsContainer.parentNode.insertBefore(errorElement, buttonsContainer);
            }
        }
        
        errorElement.textContent = message;
        errorElement.style.display = 'block';
    }
    
    clearError() {
        const errorElement = this.modal.querySelector('.modal-error');
        if (errorElement) {
            errorElement.style.display = 'none';
        }
    }
    
    showSuccessToast(message) {
        const toast = document.createElement('div');
        toast.className = 'success-toast';
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #d4edda;
            color: #155724;
            padding: 15px 20px;
            border-radius: 6px;
            border: 1px solid #c3e6cb;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            z-index: 10000;
            max-width: 400px;
            font-weight: 500;
        `;
        
        document.body.appendChild(toast);
        
        // Remove toast after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 5000);
    }
}

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RetranscribeModal;
} else if (typeof window !== 'undefined') {
    window.RetranscribeModal = RetranscribeModal;
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Get recording ID from the page URL or data attribute
    const pathParts = window.location.pathname.split('/');
    const recordingId = pathParts[pathParts.length - 1];
    
    if (recordingId && !isNaN(recordingId)) {
        new RetranscribeModal(parseInt(recordingId));
    }
});
