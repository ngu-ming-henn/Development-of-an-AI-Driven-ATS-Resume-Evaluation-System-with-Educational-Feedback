"""Image/scanned-PDF OCR, candidate name detection, contact details and
section parsing for real-world resume layouts. All resume text is fictional."""

from __future__ import annotations

import importlib
import os
import sys
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

with patch.dict(
    os.environ,
    {
        "APP_ENV": "testing",
        "FLASK_SECRET_KEY": "resume-ocr-parsing-tests-only-secret-key-value-1234567890",
        "ACCURACY_TESTING_AUTO_EXPORT": "0",
    },
    clear=False,
):
    app_module = importlib.import_module("app")

from PIL import Image  # noqa: E402


class UploadedFile:
    def __init__(self, filename: str, data: bytes):
        self.filename = filename
        self._data = data

    def read(self) -> bytes:
        return self._data


def image_bytes(size=(400, 560), mode="RGB", color="white", image_format="PNG") -> bytes:
    buffer = BytesIO()
    Image.new(mode, size, color).save(buffer, format=image_format)
    return buffer.getvalue()


OCR_RESUME_TEXT = (
    "JORDAN LEE\n"
    "jordan.lee@example.com | +60 12-345 6789\n"
    "\n"
    "EDUCATION\n"
    "Bachelor of Computer Science (Hons)\n"
    "University of Example Malaysia\n"
    "2023 - Present\n"
    "\n"
    "PROJECTS\n"
    "Campus Parking App | Flutter, Firebase\n"
    "e Built a parking finder used by 300 students with live slot updates and alerts.\n"
    "e Designed the Firebase data model and wrote unit tests for the booking flow.\n"
    "\n"
    "SKILLS\n"
    "Python, Java, SQL, Flutter, Firebase, Git, Linux, Docker, REST APIs, Machine Learning\n"
    "Communication, teamwork, problem solving, documentation and time management\n"
)


class TesseractSetupTests(unittest.TestCase):
    def test_configured_path_wins_when_it_exists(self):
        with patch.dict(os.environ, {"TESSERACT_CMD": r"D:\tools\tesseract.exe"}), patch.object(
            app_module.os.path, "isfile", side_effect=lambda path: path == r"D:\tools\tesseract.exe"
        ), patch.object(app_module.shutil, "which", return_value=None):
            self.assertEqual(app_module.find_tesseract_command(), r"D:\tools\tesseract.exe")

    def test_missing_configured_path_falls_back_to_path_lookup(self):
        with patch.dict(os.environ, {"TESSERACT_CMD": r"D:\missing\tesseract.exe"}), patch.object(
            app_module.os.path, "isfile", side_effect=lambda path: path == "/usr/bin/tesseract"
        ), patch.object(app_module.shutil, "which", return_value="/usr/bin/tesseract"):
            self.assertEqual(app_module.find_tesseract_command(), "/usr/bin/tesseract")

    def test_windows_default_install_folder_is_found_without_settings(self):
        default_path = app_module.WINDOWS_TESSERACT_PATHS[0]
        with patch.dict(os.environ, {"TESSERACT_CMD": ""}), patch.object(app_module.os, "name", "nt"), patch.object(
            app_module.os.path, "isfile", side_effect=lambda path: path == default_path
        ), patch.object(app_module.shutil, "which", return_value=None):
            self.assertEqual(app_module.find_tesseract_command(), default_path)

    def test_no_tesseract_gives_a_clear_message(self):
        with patch.object(app_module, "find_tesseract_command", return_value=""):
            with self.assertRaisesRegex(ValueError, "Install Tesseract OCR"):
                app_module.configure_tesseract()


class ImagePreparationTests(unittest.TestCase):
    def test_small_image_is_enlarged_for_ocr(self):
        prepared = app_module.prepare_image_for_ocr(Image.new("RGB", (400, 560), "white"))
        self.assertEqual(prepared.mode, "L")
        self.assertEqual(prepared.width, app_module.OCR_TARGET_WIDTH)
        self.assertEqual(prepared.height, 2800)

    def test_upscaling_is_capped(self):
        prepared = app_module.prepare_image_for_ocr(Image.new("RGB", (100, 140), "white"))
        self.assertEqual(prepared.width, int(100 * app_module.OCR_MAX_UPSCALE))

    def test_very_large_image_is_reduced_to_the_pixel_budget(self):
        prepared = app_module.prepare_image_for_ocr(Image.new("RGB", (5000, 7000), "white"))
        self.assertLessEqual(prepared.width * prepared.height, app_module.OCR_MAX_PIXELS * 1.01)

    def test_transparent_png_is_flattened_onto_white(self):
        transparent = Image.new("RGBA", (2400, 100), (0, 0, 0, 0))
        prepared = app_module.prepare_image_for_ocr(transparent)
        self.assertEqual(prepared.getpixel((10, 10)), 255)


