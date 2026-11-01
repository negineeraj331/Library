"""
Verification suite for Light/Dark Mode toggle integration
"""
import unittest
import re

class TestDarkModeIntegration(unittest.TestCase):
    def test_style_css_tokens(self):
        with open("static/style.css", "r", encoding="utf-8") as f:
            css = f.read()
        self.assertIn("color-scheme: light dark", css)
        self.assertIn(':root[data-theme="dark"]', css)
        self.assertIn("--bg-main: #0b1320", css)
        self.assertIn("--card-bg: #131f33", css)
        self.assertIn("--btn-primary-bg: #0284c7", css)
        self.assertIn(".theme-toggle-btn", css)
        self.assertIn(".sidebar-theme-btn", css)
        self.assertIn(".badge-navy", css)
        self.assertIn(".badge-issued", css)
        self.assertIn(".alert-success", css)
        self.assertIn(".alert-error", css)

    def test_script_js_theme_logic(self):
        with open("static/script.js", "r", encoding="utf-8") as f:
            js = f.read()
        self.assertIn("getPreferredTheme", js)
        self.assertIn("applyTheme", js)
        self.assertIn("toggleTheme", js)
        self.assertIn("localStorage.getItem('theme')", js)
        self.assertIn("prefers-color-scheme: dark", js)
        self.assertIn("window.addEventListener('storage'", js)

    def test_templates_fouc_and_buttons(self):
        templates_to_check = [
            "templates/base.html",
            "templates/student_base.html",
            "templates/login.html",
            "templates/student_login.html",
            "templates/student_register.html"
        ]
        for path in templates_to_check:
            with open(path, "r", encoding="utf-8") as f:
                html = f.read()
            self.assertIn('meta name="color-scheme" content="light dark"', html, f"Missing color-scheme meta in {path}")
            self.assertIn('document.documentElement.setAttribute(\'data-theme\', theme)', html, f"Missing anti-FOUC script in {path}")
            self.assertTrue(
                "theme-toggle-btn" in html or "sidebar-theme-btn" in html,
                f"Missing theme toggle button in {path}"
            )

if __name__ == "__main__":
    unittest.main()

