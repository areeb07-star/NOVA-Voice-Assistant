/* ============================================================
   NOVA - Theme Toggle
   Loads saved theme, applies it, wires up toggle buttons.
   ============================================================ */

(function () {
  'use strict';

  const STORAGE_KEY = 'nova-theme';

  // ---------- Apply theme immediately (no flicker) ----------
  function getSavedTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY) || 'dark';
    } catch (e) {
      return 'dark';
    }
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {}

    // Update icon in any existing toggle buttons
    document.querySelectorAll('.theme-toggle-btn').forEach(function (btn) {
      updateToggleIcon(btn, theme);
    });

    // Update profile page theme display if present
    const themeLabel = document.getElementById('profileThemeLabel');
    if (themeLabel) {
      themeLabel.textContent = theme === 'light' ? 'Light' : 'Dark';
    }
  }

  function updateToggleIcon(btn, theme) {
    // Simple text swap - works without needing lucide
    btn.innerHTML = theme === 'light'
      ? '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>'
      : '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"></circle><path d="M12 2v2"></path><path d="M12 20v2"></path><path d="m4.93 4.93 1.41 1.41"></path><path d="m17.66 17.66 1.41 1.41"></path><path d="M2 12h2"></path><path d="M20 12h2"></path><path d="m6.34 17.66-1.41 1.41"></path><path d="m19.07 4.93-1.41 1.41"></path></svg>';
    btn.title = theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode';
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'light' ? 'dark' : 'light';
    applyTheme(next);
  }

  // ---------- Apply on page load (before paint) ----------
  applyTheme(getSavedTheme());

  // ---------- Wire up buttons after DOM ready ----------
  document.addEventListener('DOMContentLoaded', function () {
    // Reapply (in case attribute got lost)
    applyTheme(getSavedTheme());

    document.querySelectorAll('.theme-toggle-btn').forEach(function (btn) {
      if (btn.dataset.themeWired) return;
      btn.dataset.themeWired = 'true';
      updateToggleIcon(btn, document.documentElement.getAttribute('data-theme') || 'dark');
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        toggleTheme();
      });
    });
  });

  // ---------- Expose for other scripts ----------
  window.NOVA_THEME = {
    get: getSavedTheme,
    set: applyTheme,
    toggle: toggleTheme
  };
})();