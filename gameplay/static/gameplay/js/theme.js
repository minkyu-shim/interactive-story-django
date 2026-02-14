(function () {
    var storageKey = 'nahb-theme';
    var root = document.documentElement;

    function readStoredTheme() {
        try {
            var value = localStorage.getItem(storageKey);
            if (value === 'light' || value === 'dark') {
                return value;
            }
        } catch (err) {}
        return null;
    }

    function writeStoredTheme(value) {
        try {
            localStorage.setItem(storageKey, value);
        } catch (err) {}
    }

    function getSystemTheme() {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return 'light';
    }

    function applyTheme(theme) {
        root.setAttribute('data-theme', theme);
    }

    function updateButton(button, theme) {
        button.textContent = theme === 'dark' ? 'Light mode' : 'Dark mode';
        button.setAttribute('aria-pressed', String(theme === 'dark'));
    }

    function currentTheme() {
        return root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
    }

    applyTheme(readStoredTheme() || getSystemTheme());

    document.addEventListener('DOMContentLoaded', function () {
        if (!document.body || document.querySelector('.theme-toggle')) {
            return;
        }

        var button = document.createElement('button');
        button.type = 'button';
        button.className = 'theme-toggle';
        button.setAttribute('aria-label', 'Toggle dark mode');
        updateButton(button, currentTheme());

        button.addEventListener('click', function () {
            var nextTheme = currentTheme() === 'dark' ? 'light' : 'dark';
            applyTheme(nextTheme);
            writeStoredTheme(nextTheme);
            updateButton(button, nextTheme);
        });

        document.body.appendChild(button);
    });

    if (window.matchMedia) {
        var query = window.matchMedia('(prefers-color-scheme: dark)');
        var onSystemThemeChange = function (event) {
            if (readStoredTheme()) {
                return;
            }
            applyTheme(event.matches ? 'dark' : 'light');
            var toggle = document.querySelector('.theme-toggle');
            if (toggle) {
                updateButton(toggle, currentTheme());
            }
        };

        if (typeof query.addEventListener === 'function') {
            query.addEventListener('change', onSystemThemeChange);
        } else if (typeof query.addListener === 'function') {
            query.addListener(onSystemThemeChange);
        }
    }
})();
