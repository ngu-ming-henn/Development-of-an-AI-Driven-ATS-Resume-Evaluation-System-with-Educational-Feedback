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
        self.assertIn(".report-progress, .report-quick { margin: 0; padding: clamp(1.75rem,3.5vw,2.5rem) 0; border: 0; border-radius: 0; background: none; box-shadow: none; }", REPORT)
        self.assertIn("overflow: visible; border: 0; border-radius: 0; background: none; box-shadow: none; }", REPORT)
        # No side line between the title and the score.
        self.assertIn(".report-hero .report-score-card { border-left: 0; border-top: 0; }", REPORT)

    def test_sections_are_split_by_background_bands(self):
        # Like the home page: full-width bands take turns (blue behind the score,
        # then white and pale blue), and no lines run between the blocks.
        self.assertIn(".report-top::before, .report-progress::before, .report-quick::before, #job-match::before, #ats-checks::before, #resume-draft::before { content: \"\"; position: absolute; z-index: -1; top: 0; bottom: 0; left: calc(50% - 50vw); right: calc(50% - 50vw);", REPORT)
        self.assertIn(".report-top::before { z-index: -2; top: -48px; background:", REPORT)
        self.assertIn(".report-progress::before { background: #fff; }", REPORT)
        self.assertIn(".report-quick::before, #job-match::before, #ats-checks::before { background: #f3f8fe; }", REPORT)
        self.assertIn(".report-progress[hidden] + .report-quick::before { background: #fff; }", REPORT)
        self.assertIn("#resume-draft::before { bottom: -5rem; background: linear-gradient(180deg, #fff 0, #fff 30%, #e6f1fe 100%); }", REPORT)
        self.assertIn("body.bg-background { background-color: #fff; }", REPORT)
        self.assertNotIn(".report-quick::after", REPORT)
        self.assertNotIn("border-top: 1px solid #d3e3f2", REPORT)
        # The contents fade up; the section (and its band) stays put. Nothing
        # slides sideways, so the page never widens.
        self.assertIn(".report-section.report-reveal { opacity: 1; filter: none; transform: none; transition: none; }", REPORT)
        self.assertIn(".report-section.report-reveal.is-visible > * { opacity: 1; filter: none; transform: none; }", REPORT)
        self.assertIn('.report-reveal[data-reveal-side="left"], .report-reveal[data-reveal-side="right"] { --reveal-x: 0px; }', REPORT)
        self.assertNotIn("        .report-main { overflow-x: clip; }", REPORT)
        self.assertIn("html { scroll-behavior: smooth; overflow-x: clip; }", REPORT)

    def test_tracks_are_one_smooth_bar(self):
        self.assertIn("border-radius: 999px; background: #e2ecf6; }", REPORT)
        self.assertNotIn("repeating-linear-gradient(90deg, #e2ecf6 0 calc(10% - 2px)", REPORT)

    def test_files_and_next_steps_is_one_split_panel(self):
        panel = REPORT[REPORT.index('<div class="report-workspace-panel">'):REPORT.index('id="generatedResumePanel"')]
        self.assertIn('<div class="submission-card">', panel)
        self.assertIn('<div class="report-workspace-grid">', panel)
        self.assertIn(".report-workspace-panel .report-build-card { border-right: 1px solid var(--studio-border); }", REPORT)
        self.assertIn(".report-workspace-panel .report-work-card { border: 0; border-radius: 0; box-shadow: none; }", REPORT)

    def test_role_route(self):
        self.assertIn('#selectedDatabaseRoleDisplay::before { content: "\\2192";', REPORT)


if __name__ == "__main__":
    unittest.main()