class ImageUploadOcrTests(unittest.TestCase):
    def setUp(self):
        self.fake_tesseract = SimpleNamespace(image_to_string=lambda image, config="": OCR_RESUME_TEXT)
        self.patches = [
            patch.object(app_module, "configure_tesseract", return_value=None),
            patch.object(app_module, "pytesseract", self.fake_tesseract),
        ]
        for active_patch in self.patches:
            active_patch.start()

    def tearDown(self):
        for active_patch in reversed(self.patches):
            active_patch.stop()

    def test_image_text_keeps_its_lines_so_the_resume_can_be_parsed(self):
        for filename, image_format in (("resume.png", "PNG"), ("resume.jpg", "JPEG")):
            with self.subTest(filename=filename):
                text, info = app_module.extract_resume_text(
                    UploadedFile(filename, image_bytes(image_format=image_format)), filename
                )
                self.assertTrue(info["ocr_used"])
                self.assertIn("\n", text)
                self.assertEqual(app_module.infer_resume_name_from_text(text), "Jordan Lee")
                sections = app_module.parse_structured_resume_sections(text)
                self.assertEqual(sections["projects"][0]["title"], "Campus Parking App")
                self.assertEqual(sections["education"][0]["credential"], "Bachelor of Computer Science (Hons)")

    def test_short_ocr_result_is_retried_as_one_text_block(self):
        configs: list[str] = []

        def read(image, config=""):
            configs.append(config)
            return "JORDAN LEE" if "--psm 3" in config else OCR_RESUME_TEXT

        with patch.object(app_module, "pytesseract", SimpleNamespace(image_to_string=read)):
            text = app_module.run_resume_ocr(Image.new("RGB", (800, 1100), "white"))
        self.assertEqual(configs, ["--psm 3", "--psm 6"])
        self.assertIn("Campus Parking App", text)

    def test_unreadable_small_image_explains_the_resolution_problem(self):
        with patch.object(app_module, "pytesseract", SimpleNamespace(image_to_string=lambda image, config="": "Q Phone\nEDUCATION")):
            with self.assertRaisesRegex(ValueError, "only 373 pixels wide"):
                app_module.extract_resume_text(UploadedFile("resume.png", image_bytes(size=(373, 536))), "resume.png")

    def test_broken_image_file_is_reported(self):
        with self.assertRaisesRegex(ValueError, "valid PNG or JPG"):
            app_module.extract_resume_text(UploadedFile("resume.png", b"not an image"), "resume.png")

    def test_oversized_image_is_refused_before_decoding(self):
        with patch.object(app_module, "OCR_MAX_INPUT_PIXELS", 1000 * 1000), patch.object(app_module, "run_resume_ocr") as ocr:
            with self.assertRaisesRegex(ValueError, "under 40 megapixels"):
                app_module.extract_resume_text(UploadedFile("resume.png", image_bytes(size=(1200, 1000))), "resume.png")
        ocr.assert_not_called()


class ScannedPdfOcrTests(unittest.TestCase):
    def scanned_pdf(self) -> bytes:
        buffer = BytesIO()
        Image.new("RGB", (900, 1270), "white").save(buffer, format="PDF")
        return buffer.getvalue()

    def test_pdf_without_a_text_layer_is_read_with_ocr(self):
        with patch.object(app_module, "find_tesseract_command", return_value="tesseract"), patch.object(
            app_module, "configure_tesseract", return_value=None
        ), patch.object(app_module, "run_resume_ocr", return_value=OCR_RESUME_TEXT) as ocr:
            text, info = app_module.extract_pdf_text(BytesIO(self.scanned_pdf()))
        ocr.assert_called_once()
        self.assertTrue(info["ocr_used"])
        self.assertEqual(info["pdf_extraction_mode"], "ocr")
        self.assertIn("Campus Parking App", text)

    def test_scanned_pdf_without_tesseract_keeps_the_scanned_pdf_message_path(self):
        with patch.object(app_module, "find_tesseract_command", return_value=""):
            text, info = app_module.extract_pdf_text(BytesIO(self.scanned_pdf()))
        self.assertEqual(text, "")
        self.assertFalse(info["ocr_used"])


