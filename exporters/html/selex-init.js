/**
 * SE-Lex HTML Page Initialization
 * 
 * This file initializes and configures the navbar and other JavaScript functionality
 * for SE-Lex HTML pages. It is loaded with "defer" so pages work even without JavaScript.
 */

(function() {
    'use strict';

    /**
     * Initialize the navbar with SE-Lex configuration
     */
    function initNavbar() {
        // Check if navbar library is loaded
        if (typeof SweNavbar === 'undefined') {
            return;
        }

        // Get beteckning from data attribute if available
        const bodyElement = document.body;
        const beteckning = bodyElement.getAttribute('data-beteckning');

        // Configure navbar
        if (beteckning) {
            SweNavbar.setHeader("SFS");
            SweNavbar.setHeaderChild(beteckning);
        } else {
            SweNavbar.setHeader("SFS");
        }
    }

    /**
     * Tab switching functionality for amendment pages
     */
    function showTab(tabName) {
        // Hide all tab contents
        const contents = document.querySelectorAll('.tab-content');
        contents.forEach(content => content.classList.remove('active'));

        // Remove active class from all buttons
        const buttons = document.querySelectorAll('.tab-button');
        buttons.forEach(button => button.classList.remove('active'));

        // Show selected tab content
        const selectedTab = document.getElementById(tabName);
        if (selectedTab) {
            selectedTab.classList.add('active');
        }

        // Mark button as active
        const activeButton = document.querySelector(`[data-tab="${tabName}"]`);
        if (activeButton) {
            activeButton.classList.add('active');
        }
    }

    /**
     * Initialize tab functionality if tabs are present
     */
    function initTabs() {
        const tabButtons = document.querySelectorAll('.tab-button[data-tab]');
        
        tabButtons.forEach(button => {
            button.addEventListener('click', function() {
                const tabName = this.getAttribute('data-tab');
                showTab(tabName);
            });
        });
    }

    /**
     * Main initialization function
     */
    function init() {
        // Initialize navbar
        initNavbar();
        
        // Initialize tabs if present
        initTabs();
    }

    // Run initialization when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        // DOM is already ready
        init();
    }

    // Expose showTab function globally for backwards compatibility
    window.showTab = showTab;
})();
