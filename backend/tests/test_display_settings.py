"""Settings > Display (language and light/dark theme) and the generated dark-theme CSS."""

from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


def load_builder():
    spec = importlib.util.spec_from_file_location("build_dark_theme", ROOT / "tools" / "build_dark_theme.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DisplaySettingsTests(unittest.TestCase):
    def test_language_and_theme_live_in_settings_not_the_header(self):
        common = (FRONTEND / "app_common.js").read_text(encoding="utf-8")
        self.assertNotIn("account-language-switch", common)
        self.assertIn('data-language-option="ms"', common)
        self.assertIn('data-theme-option="dark"', common)
        # The saved theme is applied while the script loads in <head>, before the page paints.
        head = common.split("function getRequestUrl", 1)[0]
        self.assertIn('const THEME_KEY = "careerNavigatorTheme";', head)
        self.assertIn("document.documentElement.dataset.theme = theme;", head)
        for label in ("Display", "Language", "Appearance", "Light", "Dark", "Your preferences", "Preferences and security"):
            with self.subTest(label=label):
                self.assertIn(f'"{label}": ', common)

    def test_every_page_loads_the_common_script_before_its_styles(self):
        for page in ("home_page.html", "analysis_result.html", "job_data_insights.html"):
            with self.subTest(page=page):
                html = (FRONTEND / page).read_text(encoding="utf-8")
                self.assertLess(html.index('<script src="app_common.js"></script>'), html.index("<style>"))
                self.assertIn('<style id="darkThemeGenerated">', html)
                self.assertIn('<style id="darkThemeTweaks">', html)


class DarkThemeBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = load_builder()

    def test_generated_blocks_match_the_light_styles(self):
        """Fails when colours change without running python tools/build_dark_theme.py."""
        builder = self.builder
        for page in builder.PAGES:
            with self.subTest(page=page):
                html = (FRONTEND / page).read_text(encoding="utf-8")
                light = re.search(r"<style>(.*?)</style>", html, re.S).group(1)
                self.assertIn(f'<style id="{builder.PAGE_STYLE_ID}">\n{builder.dark_css(light)}\n</style>', html)
        shared = builder.SHARED_CSS.read_text(encoding="utf-8")
        expected = builder.dark_css(builder.TAILWIND.read_text(encoding="utf-8"), builder.remove_generated_css(shared))
        self.assertIn(builder.CSS_START + "\n" + expected + "\n" + builder.CSS_END, shared)

    def test_light_surfaces_turn_dark_and_dark_text_turns_light(self):
        builder = self.builder

        def lightness(hex_color):
            return builder.to_oklab(*(int(hex_color[i:i + 2], 16) for i in (1, 3, 5)))[0]

        white_card = builder.map_value("#ffffff", "background")
        self.assertLess(lightness(white_card), 0.3)
        ink = builder.map_value("#17202e", "text")
        self.assertGreater(lightness(ink), 0.8)
        # Accent buttons and the already-dark footer keep their colours.
        self.assertEqual(builder.map_value("#0066cc", "background"), "#0066cc")
        self.assertEqual(builder.map_value("#122b3b", "background"), "#122b3b")
        # Faint overlays (mostly on the dark footer) are left alone.
        self.assertEqual(builder.map_value("rgba(255,255,255,.13)", "border"), "rgba(255,255,255,.13)")

    def test_twins_only_change_colours(self):
        builder = self.builder
        twins = builder.twin_declarations(builder.parse_declarations(
            'border: 1px solid #d7e5ef; border-radius: 20px; background: #fff url("data:image/png;base64,AAAA") no-repeat; color: var(--career-teal-deep)'
        ), keep_colours=False)
        self.assertEqual(twins[0].split(":")[0], "border-color")
        self.assertFalse(any(twin.startswith(("border-radius", "border:")) for twin in twins))
        self.assertIn('background-image:url("data:image/png;base64,AAAA")', twins)
        self.assertIn("color:var(--career-teal-deep-text, var(--career-teal-deep))", twins)

    def test_print_and_resume_paper_keep_light_colours(self):
        builder = self.builder
        css = builder.dark_css(".career-draft-page { background: #fff; color: #17202e; } @media print { .x { color: #000; } }")
        self.assertTrue(css.startswith("@media screen{"))
        self.assertIn("background-color:#fff;color:#17202e", css)
        self.assertNotIn(" .x{", css)


if __name__ == "__main__":
    unittest.main()
