"""Site icon and the report blocks that replaced the card-in-card layout.

- Every page links the blue "U" icon (tab, old browsers, phone home screen) and
  the server returns the three files.
- The report shows each block in its own shape: a striped sample ribbon, a
  0-100 track and two plain lists for progress, numbered timelines for the next
  edits and the improvement plan, a ranked bar chart for the Top 3 roles and a
  one-line role route.

The page checks read the source; the icon check calls the Flask app.
"""
import importlib
import os
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
        "FLASK_SECRET_KEY": "report-shapes-icon-tests-only-secret-key-value-1234567890",
        "ACCURACY_TESTING_AUTO_EXPORT": "0",
    },
    clear=False,
):
    app_module = importlib.import_module("app")

FRONTEND = BACKEND_DIR.parent / "frontend"
REPORT = (FRONTEND / "analysis_result.html").read_text(encoding="utf-8")
COMMON = (FRONTEND / "app_common.js").read_text(encoding="utf-8")


def function_source(name: str) -> str:
    start = REPORT.index("function " + name + "(")
    return REPORT[start:REPORT.index("\n    }\n", start)]


class SiteIconTests(unittest.TestCase):
    def test_every_page_links_the_icons(self):
        for page in ("home_page.html", "analysis_result.html", "job_data_insights.html"):
            source = (FRONTEND / page).read_text(encoding="utf-8")
            with self.subTest(page=page):
                self.assertIn('<link rel="icon" href="favicon.ico" sizes="32x32">', source)
                self.assertIn('<link rel="icon" href="favicon.svg" type="image/svg+xml">', source)
                self.assertIn('<link rel="apple-touch-icon" href="apple-touch-icon.png">', source)

    def test_icon_is_the_brand_mark(self):
        icon = (FRONTEND / "favicon.svg").read_text(encoding="utf-8")
        self.assertIn('fill="#087fec"', icon)
        self.assertIn('d="M7 7v10c0 6 3.4 9 9 9s9-3 9-9V7"', icon)

    def test_server_returns_the_icon_files(self):
        client = app_module.app.test_client()
        for path, kind in (("/favicon.ico", "image/"), ("/favicon.svg", "image/svg+xml"), ("/apple-touch-icon.png", "image/png")):
            with self.subTest(path=path):
                response = client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.content_type.startswith(kind), response.content_type)
                self.assertGreater(len(response.data), 100)
                response.close()


class ReportShapeTests(unittest.TestCase):
    def test_progress_is_a_track_and_two_lists(self):
        progress = function_source("renderProgress")
        self.assertIn('<div class="progress-track" role="img"', progress)
        self.assertIn("--from:' + fromScore + '%;--to:' + toScore + '%", progress)
        self.assertIn('<span class="progress-track-mark is-before"></span>', progress)
        self.assertIn('<div class="progress-ledger">', progress)
        self.assertNotIn("report-progress-grid", progress)
        # The score row (numbers + track) is what a minimized phone card keeps.
        self.assertIn("#reportProgressBody.is-collapsed > :not(.report-progress-score) { display: none; }", REPORT)
        for label, malay in (("Better now", "Lebih baik sekarang"), ("Still to do", "Masih perlu dibuat"), ("Improve with", "Perbaiki dengan")):
            with self.subTest(label=label):
                self.assertIn(f'"{label}": "{malay}"', COMMON)

    def test_edits_and_plan_are_numbered_timelines(self):
        quick = function_source("renderQuickActions")
        self.assertIn('<span class="quick-edit-number" aria-hidden="true">\' + (index + 1) + \'</span>', quick)
        self.assertNotIn("/ EDIT", quick)
        self.assertIn(".report-quick-list article:not(:last-child)::before, .priority-action-grid > .priority-action:not(:last-child)::before", REPORT)
        self.assertIn(".report-quick-list, #priorityActionList.priority-action-grid { grid-template-columns: minmax(0, 1fr); gap: 0; }", REPORT)

    def test_top_roles_are_a_ranked_bar_chart(self):
        roles = REPORT.split("function renderTopRoleMatches", 1)[1].split("\n    function ", 1)[0]
        self.assertIn('<span class="role-match-bar" aria-hidden="true"><span></span></span>', roles)
        self.assertIn("' style=\"--role-score:' + score + '%\">'", roles)
        self.assertIn("(isFinal ? ' data-final=\"true\"' : \"\")", roles)
        # Wide screens open only the first row (the role used for the score).
        self.assertIn('const openAttribute = listOpen && index === 0 ? " open" : "";', roles)
        self.assertIn(".role-match-grid { grid-template-columns: minmax(0, 1fr); gap: 0;", REPORT)

    def test_report_top_has_no_cards_and_a_full_width_band(self):
        # Sample notice, score, progress and next edits sit in one open area.
        top = REPORT[REPORT.index('<div class="report-top">'):REPORT.index('<nav class="report-tabs"')]
        for block in ('id="reportSampleBanner"', 'class="report-hero"', 'id="reportProgress"', 'class="report-quick"'):
            self.assertIn(block, top)
        self.assertIn("padding: 0; border: 0; border-radius: 0; background: none; color: #16466f;", REPORT)
        self.assertIn(".report-progress, .report-quick { margin: 0; padding: clamp(1.4rem,3vw,2rem) 0; border: 0; border-top: 1px solid #d3e3f2;", REPORT)
        self.assertIn("overflow: visible; border: 0; border-radius: 0; background: none; box-shadow: none; }", REPORT)
        # The band is painted on the page, so it reaches both screen edges
        # while the report body still clips sideways slide-ins.
        self.assertIn("body { background-image: radial-gradient(440px circle at 6% 170px,", REPORT)
        self.assertIn("        .report-main { overflow-x: clip; }", REPORT)

    def test_role_route(self):
        self.assertIn('#selectedDatabaseRoleDisplay::before { content: "\\2192";', REPORT)


if __name__ == "__main__":
    unittest.main()
