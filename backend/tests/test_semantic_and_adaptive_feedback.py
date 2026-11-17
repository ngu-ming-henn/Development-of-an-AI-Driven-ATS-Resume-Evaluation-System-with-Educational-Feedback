"""Semantic requirement matching (skill knowledge base) and adaptive progress feedback."""

import importlib
import io
import os
import re
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

with patch.dict(
    os.environ,
    {
        "APP_ENV": "testing",
        "FLASK_SECRET_KEY": "semantic-adaptive-tests-only-secret-key-value-1234567890",
        "ACCURACY_TESTING_AUTO_EXPORT": "0",
    },
    clear=False,
):
    app_module = importlib.import_module("app")

import skill_knowledge  # noqa: E402


def score(resume_text, requirement_text):
    resume_tokens = set(app_module.tokenize_canonical_keywords(resume_text))
    return app_module.score_requirement_against_resume(resume_text, resume_tokens, requirement_text)


def concept_index(name):
    return next(index for index, concept in enumerate(skill_knowledge.SKILL_CONCEPTS) if concept.name == name)


class SemanticRequirementMatchingTests(unittest.TestCase):
    def test_specific_tool_proves_the_general_requirement(self):
        result = score("Built image classifiers with TensorFlow and PyTorch.", "Machine Learning")

        self.assertEqual(result["matched_tokens"], ["machine", "learning"])
        self.assertEqual(result["missing_tokens"], [])
        self.assertEqual(len(result["semantic_matches"]), 1)
        self.assertEqual(result["semantic_matches"][0]["concept"], "Machine learning")
        self.assertIn("TensorFlow", result["semantic_matches"][0]["evidence"])
        self.assertGreater(result["score"], 80)

    def test_tool_category_requirements_are_proven_by_named_tools(self):
        for resume_text, requirement in (
            ("Set up Jenkins and GitHub Actions pipelines for 12 services.", "CI/CD tools"),
            ("Monitored 40 branch sites with Nagios and Wireshark.", "Network monitoring tools"),
            ("Wrote Selenium and Jest test suites for the checkout flow.", "Software Testing"),
            ("Built monthly sales dashboards in Power BI.", "Data Visualization"),
            ("Stored user data in MongoDB Atlas through Mongoose.", "Mongo DB"),
        ):
            with self.subTest(requirement=requirement):
                result = score(resume_text, requirement)
                self.assertTrue(result["semantic_matches"])
                self.assertEqual(result["missing_tokens"], [])

    def test_relation_only_works_from_specific_to_general(self):
        # A general skill or another vendor never proves a specific product.
        self.assertEqual(score("Hosted the web app on AWS.", "Microsoft Azure")["semantic_matches"], [])
        self.assertEqual(score("Strong machine learning background.", "TensorFlow")["semantic_matches"], [])
        # One language does not prove another.
        self.assertEqual(score("Built backend services in Java.", "Python")["semantic_matches"], [])

    def test_negated_tools_are_not_evidence(self):
        result = score("No experience with TensorFlow or PyTorch yet.", "Machine Learning")
        self.assertEqual(result["semantic_matches"], [])

    def test_everyday_words_from_other_fields_are_not_tool_evidence(self):
        non_cs_resume = (
            "Head Chef at a hotel kitchen. Postman delivering mail. Coached the rugby scrum. "
            "Able to react quickly to customer complaints. Made it support three languages. "
            "Prepared each flask in the chemistry lab. Ran a kanban board on the factory floor. "
            "Supervised learning activities for Year 3 pupils."
        )
        found = app_module.get_resume_skill_concepts(non_cs_resume)
        self.assertEqual(found, {})

    def test_ambiguous_product_names_are_matched_case_sensitively(self):
        front_end = concept_index("Front-end development")
        self.assertIn("React", app_module.get_resume_skill_concepts("Built single-page apps in React.").get(front_end, ()))
        self.assertNotIn(front_end, app_module.get_resume_skill_concepts("Able to react quickly under pressure."))
        back_end = concept_index("Back-end development")
        self.assertIn("Node.js", app_module.get_resume_skill_concepts("Wrote services in Node.js.").get(back_end, ()))
        self.assertNotIn(back_end, app_module.get_resume_skill_concepts("Replaced a failed network node."))

    def test_tool_names_wrapped_across_pdf_lines_still_count(self):
        ide = concept_index("Development environments")
        found = app_module.get_resume_skill_concepts("Skills: Python, Git, Docker, VS\nCode, Jira")
        self.assertIn("VS Code", found.get(ide, ()))

    def test_wording_advice_skips_tool_categories(self):
        analysis = {
            "role_recommendation": {"recommended_role": "Software Developer", "match_status": "matched"},
            "job_description_analysis": {
                "semantic_matches": [
                    {"concept": "Development environments", "evidence": ["VS Code"], "requirements": ["Development Environment Software"]}
                ],
            },
        }
        actions = app_module.build_part8_recommendation_module(analysis)["priority_actions"]
        self.assertNotIn("ats_wording", [action["category"] for action in actions])

    def test_exact_triggers_only_match_the_whole_requirement(self):
        monitoring = concept_index("Monitoring")
        self.assertIn(monitoring, dict(app_module.get_requirement_skill_concepts("Monitoring")))
        self.assertNotIn(monitoring, dict(app_module.get_requirement_skill_concepts("Staff performance monitoring")))

    def test_exact_requirement_wording_still_scores_full_marks(self):
        result = score("Applied machine learning with TensorFlow.", "Machine Learning")
        self.assertEqual(result["score"], 100.0)
        self.assertEqual(result["semantic_matches"], [])

    def test_semantic_evidence_reaches_the_report_and_removes_false_gaps(self):
        requirements = [
            {"requirement_text": "Machine Learning", "requirement_type": "skill", "importance_weight": 5},
            {"requirement_text": "Python", "requirement_type": "skill", "importance_weight": 5},
            {"requirement_text": "Kubernetes", "requirement_type": "tool", "importance_weight": 3},
        ]
        resume_text = (
            "Skills: Python, TensorFlow, PyTorch\n"
            "Projects: trained a CNN image classifier with TensorFlow and served it with Flask."
        )
        analysis = app_module.build_analysis_payload(
            resume_text,
            "Machine Learning Python Kubernetes",
            "resume.pdf",
            requirements,
            "Machine Learning Engineer",
            {"file_type": "pdf"},
        )
        job = analysis["job_description_analysis"]

        self.assertEqual([item["concept"] for item in job["semantic_matches"]], ["Machine learning"])
        self.assertIn("Machine Learning", job["semantic_matches"][0]["requirements"])
        self.assertNotIn("machine", job["missing_keywords"])
        self.assertNotIn("learning", job["missing_keywords"])
        # Kubernetes has no evidence, so it stays a real gap.
        kubernetes = app_module.normalize_keyword_token("Kubernetes")
        self.assertIn(kubernetes, job["missing_keywords"])
        self.assertIn(kubernetes, job["all_missing_keywords"])

    def test_improvement_plan_asks_for_the_exact_terms(self):
        analysis = {
            "target_role": "Machine Learning Engineer",
            "role_recommendation": {"recommended_role": "Machine Learning Engineer", "match_status": "matched"},
            "job_description_analysis": {
                "missing_keywords": [],
                "semantic_matches": [
                    {"concept": "Machine learning", "evidence": ["TensorFlow", "PyTorch"], "requirements": ["Machine Learning"]}
                ],
            },
            "compatibility": {},
        }
        actions = app_module.build_part8_recommendation_module(analysis)["priority_actions"]
        wording = next(action for action in actions if action["category"] == "ats_wording")
        self.assertEqual(wording["keywords"], ["Machine Learning"])
        self.assertIn("TensorFlow", wording["detail"])

    def test_knowledge_base_is_well_formed(self):
        everyday_words = {
            "react", "node", "chef", "puppet", "scrum", "kanban", "helm", "postman", "mocha", "sprint",
            "it", "flask", "blender", "bootstrap", "selenium", "panda", "rest", "angular", "unity", "swift",
        }
        names = set()
        for concept in skill_knowledge.SKILL_CONCEPTS:
            with self.subTest(concept=concept.name):
                self.assertNotIn(concept.name, names)
                names.add(concept.name)
                self.assertTrue(concept.triggers)
                self.assertTrue(concept.evidence or concept.patterns)
                for trigger in concept.triggers:
                    self.assertTrue(app_module.tokenize_canonical_keywords(trigger.lstrip("=")), trigger)
                for evidence in concept.evidence:
                    tokens = app_module.skill_evidence_tokens(evidence)
                    self.assertTrue(tokens, evidence)
                    if len(tokens) == 1:
                        self.assertNotIn(tokens[0], everyday_words, evidence)
                for _, pattern in concept.patterns:
                    re.compile(pattern)