class CandidateNameTests(unittest.TestCase):
    infer_name = staticmethod(app_module.infer_resume_name_from_text)

    def test_two_capital_lines_with_binti_are_one_name(self):
        self.assertEqual(
            self.infer_name("NUR AINA\nBINTI AHMAD\nComputer Science student at an example university."),
            "Nur Aina Binti Ahmad",
        )

    def test_name_line_with_details_after_it(self):
        self.assertEqual(
            self.infer_name("Nur Aisyah binti Kamal (24 years old, Malaysian) | Selangor\nSUMMARY\nData analyst."),
            "Nur Aisyah binti Kamal",
        )
        self.assertEqual(
            self.infer_name("MUHAMMAD ALI BIN OMAR NO 12, JALAN EXAMPLE 3, TAMAN CONTOH\nEDUCATION"),
            "Muhammad Ali Bin Omar",
        )
        self.assertEqual(self.infer_name("Jamie Kaur Email: jamie.kaur@example.com\nSKILLS\nPython"), "Jamie Kaur")

    def test_headings_labels_companies_and_sentences_are_not_names(self):
        text = (
            "Example Mart Hypermarket Holding Berhad, Malaysia\n"
            "Job Category: Help desk\n"
            "Operating System\n"
            "Campnter Scienee undergraduate specialising in data science and analytics.\n"
            "Utilized Java Mail to send automated messages.\n"
            "QQ Adoress\n"
        )
        self.assertEqual(self.infer_name(text), "")

    def test_middle_initial_stays_in_the_name(self):
        self.assertEqual(self.infer_name("NUR A. AZIZ\nEDUCATION\nDiploma in IT"), "Nur A. Aziz")

    def test_ocr_noise_after_an_upper_case_name_is_dropped(self):
        self.assertEqual(self.infer_name("e6013 S >\nTAUFIQ RAHMAN sacs\nBUSINESS ANALYST"), "Taufiq Rahman")
        self.assertEqual(self.infer_name("CURRICULUM VITAE\nSIT] AMINAH BINTI RAHMAN\nKuantan, Pahang"), "Siti Aminah Binti Rahman")

    def test_glued_template_fields_are_split_from_the_name(self):
        self.assertEqual(self.infer_name("JORDAN LEEDevOps ManagerNew York City, NY 10000\nEXPERIENCE"), "Jordan Lee")
        self.assertEqual(self.infer_name("Jordan LeeSenior Developer\nEXPERIENCE"), "Jordan Lee")

    def test_name_after_a_long_sidebar_is_confirmed_by_email_or_file_name(self):
        sidebar = "\n".join(f"Skill item number {index}" for index in range(18))
        text = f"CONTACT\n{sidebar}\nAlex Rivera\nalex.rivera@example.com\nEXPERIENCE\nIT intern."
        self.assertEqual(self.infer_name(text), "Alex Rivera")
        no_email = f"CONTACT\n{sidebar}\nAlex Rivera\nEXPERIENCE\nIT intern."
        self.assertEqual(self.infer_name(no_email), "")
        self.assertEqual(self.infer_name(no_email, ["Alex_Rivera_CV.pdf"]), "Alex Rivera")

    def test_lone_capital_name_line_further_down_is_a_last_resort(self):
        prose = "\n".join(
            f"Student researcher line {index} describing machine learning work and data preparation."
            for index in range(20)
        )
        self.assertEqual(self.infer_name(f"{prose}\nKAI MING WONG\nEXPERIENCE"), "Kai Ming Wong")

    def test_contact_uses_the_file_name_only_to_confirm_a_printed_name(self):
        sidebar = "\n".join(f"Skill item number {index}" for index in range(18))
        contact = app_module.extract_resume_contact(f"{sidebar}\nAlex Rivera\nEXPERIENCE", resume_filename="Alex_Rivera.pdf")
        self.assertEqual(contact["name"], "Alex Rivera")
        contact = app_module.extract_resume_contact(f"{sidebar}\nEXPERIENCE", resume_filename="Alex_Rivera.pdf")
        self.assertEqual(contact["name"], "Candidate Name")


