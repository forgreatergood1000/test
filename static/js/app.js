/**
 * Main JavaScript file for SAML Azure AD Authentication App
 * Handles client-side functionality and user interactions
 */

// Global app configuration
const App = {
    config: {
        sessionCheckInterval: 60000, // Check session every minute
        alertAutoHideDelay: 5000,    // Auto-hide alerts after 5 seconds
        animationDuration: 300       // Animation duration in ms
    },
    
    // Initialize the application
    init: function() {
        this.setupEventListeners();
        this.initializeComponents();
        this.startSessionMonitoring();
        console.log('SAML Auth App initialized');
    },
    
    // Set up event listeners
    setupEventListeners: function() {
        // Auto-hide alerts
        document.addEventListener('DOMContentLoaded', function() {
            const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
            alerts.forEach(alert => {
                setTimeout(() => {
                    App.hideAlert(alert);
                }, App.config.alertAutoHideDelay);
            });
        });
        
        // Handle form submissions
        document.addEventListener('submit', function(e) {
            const form = e.target;
            if (form.classList.contains('needs-validation')) {
                App.validateForm(form, e);
            }
        });
        
        // Handle copy-to-clipboard functionality
        document.addEventListener('click', function(e) {
            if (e.target.classList.contains('copy-btn')) {
                App.copyToClipboard(e.target);
            }
        });
        
        // Handle refresh buttons
        document.addEventListener('click', function(e) {
            if (e.target.classList.contains('refresh-btn')) {
                App.refreshData(e.target);
            }
        });
    },
    
    // Initialize components
    initializeComponents: function() {
        // Initialize tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
        
        // Initialize popovers
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function(popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
        
        // Add fade-in animation to cards
        const cards = document.querySelectorAll('.card');
        cards.forEach((card, index) => {
            setTimeout(() => {
                card.classList.add('fade-in');
            }, index * 100);
        });
    },
    
    // Start session monitoring
    startSessionMonitoring: function() {
        // Only monitor if user is authenticated
        if (document.body.dataset.authenticated === 'true') {
            setInterval(() => {
                this.checkSessionStatus();
            }, this.config.sessionCheckInterval);
        }
    },
    
    // Check session status
    checkSessionStatus: function() {
        fetch('/api/session/status', {
            method: 'GET',
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            if (!data.authenticated) {
                this.handleSessionExpired();
            } else if (data.time_remaining < 300) { // Less than 5 minutes
                this.showSessionWarning(data.time_remaining);
            }
        })
        .catch(error => {
            console.error('Session check failed:', error);
        });
    },
    
    // Handle session expiration
    handleSessionExpired: function() {
        this.showAlert('Your session has expired. You will be redirected to login.', 'warning', true);
        setTimeout(() => {
            window.location.href = '/auth/login';
        }, 3000);
    },
    
    // Show session warning
    showSessionWarning: function(timeRemaining) {
        const minutes = Math.floor(timeRemaining / 60);
        const message = `Your session will expire in ${minutes} minute(s). Click to extend.`;
        
        const alertElement = this.showAlert(message, 'warning', false, true);
        alertElement.style.cursor = 'pointer';
        alertElement.addEventListener('click', () => {
            this.extendSession();
        });
    },
    
    // Extend session
    extendSession: function() {
        fetch('/api/session/extend', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showAlert('Session extended successfully!', 'success');
            } else {
                this.showAlert('Failed to extend session.', 'danger');
            }
        })
        .catch(error => {
            this.showAlert('Error extending session.', 'danger');
        });
    },
    
    // Show alert message
    showAlert: function(message, type = 'info', permanent = false, clickable = false) {
        const alertContainer = document.querySelector('.container');
        const alertId = 'alert-' + Date.now();
        
        const alertHTML = `
            <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show ${permanent ? 'alert-permanent' : ''}" role="alert">
                <i class="fas fa-${this.getAlertIcon(type)} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        alertContainer.insertAdjacentHTML('afterbegin', alertHTML);
        const alertElement = document.getElementById(alertId);
        
        // Auto-hide non-permanent alerts
        if (!permanent) {
            setTimeout(() => {
                this.hideAlert(alertElement);
            }, this.config.alertAutoHideDelay);
        }
        
        return alertElement;
    },
    
    // Get alert icon based on type
    getAlertIcon: function(type) {
        const icons = {
            'success': 'check-circle',
            'info': 'info-circle',
            'warning': 'exclamation-triangle',
            'danger': 'exclamation-circle'
        };
        return icons[type] || 'info-circle';
    },
    
    // Hide alert with animation
    hideAlert: function(alertElement) {
        if (alertElement && alertElement.parentNode) {
            alertElement.style.opacity = '0';
            alertElement.style.transform = 'translateY(-20px)';
            setTimeout(() => {
                alertElement.remove();
            }, this.config.animationDuration);
        }
    },
    
    // Validate form
    validateForm: function(form, event) {
        if (!form.checkValidity()) {
            event.preventDefault();
            event.stopPropagation();
            this.showAlert('Please fill in all required fields correctly.', 'warning');
        }
        form.classList.add('was-validated');
    },
    
    // Copy text to clipboard
    copyToClipboard: function(button) {
        const targetId = button.dataset.target;
        const targetElement = document.getElementById(targetId);
        
        if (targetElement) {
            const text = targetElement.textContent || targetElement.value;
            
            navigator.clipboard.writeText(text).then(() => {
                const originalText = button.textContent;
                button.textContent = 'Copied!';
                button.classList.add('btn-success');
                
                setTimeout(() => {
                    button.textContent = originalText;
                    button.classList.remove('btn-success');
                }, 2000);
            }).catch(err => {
                this.showAlert('Failed to copy to clipboard.', 'danger');
            });
        }
    },
    
    // Refresh data
    refreshData: function(button) {
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Refreshing...';
        button.disabled = true;
        
        // Simulate refresh (replace with actual refresh logic)
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    },
    
    // Format timestamp
    formatTimestamp: function(timestamp) {
        const date = new Date(timestamp * 1000);
        return date.toLocaleString();
    },
    
    // Format duration
    formatDuration: function(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        
        if (hours > 0) {
            return `${hours}h ${minutes}m ${secs}s`;
        } else if (minutes > 0) {
            return `${minutes}m ${secs}s`;
        } else {
            return `${secs}s`;
        }
    },
    
    // Animate counter
    animateCounter: function(element, start, end, duration = 1000) {
        const range = end - start;
        const increment = range / (duration / 16);
        let current = start;
        
        const timer = setInterval(() => {
            current += increment;
            element.textContent = Math.floor(current);
            
            if (current >= end) {
                element.textContent = end;
                clearInterval(timer);
            }
        }, 16);
    },
    
    // Show loading spinner
    showLoading: function(element) {
        const spinner = document.createElement('div');
        spinner.className = 'text-center p-4';
        spinner.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div>';
        element.appendChild(spinner);
        return spinner;
    },
    
    // Hide loading spinner
    hideLoading: function(spinner) {
        if (spinner && spinner.parentNode) {
            spinner.remove();
        }
    },
    
    // Debounce function
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // Throttle function
    throttle: function(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
};

// Utility functions
const Utils = {
    // Check if element is in viewport
    isInViewport: function(element) {
        const rect = element.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    },
    
    // Smooth scroll to element
    scrollToElement: function(element, offset = 0) {
        const elementPosition = element.getBoundingClientRect().top;
        const offsetPosition = elementPosition + window.pageYOffset - offset;
        
        window.scrollTo({
            top: offsetPosition,
            behavior: 'smooth'
        });
    },
    
    // Generate random ID
    generateId: function(prefix = 'id') {
        return prefix + '-' + Math.random().toString(36).substr(2, 9);
    },
    
    // Format file size
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    App.init();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'visible') {
        // Page became visible, check session status
        if (document.body.dataset.authenticated === 'true') {
            App.checkSessionStatus();
        }
    }
});

// Handle online/offline status
window.addEventListener('online', function() {
    App.showAlert('Connection restored.', 'success');
});

window.addEventListener('offline', function() {
    App.showAlert('Connection lost. Some features may not work.', 'warning', true);
});

// Export for global access
window.App = App;
window.Utils = Utils;