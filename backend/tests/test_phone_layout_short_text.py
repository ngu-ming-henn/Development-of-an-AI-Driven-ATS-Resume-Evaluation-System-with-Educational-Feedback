"""Phone home layout and shorter report text.

Phones (max-width 700px) get their own home hero: the title first, the three
checks as an animated column as tall as the quick tour beside it, and the
buttons across the full width under both. The repeated sample-report links,
the sign-in note and long explanations are hidden on phones only, so tablets
and computers keep them. The quick tour moves every 4 seconds and the home
page always opens at the top. On the report page (every screen size) lines
that only repeat a heading, a badge or a list are gone, while review warnings
stay.

These checks read the page source.
"""
import unittest
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parents[2]
HOME = (WEB_DIR / "frontend" / "home_page.html").read_text(encoding="utf-8")
REPORT = (WEB_DIR / "frontend" / "analysis_result.html").read_text(encoding="utf-8")
COMMON = (WEB_DIR / "frontend" / "app_common.js").read_text(encoding="utf-8")
HOME_LIGHT_CSS = HOME[HOME.index("<style>"):HOME.index("</style>")]


def media_blocks(css: str, query: str) -> list[str]:
    """Bodies of the @media blocks written as '@media <query> {'."""
    marker = "@media " + query + " {"
    blocks = []
    start = css.find(marker)
    while start >= 0:
        depth = 0
        for position in range(start + len(marker) - 1, len(css)):
            if css[position] == "{":
                depth += 1
            elif css[position] == "}":
                depth -= 1
                if depth == 0:
                    blocks.append(css[start + len(marker):position])
                    break
        start = css.find(marker, start + len(marker))
    return blocks


PHONE_CSS = "\n".join(media_blocks(HOME_LIGHT_CSS, "(max-width: 700px)"))
NARROW_CSS = "\n".join(media_blocks(HOME_LIGHT_CSS, "(max-width: 480px)"))


class PhoneHeroTests(unittest.TestCase):
    def test_checks_sit_beside_the_tour_and_buttons_under_both(self):
        self.assertIn(
            'grid-template-areas: "eyebrow eyebrow" "title title" "lead lead" "proof tour" "actions actions" "hint hint"',
            PHONE_CSS,
        )
        self.assertIn(".career-hero-content { display: contents; }", PHONE_CSS)
        self.assertIn(".career-hero-content > .career-hero-actions { grid-area: actions;", PHONE_CSS)
        self.assertIn(".career-hero-grid > .career-tour { grid-area: tour;", PHONE_CSS)
        # The column grows to its longest word, so the Malay labels fit.
        self.assertIn("grid-template-columns: minmax(66px, min-content) minmax(0, 1fr)", PHONE_CSS)

    def test_sign_in_note_shows_on_phones_only_for_errors(self):
        self.assertIn(".career-hero-content > .career-upload-hint:not(.text-error) { display: none; }", PHONE_CSS)
        self.assertIn('uploadHint.className = isError ? "career-upload-hint text-error" : "career-upload-hint";', HOME)

    def test_phones_show_short_labels_and_keep_the_full_ones_for_screen_readers(self):
        for full, short, malay in (
            ("Role-based matching", "Role match", "Padanan peranan"),
            ("ATS format feedback", "ATS format", "Format ATS"),
            ("Practical improvement tips", "Practical tips", "Tip praktikal"),
        ):
            with self.subTest(short=short):
                self.assertIn(
                    f'<span class="career-proof-label">{full}</span><span class="career-proof-short" aria-hidden="true">{short}</span>',
                    HOME,
                )
                self.assertIn(f'"{short}": "{malay}"', COMMON)
        self.assertIn(".career-proof-short { display: none; }", HOME_LIGHT_CSS)
        self.assertIn(".career-proof-short { display: block; }", PHONE_CSS)
        self.assertIn(".career-proof-label { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%);", PHONE_CSS)

    def test_check_column_is_animated_except_for_reduced_motion(self):
        self.assertIn("@keyframes careerRailTick", HOME_LIGHT_CSS)
        self.assertIn("@keyframes careerRailRun", HOME_LIGHT_CSS)
        self.assertIn("animation: careerRailRun 4.8s ease-in-out infinite;", PHONE_CSS)
        self.assertIn("animation: careerRailTick 4.8s ease-out infinite;", PHONE_CSS)
        self.assertIn(".career-proof-list li:nth-child(3) .career-proof-check::after { animation-delay: 3.2s; }", PHONE_CSS)
        reduced = "\n".join(media_blocks(HOME_LIGHT_CSS, "(prefers-reduced-motion: reduce)"))
        self.assertIn(".career-proof-check::after, .career-proof-list li::after { animation: none !important; }", reduced)

    def test_tour_button_and_sample_line_are_not_repeated_on_phones(self):
        self.assertIn(".career-tour-cta, .career-visual-disclaimer { display: none; }", PHONE_CSS)
        # Tablets and computers still have both.
        self.assertIn("data-tour-start>Check my resume", HOME)
        self.assertIn('class="career-visual-disclaimer"', HOME)

    def test_narrow_phones_fit_the_tour_controls(self):
        self.assertIn(".career-tour-nav { width: 38px; min-width: 38px; padding: 0; font-size: 0; }", NARROW_CSS)
        # Play/Pause is a round icon there; its words stay for screen readers.
        self.assertIn(".career-tour-play [data-tour-play-label] { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%);", NARROW_CSS)
        self.assertIn('id="careerTourBack" type="button" aria-label="Previous step"', HOME)
        self.assertIn('id="careerTourNext" type="button" aria-label="Next step"', HOME)
        very_narrow = "\n".join(media_blocks(HOME_LIGHT_CSS, "(max-width: 359px)"))
        self.assertIn('grid-template-areas: "eyebrow" "title" "lead" "proof" "tour" "actions" "hint"', very_narrow)


