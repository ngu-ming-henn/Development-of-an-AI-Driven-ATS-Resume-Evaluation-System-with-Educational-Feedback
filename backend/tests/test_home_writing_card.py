"""Home page "Write with evidence": one before/after card whose stronger bullet is
coloured by what each part adds, with legend chips that light those words up."""
import re
import unittest
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
HOME = (FRONTEND / "home_page.html").read_text(encoding="utf-8")
COMMON = (FRONTEND / "app_common.js").read_text(encoding="utf-8")


class WritingCardTests(unittest.TestCase):
    def test_every_highlight_has_a_matching_legend_chip(self):
        card = HOME[HOME.index('<figure class="career-writing-card">'):HOME.index("</figure>")]
        marked = set(re.findall(r'<mark data-part="([a-z]+)"', card))
        chips = set(re.findall(r'<button type="button" data-part="([a-z]+)" aria-pressed="false">', card))
        self.assertEqual(marked, {"action", "tool", "scope", "purpose"})
        self.assertEqual(chips, marked)

    def test_chips_light_up_their_words(self):
        self.assertIn("card.dataset.activePart = part;", HOME)
        for part in ("action", "tool", "scope", "purpose"):
            self.assertIn(f'.career-writing-card[data-active-part="{part}"] mark[data-part="{part}"]', HOME)

    def test_labels_have_malay_translations(self):
        for label in ("No tool, number, or purpose.", "What makes it specific", "Action", "Tools", "Scope", "Purpose"):
            with self.subTest(label=label):
                self.assertIn(f'"{label}": ', COMMON)


if __name__ == "__main__":
    unittest.main()
