(function() {
    'use strict';
    
    // Get theme preference from localStorage or default to 'light'
    function getThemePreference() {
        const savedTheme = localStorage.getItem('theme');
        
        // If user has a saved preference, use it
        if (savedTheme) {
            return savedTheme;
        }
        
        // Otherwise, check system preference
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        
        // Default to light mode
        return 'light';
    }
    
    // Apply theme to the document
    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        
        // Update toggle button state
        updateToggleButton(theme);
    }
    
    // Update toggle button appearance
    function updateToggleButton(theme) {
        const toggleBtn = document.querySelector('.theme-toggle');
        if (toggleBtn) {
            toggleBtn.setAttribute('aria-label', 
                theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'
            );
        }
    }
    
    // Toggle between light and dark
    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        applyTheme(newTheme);
        
        // animation on hover
        document.body.style.transition = 'none';
        setTimeout(() => {
            document.body.style.transition = '';
        }, 10);
    }
    
    // Initialize theme on page load
    function initTheme() {
        const theme = getThemePreference();
        applyTheme(theme);
        
        // Add click listener to toggle button
        const toggleBtn = document.querySelector('.theme-toggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', toggleTheme);
        }
        
        // Listen for system theme changes
        if (window.matchMedia) {
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
                // Only auto-switch if user hasn't manually set a preference
                if (!localStorage.getItem('theme')) {
                    applyTheme(e.matches ? 'dark' : 'light');
                }
            });
        }
    }
    
    // Run on DOMContentLoaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTheme);
    } else {
        initTheme();
    }
    
    // Expose toggle function globally (optional, for debugging)
    window.toggleTheme = toggleTheme;
})();