class ContactDetailTests(unittest.TestCase):
    def test_email_wrapped_in_a_narrow_sidebar_is_rejoined(self):
        text = "Contact\nb c s 2 4 0 0 1 @ s t u d e n t . e x a m p l e . e d\nu . m y\n+60 12-345 6789"
        self.assertEqual(app_module.extract_resume_email(app_module.clean_resume_source_text(text)), "bcs24001@student.example.edu.my")

    def test_email_is_not_glued_to_the_address_phone_or_icons(self):
        self.assertEqual(
            app_module.extract_resume_email("Selangor - +6012-3456789 - nurul.aina@example.com -"),
            "nurul.aina@example.com",
        )
        self.assertEqual(app_module.extract_resume_email("6 info@example.com"), "info@example.com")
        self.assertEqual(app_module.extract_resume_email("+6017-4410205+aina.k@example.com"), "aina.k@example.com")
        self.assertEqual(app_module.extract_resume_email("+60 17-3852395 | jamiek0 O@example.com | LinkedIn"), "jamiek0o@example.com")

    def test_phone_skips_doi_years_identity_numbers_and_noise(self):
        text = (
            "Published, DOI: https://doi.org/10.35370/bjost.2026.8.3-03\n"
            "2021 - 2025 2025\n"
            "I.C or Passport : 940401-02-1234\n"
            "rithe ab. rGuciem 239 4435799\n"
            "J (123) 456-7890 Designed a model\n"
        )
        self.assertEqual(app_module.extract_resume_phone(text), "(123) 456-7890")

    def test_phone_beside_the_candidate_email_beats_a_referee_phone(self):
        text = (
            "REFERENCES\nDr Example Referee\n084-367328\nreferee@example.edu.my\n"
            "CONTACT\nkai.wong@example.com\n+60 11-2514 8429\n"
        )
        contact = app_module.extract_resume_contact(text)
        self.assertEqual(contact["email"], "kai.wong@example.com")
        self.assertEqual(contact["phone"], "+60 11-2514 8429")

    def test_links_are_rebuilt_without_the_next_field_or_a_cut_off_copy(self):
        self.assertEqual(
            app_module.compact_resume_link_text("h t t p s: / / w w w . l in k e d in.com / in / k a i - w o n g - 0 a 4 7 /"),
            "https://www.linkedin.com/in/kai-wong-0a47/",
        )
        self.assertEqual(app_module.compact_resume_link_text("linkedin.com 9 Denver, CO"), "linkedin.com")
        self.assertEqual(
            app_module.compact_resume_link_text("LinkedIn: https://www.linkedin.com/in/aina-ex-68 a36 a11 b"),
            "https://www.linkedin.com/in/aina-ex-68a36a11b",
        )
        contact = app_module.extract_resume_contact(
            "Kai Wong\nlinkedin.com/in/kai-wong-0a47b7310", extra_links=["linkedin.com/in/kai-wong-0"]
        )
        self.assertEqual(contact["links"], ["https://linkedin.com/in/kai-wong-0a47b7310"])