def make_analysis(score_value, shown_missing=(), all_matched=(), all_missing=(), issues=(), components=None):
    return {
        "target_role": "Software Developer",
        "matching_percentage": score_value,
        "compatibility": dict(components or {}, matching_percentage=score_value),
        "job_description_analysis": {
            "missing_keywords": list(shown_missing),
            "all_matched_keywords": list(all_matched),
            "all_missing_keywords": list(all_missing),
        },
        "resume_quality": {"issues": [{"category": category, "title": title} for category, title in issues]},
    }


class AdaptiveProgressTests(unittest.TestCase):
    def test_first_check_for_a_role_has_no_comparison(self):
        progress = app_module.build_progress_since_last_check(make_analysis(55), {"analysis": None, "checks_for_role": 0})
        self.assertEqual(progress, {"available": False, "target_role": "Software Developer", "check_number": 1})

    def test_progress_reports_score_change_keywords_and_components(self):
        previous = make_analysis(
            50.5,
            shown_missing=["sql", "docker", "aws"],
            all_matched=["python"],
            all_missing=["sql", "docker", "aws"],
            components={"keyword_match": 40, "resume_quality": 70},
        )
        current = make_analysis(
            58,
            shown_missing=["docker", "aws"],
            all_matched=["python", "sql"],
            all_missing=["docker", "aws"],
            components={"keyword_match": 52, "resume_quality": 70},
        )
        progress = app_module.build_progress_since_last_check(
            current,
            {"analysis": previous, "checks_for_role": 2, "analysis_id": 9, "checked_at": "2026-11-10T08:00:00"},
        )

        self.assertTrue(progress["available"])
        self.assertEqual(progress["check_number"], 3)
        self.assertEqual(progress["trend"], "improved")
        self.assertEqual(progress["score_change"], 7.5)
        self.assertEqual(progress["keywords_now_matched"], ["SQL"])
        self.assertEqual(progress["keywords_still_missing"], ["Docker", "AWS"])
        self.assertEqual(progress["keywords_no_longer_found"], [])
        self.assertEqual(
            progress["components"][0],
            {"key": "keyword_match", "label": "Keyword match", "previous": 40, "current": 52, "change": 12},
        )
        self.assertEqual(progress["summary"], "Your score rose by 7.5 points since your last check (50.5 to 58). Now shown: SQL.")

    def test_progress_flags_evidence_that_disappeared(self):
        previous = make_analysis(60, all_matched=["python", "docker"], all_missing=["aws"])
        current = make_analysis(52, all_matched=["python"], all_missing=["aws", "docker"])
        progress = app_module.build_progress_since_last_check(current, {"analysis": previous, "checks_for_role": 1})

        self.assertEqual(progress["trend"], "declined")
        self.assertEqual(progress["keywords_no_longer_found"], ["Docker"])
        self.assertIn("No longer found: Docker", progress["summary"])

    def test_score_change_matches_the_rounded_scores_shown(self):
        # 72.51 - 54.06 = 18.45, but the report shows 54.1 and 72.5, so the change must read 18.4.
        progress = app_module.build_progress_since_last_check(
            make_analysis(72.51), {"analysis": make_analysis(54.06), "checks_for_role": 1}
        )
        self.assertEqual(progress["score_change"], 18.4)
        self.assertEqual(progress["summary"], "Your score rose by 18.4 points since your last check (54.1 to 72.5).")
        self.assertEqual(app_module.format_score_points(54.05), "54.1")

    def test_small_changes_count_as_unchanged(self):
        progress = app_module.build_progress_since_last_check(
            make_analysis(60.4, shown_missing=["aws"], all_missing=["aws"]),
            {"analysis": make_analysis(60.0, shown_missing=["aws"], all_missing=["aws"]), "checks_for_role": 1},
        )
        self.assertEqual(progress["trend"], "unchanged")
        self.assertEqual(progress["keywords_still_missing"], ["AWS"])

    def test_progress_tracks_fixed_open_and_new_ats_issues(self):
        previous = make_analysis(50, issues=[("Contact", "Incomplete contact details"), ("Impact", "Limited measurable impact")])
        current = make_analysis(55, issues=[("Impact", "Limited measurable impact"), ("Length", "Resume may be too long")])
        progress = app_module.build_progress_since_last_check(current, {"analysis": previous, "checks_for_role": 1})

        self.assertEqual(progress["ats_issues_fixed"], ["Incomplete contact details"])
        self.assertEqual(progress["ats_issues_still_open"], ["Limited measurable impact"])
        self.assertEqual(progress["ats_issues_new"], ["Resume may be too long"])

    def test_plan_puts_repeated_gaps_first(self):
        analysis = make_analysis(
            48,
            shown_missing=["docker", "aws"],
            all_missing=["docker", "aws"],
            issues=[("Contact", "Incomplete contact details"), ("Impact", "Limited measurable impact")],
        )
        analysis["role_recommendation"] = {"recommended_role": "Software Developer", "match_status": "matched"}
        analysis["resume_quality"]["issues"] = [
            {"category": "Contact", "title": "Incomplete contact details", "detail": "d", "suggestion": "s"},
            {"category": "Impact", "title": "Limited measurable impact", "detail": "d", "suggestion": "s"},
        ]
        analysis["progress"] = {
            "available": True,
            "keywords_still_missing": ["Docker"],
            "keywords_no_longer_found": [],
            "ats_issues_still_open": ["Limited measurable impact"],
            "summary": "Your score is about the same as your last check (48).",
        }
        module = app_module.build_part8_recommendation_module(analysis)
        actions = module["priority_actions"]

        self.assertEqual(actions[0]["title"], "Still missing since your last check")
        self.assertEqual(actions[0]["keywords"][0], "Docker")
        self.assertTrue(actions[0]["adaptive"])
        self.assertEqual(actions[1]["title"], "Still open: Limited measurable impact")
        self.assertEqual([action["priority"] for action in actions], list(range(1, len(actions) + 1)))
        self.assertTrue(module["summary"].startswith("Your score is about the same as your last check"))

    def test_plan_asks_to_restore_lost_evidence(self):
        analysis = make_analysis(40)
        analysis["role_recommendation"] = {"recommended_role": "Software Developer", "match_status": "matched"}
        analysis["progress"] = {"available": True, "keywords_no_longer_found": ["Docker"], "summary": "s"}
        actions = app_module.build_part8_recommendation_module(analysis)["priority_actions"]

        self.assertEqual(actions[0]["category"], "regression")
        self.assertEqual(actions[0]["keywords"], ["Docker"])

    def test_role_review_gate_stays_ahead_of_carried_over_actions(self):
        analysis = make_analysis(18, shown_missing=["sql"], all_missing=["sql"])
        analysis["role_recommendation"] = {
            "recommended_role": "Software Developer",
            "match_status": "no_suitable_role",
            "human_review_required": True,
            "reason_summary": "No database role reached the threshold.",
        }
        analysis["progress"] = {"available": True, "keywords_still_missing": ["SQL"], "summary": "s"}
        actions = app_module.build_part8_recommendation_module(analysis)["priority_actions"]

        self.assertEqual(actions[0]["category"], "role_fit_review")
        self.assertEqual(actions[1]["title"], "Still missing since your last check")


