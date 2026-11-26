"""Learning-example resumes below 40% and the rotating popular market roles."""

import importlib
import os
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

with patch.dict(
    os.environ,
    {
        "APP_ENV": "testing",
        "FLASK_SECRET_KEY": "low-match-example-tests-only-secret-key-value-1234567890",
        "ACCURACY_TESTING_AUTO_EXPORT": "0",
    },
    clear=False,
):
    app_module = importlib.import_module("app")


def make_analysis(top_roles, selected=None):
    role_recommendation = {
        "top_role_matches": [{"role": role, "score": score} for role, score in top_roles],
        "match_status": "recommended",
    }
    if selected:
        role_recommendation.update(selected_role=selected[0], selected_score=selected[1])
    return {
        "matching_percentage": 33,
        "target_role": selected[0] if selected else top_roles[0][0],
        "top_role_matches": [{"role": role, "score": score} for role, score in top_roles],
        "role_recommendation": role_recommendation,
        "resume_summary": {"skills": ["python", "sql"], "education_markers": ["bachelor"], "experience_markers": ["built"]},
        "job_description_analysis": {"matched_keywords": [], "missing_keywords": []},
    }


RESUME_TEXT = "\n".join([
    "Alex Example",
    "alex.example@example.com | +60 12-345 6789",
    "Projects",
    "Library Booking System",
    "- Built a web system with Python and SQL for students to book library rooms",
    "Education",
    "Bachelor of Computer Science",
    "University of Technology Sarawak",
    "2023 - Present",
])


class LowMatchExampleTests(unittest.TestCase):
    def test_roles_below_40_get_one_example_per_family(self):
        guide = app_module.build_low_match_role_examples(
            make_analysis([("Software Developer", 36.0), ("Computer Programmer", 34.5), ("Business Data Analyst", 31.0)])
        )
        self.assertEqual(guide["threshold"], 40.0)
        self.assertEqual(guide["note"], app_module.LOW_MATCH_NOTE_RECOMMENDED)
        self.assertEqual([example["roles"] for example in guide["examples"]],
                         [["Software Developer", "Computer Programmer"], ["Business Data Analyst"]])
        first = guide["examples"][0]
        self.assertEqual(first["score"], 36.0)
        self.assertIn("Your own draft is shown separately", first["plain_text"] + first["html"])

    def test_selected_role_comes_first_and_changes_the_note(self):
        guide = app_module.build_low_match_role_examples(
            make_analysis([("Software Developer", 36.0), ("Software Designer", 35.0), ("Computer Programmer", 34.0)],
                          selected=("Cybersecurity Analyst", 28.0))
        )
        self.assertEqual(guide["note"], app_module.LOW_MATCH_NOTE_WITH_SELECTED)
        self.assertEqual(guide["examples"][0]["role"], "Cybersecurity Analyst")
        self.assertEqual(len(guide["examples"]), 2)

    def test_no_examples_when_any_role_reaches_40(self):
        self.assertIsNone(app_module.build_low_match_role_examples(
            make_analysis([("Software Developer", 41.0), ("Computer Programmer", 30.0), ("Software Designer", 29.0)])
        ))
        self.assertIsNone(app_module.build_low_match_role_examples(
            make_analysis([("Software Developer", 30.0), ("Software Designer", 29.0), ("Computer Programmer", 28.0)],
                          selected=("Data Scientist", 52.0))
        ))

    def test_generated_draft_keeps_the_real_resume_and_adds_examples(self):
        draft = app_module.build_generated_resume_payload(
            make_analysis([("Software Developer", 36.0), ("Computer Programmer", 34.5), ("Business Data Analyst", 31.0)]),
            RESUME_TEXT,
            "Software Developer",
        )
        self.assertFalse(draft.get("sample_only"))
        self.assertIn("Library Booking System", draft["plain_text"])
        self.assertEqual(len(draft["role_examples"]["examples"]), 2)

    def test_draft_above_40_has_no_examples(self):
        draft = app_module.build_generated_resume_payload(
            make_analysis([("Software Developer", 58.0), ("Computer Programmer", 50.0), ("Software Designer", 47.0)]),
            RESUME_TEXT,
            "Software Developer",
        )
        self.assertNotIn("role_examples", draft)


    def test_catalogue_role_names_get_a_specific_example_family(self):
        expected = {
            "Security Technologist Specialist": "Cybersecurity",
            "Data Security Specialist": "Cybersecurity",
            "Digital Forensic Specialist": "Cybersecurity",
            "Computer Infrastructure Specialist": "Network / Infrastructure",
            "Product Support Engineer": "IT Support",
            "Java Consultant": "Software Development",
            "Graphic Designer": "Technology",
        }
        for role, family in expected.items():
            with self.subTest(role=role):
                self.assertEqual(app_module.build_sample_resume_role_profile(role)["family"], family)


class FrontendTests(unittest.TestCase):
    def test_report_renders_examples_only_for_real_drafts(self):
        page = (FRONTEND_DIR / "analysis_result.html").read_text(encoding="utf-8")
        self.assertIn('id="roleExamplesPanel"', page)
        self.assertIn("renderRoleExamples(isExample ? null : draft.role_examples);", page)
        common = (FRONTEND_DIR / "app_common.js").read_text(encoding="utf-8")
        for text in (app_module.LOW_MATCH_NOTE_RECOMMENDED, app_module.LOW_MATCH_NOTE_WITH_SELECTED,
                     "Example resumes for your recommended roles"):
            with self.subTest(text=text[:40]):
                self.assertIn(f'"{text}": ', common)

    def test_every_rotating_popular_role_maps_to_a_database_role(self):
        page = (FRONTEND_DIR / "home_page.html").read_text(encoding="utf-8")
        block = re.search(r"const POPULAR_ROLE_SETS = \[(.*?)\];", page, re.S).group(1)
        sets = re.findall(r"\[([^\[\]]*)\]", block)
        self.assertEqual(len(sets), 3)
        roles = [role for group in sets for role in re.findall(r'"([^"]+)"', group)]
        self.assertTrue(all(len(re.findall(r'"([^"]+)"', group)) == 6 for group in sets))
        self.assertEqual(len(roles), len(set(roles)))
        for role in roles:
            with self.subTest(role=role):
                self.assertIn(role.lower(), app_module.POPULAR_ROLE_ALIASES)


if __name__ == "__main__":
    unittest.main()