class SectionParsingTests(unittest.TestCase):
    def test_split_and_combined_headings_are_recognised(self):
        detect = app_module.detect_resume_section_heading
        self.assertEqual(detect("ABOUT M E"), "summary")
        self.assertEqual(detect("A B O U T  M E"), "summary")
        self.assertEqual(detect("CONTACT INFORMATION"), "other")
        self.assertEqual(detect("INTERNSHIP AVAILABILITY"), "other")
        self.assertEqual(detect("WORKSHOP & TRAINING"), "certifications")
        self.assertEqual(detect("AWARDS & ACHIEVEMENTS"), "achievements")
        self.assertEqual(detect("FEATURED PROJECTS"), "projects")
        self.assertEqual(detect("TRAINING"), "certifications")
        # A wrapped line of an ordinary sentence is not a heading.
        self.assertEqual(detect("Training"), "")

    def test_sidebar_headings_no_longer_leak_into_projects(self):
        text = (
            "KAI WONG\nABOUT M E\nFinal-year Computer Science student.\n"
            "PROJECTS\n"
            "Screening Web Application (FYP) | TypeScript,\nPython\n"
            "Developed an interactive web application for early screening using image and audio tasks.\n"
            "Campus Chatbot (Individual Project) | Python & RAG\n"
            "Developed a localised AI chatbot using Retrieval-\n"
            "Augmented Generation (RAG) to answer questions about the campus.\n"
            "CONTACT INFORMATION\n+60123456789\nkai.wong@example.com\n"
            "INTERNSHIP AVAILABILITY\nMarch 2027 - August 2027\n"
        )
        projects = app_module.parse_structured_resume_sections(text)["projects"]
        self.assertEqual([project["title"] for project in projects], ["Screening Web Application (FYP)", "Campus Chatbot (Individual Project)"])
        self.assertEqual(projects[0]["technologies"], "TypeScript, Python")
        self.assertNotIn("Python.", projects[0]["bullets"])
        self.assertIn("Retrieval-Augmented Generation (RAG)", projects[1]["bullets"][0])

    def test_education_keeps_expected_graduation_language_tests_and_results(self):
        text = (
            "EDUCATION\n"
            "Bachelor of Computer Science (Hons)\nUniversity of Example Malaysia\n"
            "2024 - Present | Expected Graduation: 2027\nCGPA: 3.21\n"
            "STPM (2022 - 2023)\nExample Form Six College, Miri\nCGPA: 2.33 MUET: Band 3.5\n"
            "SPM (2017 - 2021)\nSMK EXAMPLE, MIRI\nResult: 1 A 2 B 5 C\n"
        )
        education = app_module.parse_structured_resume_sections(text)["education"]
        self.assertEqual([entry["credential"] for entry in education], ["Bachelor of Computer Science (Hons)", "STPM", "SPM"])
        self.assertEqual(education[0]["dates"], "2024 - Present")
        self.assertEqual(education[0]["details"], ["Expected graduation: 2027."])
        self.assertEqual(education[1]["grade"], "CGPA: 2.33")
        self.assertEqual(education[1]["details"], ["MUET: Band 3.5."])
        self.assertEqual(education[2]["details"], ["Result: 1 A 2 B 5 C."])

    def test_training_lines_are_grouped_into_whole_items(self):
        parse = app_module.parse_structured_certification_lines
        self.assertEqual(
            parse(
                [
                    "Example Bootcamp",
                    "Developed a food court ordering mobile application.",
                    "Academic Resource Centre-Information Literacy",
                    "Programme",
                    "Advanced Java Programming",
                    "Coursera, 2024",
                ],
                set(),
            ),
            [
                "Example Bootcamp - Developed a food court ordering mobile application.",
                "Academic Resource Centre-Information Literacy Programme",
                "Advanced Java Programming (Coursera, 2024)",
            ],
        )

    def test_side_by_side_columns_read_across_are_rejected(self):
        lines = [
            "Full-Stack Web Development Python for Data Science and",
            "Bootcamp AI",
            "Issuing Institution: Example Academy, Year: 2025",
        ]
        self.assertEqual(app_module.parse_structured_certification_lines(lines, set()), [])


class GeneratedResumeFallbackTests(unittest.TestCase):
    def test_no_projects_are_invented_when_the_resume_has_no_projects_section(self):
        text = (
            "JORDAN LEE\njordan.lee@example.com\n"
            "SUMMARY\nStrong collaborative and problem-solving abilities crafted through project work.\n"
            "EXPERIENCE\n"
            "Software Intern\nExample Labs | Jan 2026 - Present\n"
            "- Built a React dashboard for a web application project used by 40 staff.\n"
            "- Developed Python scripts that reduced manual reporting time by 20%.\n"
            "INTERESTS\nWeb Application Development\nCommunity coding workshops for students.\n"
        )
        draft = app_module.build_generated_resume_payload({}, text, "Software Developer")
        self.assertTrue(draft["sections"]["experience_entries"])
        self.assertEqual(draft["sections"]["projects"], [])

    def test_summary_prose_stays_out_of_education_and_experience(self):
        text = (
            "Student researcher at the University of Example Malaysia and first author of a peer-reviewed paper on\n"
            "explainable machine learning for heart risk prediction in a regional science journal published this year.\n"
            "Experienced in building end-to-end machine learning\n"
            "pipelines, from data preparation and model design to explainability and evaluation.\n"
            "Seeking an internship in AI and data science.\n"
            "University's Students\n"
            "Bachelor of Computer Science\n"
            "University of Example Malaysia, School of Computing, Sibu\n"
            "Built a road safety reporting app with a student team, reaching the competition final.\n"
        )
        analysis = {"job_description_analysis": {"matched_keywords": ["machine learning", "data"]}}
        draft = app_module.build_generated_resume_payload(analysis, text, "Machine Learning Engineer")
        education = " ".join(draft["sections"]["education"])
        self.assertIn("Bachelor of Computer Science", education)
        self.assertNotIn("Student researcher", education)
        self.assertNotIn("University's Students", education)
        experience = " ".join(draft["sections"]["experience_bullets"])
        self.assertNotIn("pipelines, from data preparation", experience)
        self.assertNotIn("Seeking an internship", experience)


if __name__ == "__main__":
    unittest.main()