class FakeHistoryCursor:
    def __init__(self, rows, stored):
        self.rows = rows
        self.stored = stored
        self.queries = []
        self.result = []

    def execute(self, query, params=()):
        self.queries.append((" ".join(query.split()), params))
        if "SELECT id, target_role, created_at" in query:
            self.result = list(self.rows)
        else:
            self.result = [{"analysis_json": self.stored.get(params[0])}]

    def fetchall(self):
        return self.result

    def fetchone(self):
        return self.result[0] if self.result else None

    def close(self):
        pass


class FakeHistoryConnection:
    def __init__(self, cursor):
        self.history_cursor = cursor
        self.closed = False

    def cursor(self, dictionary=False):
        return self.history_cursor

    def close(self):
        self.closed = True


class PreviousAnalysisLookupTests(unittest.TestCase):
    def test_latest_analysis_for_the_same_role_is_used(self):
        rows = [
            {"id": 30, "target_role": "Data Scientist", "created_at": None},
            {"id": 21, "target_role": "software developer", "created_at": None},
            {"id": 12, "target_role": "Software Developer", "created_at": None},
        ]
        cursor = FakeHistoryCursor(rows, {21: '{"matching_percentage": 61}'})
        connection = FakeHistoryConnection(cursor)
        with patch.object(app_module, "get_db_connection", return_value=connection):
            record = app_module.fetch_previous_role_analysis(7, "Software Developer")

        self.assertEqual(record["analysis_id"], 21)
        self.assertEqual(record["checks_for_role"], 2)
        self.assertEqual(record["analysis"], {"matching_percentage": 61})
        # The report is loaded for its owner only.
        self.assertEqual(cursor.queries[1][1], (21, 7))
        self.assertTrue(connection.closed)

    def test_no_previous_analysis_for_a_new_role(self):
        cursor = FakeHistoryCursor([{"id": 30, "target_role": "Data Scientist", "created_at": None}], {})
        with patch.object(app_module, "get_db_connection", return_value=FakeHistoryConnection(cursor)):
            record = app_module.fetch_previous_role_analysis(7, "Software Developer")

        self.assertEqual(record, {"analysis": None, "checks_for_role": 0})
        self.assertEqual(len(cursor.queries), 1)


class AnalyzeEndpointProgressTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config.update(TESTING=True, SECRET_KEY="semantic-adaptive-endpoint-secret")
        self.client = app_module.app.test_client()

    def test_new_analysis_is_compared_with_the_last_check(self):
        previous = make_analysis(50, shown_missing=["sql"], all_missing=["sql"])
        current = make_analysis(62, all_matched=["sql"])
        with ExitStack() as stack:
            stack.enter_context(patch.object(app_module, "get_authenticated_session_user", return_value={"id": 7}))
            stack.enter_context(patch.object(app_module, "should_enforce_extra_rate_limits", return_value=False))
            stack.enter_context(patch.object(app_module, "extract_resume_text", return_value=("resume text", {"file_type": "pdf"})))
            stack.enter_context(patch.object(app_module, "resolve_database_job_description", return_value=None))
            stack.enter_context(patch.object(app_module, "rank_database_role_matches", return_value=[]))
            stack.enter_context(patch.object(app_module, "pick_recommended_database_job", return_value=(None, None, None)))
            stack.enter_context(patch.object(app_module, "build_role_recommendation", return_value={"top_role_matches": []}))
            stack.enter_context(patch.object(app_module, "build_analysis_payload", return_value=current))
            stack.enter_context(patch.object(app_module, "extract_resume_contact", return_value={}))
            lookup = stack.enter_context(
                patch.object(
                    app_module,
                    "fetch_previous_role_analysis",
                    return_value={"analysis": previous, "checks_for_role": 1, "analysis_id": 4, "checked_at": None},
                )
            )
            stack.enter_context(patch.object(app_module, "persist_analysis", return_value=55))
            stack.enter_context(patch.object(app_module, "update_accuracy_testing_workbook", return_value={}))

            response = self.client.post(
                "/analyze-file",
                data={
                    "resume_file": (io.BytesIO(b"mock PDF"), "resume.pdf"),
                    "job_description": "Build software",
                    "target_role": "Software Developer",
                },
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 200)
        lookup.assert_called_once_with(7, "Software Developer")
        progress = response.get_json()["progress"]
        self.assertTrue(progress["available"])
        self.assertEqual(progress["score_change"], 12.0)
        self.assertEqual(progress["keywords_now_matched"], ["SQL"])

    def test_database_problem_only_skips_the_comparison(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(app_module, "get_authenticated_session_user", return_value={"id": 7}))
            stack.enter_context(patch.object(app_module, "should_enforce_extra_rate_limits", return_value=False))
            stack.enter_context(patch.object(app_module, "extract_resume_text", return_value=("resume text", {"file_type": "pdf"})))
            stack.enter_context(patch.object(app_module, "resolve_database_job_description", return_value=None))
            stack.enter_context(patch.object(app_module, "rank_database_role_matches", return_value=[]))
            stack.enter_context(patch.object(app_module, "pick_recommended_database_job", return_value=(None, None, None)))
            stack.enter_context(patch.object(app_module, "build_role_recommendation", return_value={"top_role_matches": []}))
            stack.enter_context(patch.object(app_module, "build_analysis_payload", return_value=make_analysis(62)))
            stack.enter_context(patch.object(app_module, "extract_resume_contact", return_value={}))
            stack.enter_context(
                patch.object(app_module, "fetch_previous_role_analysis", side_effect=app_module.DatabaseError("offline"))
            )
            stack.enter_context(patch.object(app_module, "persist_analysis", return_value=56))
            stack.enter_context(patch.object(app_module, "update_accuracy_testing_workbook", return_value={}))

            response = self.client.post(
                "/analyze-file",
                data={
                    "resume_file": (io.BytesIO(b"mock PDF"), "resume.pdf"),
                    "job_description": "Build software",
                    "target_role": "Software Developer",
                },
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()["progress"]["available"])