class PhoneShortTextTests(unittest.TestCase):
    def test_repeated_links_and_long_text_hide_on_phones_only(self):
        for selector in (
            ".career-flow-intro > p:not(.career-eyebrow)",
            ".career-flow-row .career-feature-link",
            ".career-flow-section.is-minimized .career-flow-row.is-open .career-feature-link",
            ".career-sample-copy > p:not(.career-eyebrow)",
            ".career-sample-copy .career-text-link",
            ".career-draft-points p",
            ".career-draft-actions { display: none; }",
        ):
            self.assertIn(selector, PHONE_CSS)
        # The markup keeps them for tablets and computers.
        self.assertEqual(HOME.count(">Explore the sample report <"), 3)
        self.assertIn(">Open the full sample report <", HOME)
        self.assertIn(">See where the draft appears <", HOME)
        self.assertIn("Scores describe evidence in the resume.", HOME)

    def test_draft_points_become_three_tiles_on_phones(self):
        self.assertIn(".career-draft-points { grid-template-columns: repeat(3, minmax(0, 1fr));", PHONE_CSS)
        self.assertEqual(HOME.count('<span class="career-draft-mark" aria-hidden="true">'), 3)


class TourAndStartTests(unittest.TestCase):
    def test_tour_moves_every_four_seconds(self):
        self.assertIn("const STEP_MS = 4000;", HOME)
        self.assertIn("var(--career-tour-interval, 4000ms)", HOME)
        self.assertNotIn("STEP_MS = 6000", HOME)

    def test_home_opens_at_the_top(self):
        script_at = HOME.index('history.scrollRestoration = "manual"')
        self.assertLess(script_at, HOME.index("</head>"))
        start = HOME[script_at - 600:HOME.index("})();", script_at)]
        self.assertIn('navigation.type === "reload" || navigation.type === "back_forward"', start)
        self.assertIn("history.replaceState(history.state, \"\", location.pathname + location.search);", start)
        self.assertIn("window.scrollTo(0, 0);", start)


class ReportShortTextTests(unittest.TestCase):
    def test_lines_that_repeat_the_report_are_gone(self):
        for sentence in (
            "Check the file used for this analysis",
            "Preview the complete report here, or save a PDF",
            "Selected role confirmed as the database match. The Top 3 list",
            "You selected this role. The Top 3 list below",
            "Generate an ATS resume draft for",
            "The original PDF or image is unavailable",
            "recommendationPlanSummary",
        ):
            self.assertNotIn(sentence, REPORT)

    def test_empty_optional_lines_are_hidden(self):
        self.assertIn("function setOptionalText(id, value)", REPORT)
        self.assertIn("element.hidden = !value;", REPORT)
        self.assertIn('setOptionalText("selectedRoleScoreDisplay", "");', REPORT)
        self.assertIn('setOptionalText(\n            "futureAtsResumeText",', REPORT)

    def test_review_warnings_and_role_switch_reason_stay(self):
        self.assertIn("Treat this result as NOT MATCH.", REPORT)
        self.assertIn("Selected role requires review and is recorded as NOT MATCH.", REPORT)
        self.assertIn("the builder will show a clearly labelled fictional example", REPORT)
        self.assertIn("roleIsDifferent\n                    ? (roleReason ||", REPORT)


if __name__ == "__main__":
    unittest.main()
