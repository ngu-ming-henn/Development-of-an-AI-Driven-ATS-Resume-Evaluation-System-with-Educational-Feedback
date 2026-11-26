"""Home page "Write with evidence" card. It must only show what the system really
does: the measurable-impact check flags the vague bullet, the advice is the
improvement plan's pattern, and the rewrite follows that pattern part by part.
The real backend checks run on the card's own sentences, so the example cannot
drift away from the system."""
import html
import importlib
import os
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

with patch.dict(
    os.environ,
    {
        "APP_ENV": "testing",
        "FLASK_SECRET_KEY": "home-writing-card-tests-only-secret-key-value-1234567890",
        "ACCURACY_TESTING_AUTO_EXPORT": "0",
    },
    clear=False,
):
    app_module = importlib.import_module("app")

FRONTEND = BACKEND_DIR.parent / "frontend"
HOME = (FRONTEND / "home_page.html").read_text(encoding="utf-8")
COMMON = (FRONTEND / "app_common.js").read_text(encoding="utf-8")
BACKEND = (BACKEND_DIR / "app.py").read_text(encoding="utf-8")
CARD = HOME[HOME.index('<figure class="career-writing-card">'):HOME.index("</figure>")]


def quote_text(section_class: str) -> str:
    section = CARD[CARD.index(f'<div class="{section_class}">'):]
    quote = re.search(r'<p class="career-writing-quote">(.*?)</p>', section, re.S).group(1)
    return html.unescape(re.sub(r"<[^>]+>", "", quote)).strip("“”")


class CardMatchesTheSystemTests(unittest.TestCase):
    def test_measurable_impact_check_agrees_with_the_card(self):
        self.assertFalse(app_module.has_measurable_impact(quote_text("career-writing-before")))
        self.assertTrue(app_module.has_measurable_impact(quote_text("career-writing-after")))

    def test_finding_and_advice_are_the_reports_own_words(self):
        title = re.search(r'<p class="career-writing-finding-title">(.*?)</p>', CARD).group(1)
        self.assertIn(f'"Impact",\n            "warning",\n            "{title}",', BACKEND)
        self.assertIn("action verb + tool/skill + task + measurable result", CARD)
        self.assertIn("using this pattern: action verb + tool/skill + task + measurable result.", BACKEND)

    def test_highlighted_tools_and_verb_are_ones_the_system_detects(self):
        rewrite = quote_text("career-writing-after")
        keywords = set(app_module.tokenize_canonical_keywords(rewrite))
        for tool in re.findall(r'<mark data-part="tool">(.*?)</mark>', CARD):
            with self.subTest(tool=tool):
                self.assertIn(tool.lower(), keywords)
        verb = re.search(r'<mark data-part="action">(.*?)</mark>', CARD).group(1)
        self.assertIn(f'"{verb.lower()}",', BACKEND)  # in the backend's action-verb lists
        result = re.search(r'<mark data-part="result">(.*?)</mark>', CARD).group(1)
        self.assertTrue(app_module.has_measurable_impact(result))


class CardLayoutTests(unittest.TestCase):
    def test_every_highlight_has_a_matching_legend_chip_in_pattern_order(self):
        marked = set(re.findall(r'<mark data-part="([a-z]+)"', CARD))
        chips = re.findall(r'<button type="button" data-part="([a-z]+)" aria-pressed="false">', CARD)
        self.assertEqual(chips, ["action", "tool", "task", "result"])
        self.assertEqual(marked, set(chips))

    def test_chips_light_up_their_words(self):
        self.assertIn("card.dataset.activePart = part;", HOME)
        for part in ("action", "tool", "task", "result"):
            self.assertIn(f'.career-writing-card[data-active-part="{part}"] mark[data-part="{part}"]', HOME)

    def test_bullets_type_out_without_moving_the_layout(self):
        typer = HOME[HOME.index('// "Write with evidence" card types itself out'):HOME.index('// "Write with evidence" card: a legend chip')]
        # Skipped for reduced motion; hidden letters keep their space (opacity, not display).
        self.assertIn("reduceMotion.matches) return;", typer)
        self.assertIn(".career-writing-card.is-typing .tw-char:not(.is-shown) { opacity: 0; }", HOME)
        # Tapping the card finishes it, and the plain text is put back at the end.
        self.assertIn('card.addEventListener("click", finish);', typer)
        self.assertIn("quote.innerHTML = originals[index];", typer)

    def test_labels_have_malay_translations(self):
        for label in (
            "Your report flags bullets without a measurable result and suggests one pattern. This fictional example follows it.",
            "Your report flags",
            "Limited measurable impact",
            "Pattern from your improvement plan: action verb + tool/skill + task + measurable result.",
            "After · your rewrite",
            "The pattern, part by part",
            "Action verb",
            "Tool / skill",
            "Task",
            "Measurable result",
        ):
            with self.subTest(label=label):
                self.assertIn(f'"{label}": ', COMMON)


if __name__ == "__main__":
    unittest.main()