FRONTEND_DIR = BACKEND_DIR.parent / "frontend"


class FrontendWiringTests(unittest.TestCase):
    def test_report_page_renders_progress_and_related_skills(self):
        page = (FRONTEND_DIR / "analysis_result.html").read_text(encoding="utf-8")
        self.assertIn('id="reportProgress"', page)
        self.assertIn("renderProgress(result.progress);", page)
        self.assertIn('id="relatedSkillPanel"', page)
        self.assertIn("renderRelatedSkills(jobAnalysis.semantic_matches);", page)
        # The preview and the PDF report receive both blocks as well.
        self.assertIn("buildReportProgressSection(report.progress)", page)
        self.assertIn("buildReportRelatedSkillsSection(report.semanticMatches)", page)
        self.assertIn("semanticMatches: Array.isArray(jobAnalysis.semantic_matches)", page)
        self.assertIn('progress: result.progress && typeof result.progress === "object"', page)
        # Keyword edits in "Your next 3 edits" list the words that "add them" refers to.
        self.assertIn('const keywordCategories = new Set(["keyword_gap", "ats_wording"]);', page)
        self.assertIn('<ul class="quick-keywords">', page)

    def test_new_labels_have_malay_translations(self):
        common = (FRONTEND_DIR / "app_common.js").read_text(encoding="utf-8")
        for label in ("Your progress", "Still missing", "Skills proven by the tools you named", "Suggested last time and still missing."):
            with self.subTest(label=label):
                self.assertIn(f'"{label}": ', common)
        self.assertIn("[/^Check (\\d+) for (.+)$/", common)
        self.assertIn("[/^Your score rose by", common)

    def test_pdf_report_includes_progress_and_related_skills(self):
        report = {
            "scoreOutOf100": 61,
            "progress": {
                "available": True,
                "previous_score": 50,
                "current_score": 61,
                "score_change": 11,
                "check_number": 2,
                "keywords_now_matched": ["SQL"],
                "summary": "Your score rose by 11 points since your last check (50 to 61). Now shown: SQL.",
            },
            "semanticMatches": [{"concept": "Machine learning", "evidence": ["TensorFlow"]}],
        }
        try:
            pdf_buffer = app_module.build_feedback_report_pdf_buffer(report)
        except RuntimeError as error:  # reportlab is optional in some environments
            self.skipTest(str(error))
        text = " ".join(page.extract_text() for page in app_module.PdfReader(pdf_buffer).pages)
        self.assertIn("PROGRESS SINCE YOUR LAST CHECK", text)
        self.assertIn("50 to 61 (+11 points)", text)
        self.assertIn("Proven by related skills: Machine learning (TensorFlow)", " ".join(text.split()))


if __name__ == "__main__":
    unittest.main()
