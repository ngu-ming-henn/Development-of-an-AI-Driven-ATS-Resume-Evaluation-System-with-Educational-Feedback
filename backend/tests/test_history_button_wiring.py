from __future__ import annotations

import unittest
from pathlib import Path


FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


class HistoryButtonWiringTests(unittest.TestCase):
    def test_guest_account_icon_offers_sign_in_and_sign_up_on_every_page(self):
        common_source = (FRONTEND_DIR / "app_common.js").read_text(encoding="utf-8")
        # Guests can also open Settings (language and colours); the account cards stay hidden.
        self.assertIn('hasAccount ? ["info", "settings", "history"] : ["access", "settings"]', common_source)
        self.assertIn("securityCards.forEach((card) => { card.hidden = !hasAccount; });", common_source)
        self.assertIn('button.dataset.accountGo', common_source)
        for page_name in ("home_page.html", "analysis_result.html", "job_data_insights.html"):
            with self.subTest(page=page_name):
                page_source = (FRONTEND_DIR / page_name).read_text(encoding="utf-8")
                self.assertIn('id="openAuthModalBtn"', page_source)
                self.assertIn('aria-controls="profileModal"', page_source)
                self.assertNotIn('id="openHistoryBtn"', page_source)
                self.assertIn('data-account-panel="access"', page_source)
                self.assertIn('data-account-view="history"', page_source)
                self.assertIn('data-account-view="history" data-account-auth-only', page_source)
                self.assertNotIn('data-account-go="history"', page_source)
                self.assertIn('data-account-auth-action="login" data-account-guest-only', page_source)
                self.assertIn('data-account-auth-action="register" data-account-guest-only', page_source)
                self.assertIn("createHistoryModal({", page_source)

    def test_clearing_history_also_forgets_the_latest_report(self):
        common_source = (FRONTEND_DIR / "app_common.js").read_text(encoding="utf-8")
        clear_handler = common_source.split('requestHistory("/analyses", "DELETE")', 1)[1].split("render();", 1)[0]
        self.assertIn("forgetLatestReport();", clear_handler)
        self.assertIn("forgetLatestReport({ analysisId: id, historyKey: item.history_key });", common_source)
        self.assertIn('new CustomEvent("career-navigator-report-cleared")', common_source)
        for page_name in ("home_page.html", "analysis_result.html"):
            with self.subTest(page=page_name):
                page_source = (FRONTEND_DIR / page_name).read_text(encoding="utf-8")
                self.assertIn('window.addEventListener("career-navigator-report-cleared"', page_source)

    def test_guest_sign_in_action_opens_existing_auth_flow(self):
        for page_name in ("home_page.html", "analysis_result.html"):
            with self.subTest(page=page_name):
                page_source = (FRONTEND_DIR / page_name).read_text(encoding="utf-8")
                self.assertIn('closeProfileModal();', page_source)
                self.assertIn('openAuthModal(mode);', page_source)


if __name__ == "__main__":
    unittest.main()
