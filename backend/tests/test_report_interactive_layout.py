"""The report page shows short, tappable summaries instead of long paragraphs.

These checks read the page source: the hero score opens its parts, the next
edits and ATS issues fold, every ATS check category has an icon, and the
issue advice follows the check's category.
"""
import re
import unittest
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parents[2]
PAGE = (WEB_DIR / "frontend" / "analysis_result.html").read_text(encoding="utf-8")
COMMON = (WEB_DIR / "frontend" / "app_common.js").read_text(encoding="utf-8")
BACKEND = (WEB_DIR / "backend" / "app.py").read_text(encoding="utf-8")


def function_source(name: str) -> str:
    start = PAGE.index("function " + name + "(")
    return PAGE[start:PAGE.index("\n    }\n", start)]


class HeroScoreTests(unittest.TestCase):
    def test_hero_drops_the_matched_evidence_line(self):
        self.assertNotIn("reportSummaryEvidence", PAGE)
        self.assertNotIn("Review the matched evidence", PAGE)

    def test_score_is_a_button_that_opens_its_parts(self):
        self.assertIn('id="reportScoreButton" type="button" aria-expanded="false" aria-controls="reportScoreParts"', PAGE)
        self.assertIn('id="reportScoreParts" hidden', PAGE)
        self.assertIn("not a hiring probability", PAGE)
        parts = function_source("renderHeroScoreParts")
        for label in ("Requirements", "Role evidence", "ATS format", "Experience"):
            self.assertIn(f'["{label}",', PAGE)
        self.assertIn('data-weakest="true"', parts)

    def test_score_counts_up_and_respects_reduced_motion(self):
        counter = function_source("animateScoreNumber")
        self.assertIn("requestAnimationFrame(step)", counter)
        self.assertIn("prefers-reduced-motion: reduce", counter)


class FoldingSectionsTests(unittest.TestCase):
    def test_next_edits_start_minimized_on_phones(self):
        self.assertIn(
            'data-collapse-toggle="quick" data-collapse-mode="items" data-collapse-default="phone" aria-controls="quickActionList"',
            PAGE,
        )
        quick = function_source("renderQuickActions")
        self.assertIn('class="quick-edit-details report-collapse-item"', quick)
        self.assertIn('isCollapseTargetOpen("quickActionList")', quick)

    def test_overview_has_no_keyword_chip_block_and_tappable_rings(self):
        self.assertNotIn("matchedSignalsChipList", PAGE)
        self.assertEqual(PAGE.count("data-evidence-tile="), 3)
        self.assertIn('id="evidenceTileDetail"', PAGE)

    def test_summary_card_lists_points_and_folds_the_method(self):
        for element_id in ("scoreMeaningLabel", "aiSummary", "scoreMeaningShort", "aiRecommendation", "scoreWeightList"):
            self.assertIn(f'id="{element_id}"', PAGE)
        self.assertIn('<details class="report-summary-more report-collapse-item">', PAGE)

    def test_strategy_card_does_not_repeat_the_role(self):
        self.assertNotIn("resumeStrategyRole", PAGE)
        self.assertNotIn("resumeStrategySummary", PAGE)
        self.assertIn("Keywords for your next draft", PAGE)

    def test_ats_method_sits_behind_an_info_fold(self):
        self.assertRegex(PAGE, r'<details class="ats-how[^"]*">\s*<summary>.*How this affects your score')
        self.assertIn('<p id="atsQualitySummaryText">', PAGE)
        self.assertIn("renderAtsMeter(resumeQuality, atsReadinessCopy.qualityScore);", PAGE)


class AtsIssueTests(unittest.TestCase):
    def test_every_backend_check_category_has_an_icon(self):
        quality = BACKEND[BACKEND.index("def analyze_resume_quality("):]
        quality = quality[:quality.index("\ndef ", 10)]
        categories = set(re.findall(r'add\(\s*"([A-Za-z]+)",', quality))
        self.assertGreaterEqual(len(categories), 10)
        icon_block = PAGE[PAGE.index("const ATS_CATEGORY_ICON_PATHS = {"):PAGE.index("const ATS_DEFAULT_ICON_PATH")]
        for category in sorted(categories):
            with self.subTest(category=category):
                self.assertIn(f"{category.lower()}: '", icon_block)
                self.assertIn(f'"{category}": ', COMMON)  # Malay label for the category

    def test_issues_fold_open_for_their_fix(self):
        renderer = function_source("renderAtsQualityCriteria")
        self.assertIn('<details class="ats-issue-details report-collapse-item">', renderer)
        self.assertIn("getAtsCategoryIcon(item.category)", renderer)

    def test_issue_advice_follows_the_category(self):
        topic = function_source("getIssueTopic")
        # Category first, so "Word, Google Docs" or "translate key skills" no longer
        # turn a scanned-PDF or language issue into length or skills advice.
        self.assertLess(topic.index("item.category"), topic.index("getIssueSearchText(item)"))
        self.assertIn('if (category === "length") return /too short/', topic)
        self.assertIn('if (category === "skills") return "skills";', topic)


class TranslationTests(unittest.TestCase):
    def test_new_report_labels_have_malay_translations(self):
        for label in (
            "See what makes up this score",
            "Hide score parts",
            "Lowest",
            "Evidence match and ATS feedback, not a hiring probability.",
            "Usable, but not fully optimized for this role yet.",
            "How the score is worked out",
            "How this affects your score",
            "Low risk",
            "Keywords for your next draft",
            "Counted as met. Write the skill words too, because ATS filters match exact words.",
        ):
            with self.subTest(label=label):
                self.assertIn(f'"{label}": ', COMMON)
        for pattern in ("[/^Next: add evidence for (.+)", "[/^Compared with (.+)\\. Start with the suggested edits below"):
            self.assertIn(pattern, COMMON)


if __name__ == "__main__":
    unittest.main()
