// Authentication Guard - Protects dashboard and protected routes
class AuthGuard {
    
    /**
     * Check if user is authenticated
     * @returns {boolean} True if authenticated, false otherwise
     */
    static isAuthenticated() {
        const userId = localStorage.getItem('sahatak_user_id');
        const userType = localStorage.getItem('sahatak_user_type');
        const userEmail = localStorage.getItem('sahatak_user_email');
        
        return userId && userType && (userEmail || userType); // Email optional for phone-only users
    }
    
    /**
     * Get current user data from localStorage
     * @returns {object|null} User data or null if not authenticated
     */
    static getCurrentUser() {
        if (!this.isAuthenticated()) {
            return null;
        }
        
        return {
            id: localStorage.getItem('sahatak_user_id'),
            userType: localStorage.getItem('sahatak_user_type'),
            email: localStorage.getItem('sahatak_user_email'),
            fullName: localStorage.getItem('sahatak_user_name')
        };
    }
    
    /**
     * Check if current user has specific user type
     * @param {string} requiredType - 'patient' or 'doctor'
     * @returns {boolean} True if user has required type
     */
    static hasUserType(requiredType) {
        const userType = localStorage.getItem('sahatak_user_type');
        return userType === requiredType;
    }
    
    /**
     * Redirect to login page with return URL
     * @param {string} returnUrl - URL to return to after login (optional)
     */
    static redirectToLogin(returnUrl = null) {
        // Store return URL for after login
        const currentHref = window.location.href;
        if (!currentHref.includes('index.html') && !currentHref.endsWith('/')) {
            localStorage.setItem('sahatak_return_url', currentHref);
        }
        
        // For GitHub Pages, use absolute path to root
        if (window.location.hostname.includes('github.io')) {
            // On GitHub Pages - use absolute path from repository root
            const repoPath = '/Sahatak/'; // Your repository name
            window.location.href = repoPath;
        } else {
            // Local development or other hosting - use relative paths
            let loginUrl;
            if (window.location.pathname.includes('/pages/dashboard/')) {
                loginUrl = '../../index.html';
            } else if (window.location.pathname.includes('/pages/')) {
                loginUrl = '../index.html';
            } else {
                loginUrl = 'index.html';
            }
            window.location.href = loginUrl;
        }
    }
    
    /**
     * Protect a page - redirect to login if not authenticated
     * @param {string} requiredUserType - 'patient', 'doctor', or null for any authenticated user
     */
    static protectPage(requiredUserType = null) {
        // Check if user is authenticated
        if (!this.isAuthenticated()) {
            console.warn('User not authenticated, redirecting to login');
            this.redirectToLogin();
            return false;
        }
        
        // Check user type if specified
        if (requiredUserType && !this.hasUserType(requiredUserType)) {
            console.warn(`User type mismatch. Required: ${requiredUserType}, Current: ${localStorage.getItem('sahatak_user_type')}`);
            
            // Redirect to correct dashboard based on actual user type
            const actualUserType = localStorage.getItem('sahatak_user_type');
            if (actualUserType === 'patient') {
                if (window.location.pathname.includes('/pages/dashboard/')) {
                    window.location.href = 'patient.html';
                } else {
                    window.location.href = 'frontend/pages/dashboard/patient.html';
                }
            } else if (actualUserType === 'doctor') {
                if (window.location.pathname.includes('/pages/dashboard/')) {
                    window.location.href = 'doctor.html';
                } else {
                    window.location.href = 'frontend/pages/dashboard/doctor.html';
                }
            } else {
                this.redirectToLogin();
            }
            return false;
        }
        
        return true;
    }
    
    /**
     * Verify authentication with backend (optional - for enhanced security)
     * @returns {Promise<boolean>} True if session is valid
     */
    static async verifySession() {
        try {
            // This would require implementing a /api/auth/verify endpoint
            const response = await fetch('/api/auth/me', {
                method: 'GET',
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                return data.success;
            }
            
            return false;
        } catch (error) {
            console.error('Session verification failed:', error);
            return false;
        }
    }
    
    /**
     * Clear authentication data (logout)
     */
    static clearAuth() {
        localStorage.removeItem('sahatak_user_id');
        localStorage.removeItem('sahatak_user_type');
        localStorage.removeItem('sahatak_user_email');
        localStorage.removeItem('sahatak_user_name');
        localStorage.removeItem('sahatak_return_url');
    }
    
    /**
     * Complete logout - clear local data and call backend
     * @returns {Promise<boolean>} True if logout successful
     */
    static async logout() {
        try {
            // Call backend logout endpoint to invalidate session
            const baseUrl = 'https://sahatak.pythonanywhere.com/api';
            const response = await fetch(`${baseUrl}/auth/logout`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            console.log('Backend logout successful:', response.ok);
        } catch (error) {
            console.error('Backend logout error:', error);
            // Continue with frontend cleanup even if backend fails
        }
        
        // Clear all local authentication data
        this.clearAuth();
        
        // Redirect to login page
        this.redirectToLogin();
        
        return true;
    }
    
    /**
     * Create logout button element
     * @param {string} className - CSS classes for the button
     * @param {string} text - Button text (optional)
     * @returns {HTMLElement} Logout button element
     */
    static createLogoutButton(className = 'btn btn-outline-danger', text = null) {
        const lang = localStorage.getItem('sahatak_language') || 'ar';
        const defaultText = lang === 'ar' ? 'تسجيل خروج' : 'Logout';
        
        const button = document.createElement('button');
        button.className = className;
        button.innerHTML = `<i class="bi bi-box-arrow-right me-1"></i> ${text || defaultText}`;
        button.onclick = () => this.logout();
        
        return button;
    }
}

// Auto-protect pages that include this script with data-protect attribute
document.addEventListener('DOMContentLoaded', function() {
    const body = document.body;
    const protectType = body.getAttribute('data-protect');
    
    if (protectType !== null) {
        // Page requires protection
        const requiredUserType = protectType === '' ? null : protectType;
        AuthGuard.protectPage(requiredUserType);
    }
});

// Export for use in other scripts
window.AuthGuard = AuthGuard;