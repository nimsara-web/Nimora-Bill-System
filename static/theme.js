// ============================================
//   NIMORA - Theme Toggle
// ============================================

(function() {
    // Load saved theme
    const savedTheme = localStorage.getItem('nimora-theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);

    // Wait for DOM
    document.addEventListener('DOMContentLoaded', function() {
        updateToggleIcon(savedTheme);

        const toggle = document.getElementById('themeToggle');
        if (toggle) {
            toggle.addEventListener('click', function() {
                const current = document.documentElement.getAttribute('data-theme');
                const next = current === 'dark' ? 'light' : 'dark';
                document.documentElement.setAttribute('data-theme', next);
                localStorage.setItem('nimora-theme', next);
                updateToggleIcon(next);
            });
        }
    });

    function updateToggleIcon(theme) {
        const toggle = document.getElementById('themeToggle');
        if (!toggle) return;
        if (theme === 'dark') {
            toggle.innerHTML = '☀️ <span style="display:none">Light</span>';
            toggle.title = 'Switch to Light Mode';
        } else {
            toggle.innerHTML = '🌙 <span style="display:none">Dark</span>';
            toggle.title = 'Switch to Dark Mode';
        }
    }
})();