import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _load_module(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


grader = _load_module("smiles_llm_grader_v1", "smiles_llm_grader_v1.py")
manifest = _load_module("benchmark_manifest", "benchmark_manifest.py")
runner_utils = _load_module("benchmark_runner_utils", "benchmark_runner_utils.py")
keygen = _load_module("generate_answer_key", "generate_answer_key.py")


class BenchmarkPromptTests(unittest.TestCase):
    def test_prompt_labels_diagnostic_questions_and_public_score_behavior(self):
        text = (ROOT / "smiles_llm_benchmark_questions.md").read_text(encoding="utf-8")
        self.assertIn("Questions labeled `Diagnostic` are unscored", text)
        self.assertIn("### Q-C1", text)
        self.assertIn("### Q-C10", text)
        banned_word = "".join(["ca", "nary"])
        self.assertNotIn(banned_word, text.lower())

    def test_prompt_mentions_all_public_ids(self):
        text = (ROOT / "smiles_llm_benchmark_questions.md").read_text(encoding="utf-8")
        for qid in manifest.PUBLIC_QUESTION_IDS:
            self.assertIn(f"### {qid}", text)


class ManifestTests(unittest.TestCase):
    def test_public_scored_diagnostic_and_core_sets_are_consistent(self):
        public_ids = set(manifest.PUBLIC_QUESTION_IDS)
        scored_ids = set(manifest.SCORED_QUESTION_IDS)
        diagnostic_ids = set(manifest.DIAGNOSTIC_QUESTION_IDS)
        core_ids = set(manifest.CORE_QUESTION_IDS)
        self.assertFalse(scored_ids & diagnostic_ids)
        self.assertTrue(scored_ids <= public_ids)
        self.assertTrue(diagnostic_ids <= public_ids)
        self.assertTrue(core_ids <= scored_ids)
        self.assertEqual(len(manifest.SCORED_QUESTION_IDS), 24)
        self.assertEqual(len(manifest.DIAGNOSTIC_QUESTION_IDS), 6)

    def test_question_categories_cover_only_scored_questions(self):
        categorized = {qid for values in manifest.QUESTION_CATEGORIES.values() for qid in values}
        self.assertEqual(categorized, set(manifest.SCORED_QUESTION_IDS))
        self.assertFalse(categorized & set(manifest.DIAGNOSTIC_QUESTION_IDS))

    def test_percent_for_questions_ignores_diagnostics_when_ids_excluded(self):
        per_question = {
            "Q1": {"earned": 2.0, "max": 2.0},
            "Q2": {"earned": 0.0, "max": 2.0},
            "Q-C1": {"earned": 99.0, "max": 99.0},
        }
        self.assertEqual(manifest.percent_for_questions(per_question, ["Q1", "Q2"]), 50.0)


class GraderBehaviorTests(unittest.TestCase):
    def test_public_grade_contains_no_answer_key(self):
        grade = grader.grade({"answers": []})
        self.assertNotIn("answer_key", grade)
        self.assertIn("per_question", grade)

    def test_diagnostic_questions_do_not_affect_public_score(self):
        base_grade = grader.grade({"answers": []})
        diagnostic_only_submission = {
            "answers": [
                {"id": "Q-C1", "answer": {"smiles": "c1ccc(cc1)C2CCC(NC(=O)c3ccccc3)CC2O"}},
                {"id": "Q-C2", "answer": {"smiles": "c1cc[nH]c(c1)[C@H](C)C"}},
            ]
        }
        diagnostic_grade = grader.grade(diagnostic_only_submission)
        self.assertEqual(base_grade["score"], diagnostic_grade["score"])
        self.assertEqual(base_grade["max_points"], diagnostic_grade["max_points"])
        self.assertNotIn("Q-C1", diagnostic_grade["per_question"])

    def test_public_key_marks_diagnostics_unscored(self):
        public_key = grader.compute_public_answer_key()
        self.assertEqual(public_key["Q-C1"]["status"], "unscored diagnostic")
        self.assertIn("public_reference_answer", public_key["Q-C1"])
        self.assertEqual(public_key["Q1"]["status"], "trusted answer withheld")


class RunnerUtilsTests(unittest.TestCase):
    def test_single_turn_result_reports_invalid_json_without_retry(self):
        result = runner_utils.build_single_turn_result("not json", ["Q1", "Q2"])
        self.assertFalse(result["parse_ok"])
        self.assertEqual(result["missing_ids_turn1"], ["Q1", "Q2"])
        self.assertFalse(result["retry_used"])

    def test_family_paths_and_model_slug(self):
        paths = _load_module("benchmark_paths", "benchmark_paths.py")
        self.assertEqual(paths.model_slug("claude-sonnet-4-6"), "claude-sonnet-4-6")
        self.assertEqual(paths.model_slug("gpt-5.4-nano"), "gpt-5-4-nano")
        run_dir = paths.run_directory(ROOT / "outputs", "claude", "claude-haiku-4-5", "20260417T000000Z")
        self.assertEqual(
            run_dir,
            ROOT / "outputs" / "claude" / "claude-haiku-4-5" / "20260417T000000Z",
        )

    def test_public_grade_sanitizer_keeps_only_score_fields(self):
        sanitized = runner_utils.sanitize_public_grade_result(
            {
                "score": 4.0,
                "max_points": 8.0,
                "percent": 50.0,
                "per_question": {
                    "Q1": {"earned": 1.0, "max": 3.0, "detail": {"expected": 168}},
                },
                "answer_key": {"Q1": {"heavy_atoms": 168}},
            }
        )
        self.assertEqual(
            sanitized,
            {
                "score": 4.0,
                "max_points": 8.0,
                "percent": 50.0,
                "per_question": {"Q1": {"earned": 1.0, "max": 3.0}},
            },
        )

    def test_run_artifact_writer_sends_raw_files_only_to_private_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            public_dir = tmp_path / "outputs" / "openai" / "model" / "stamp"
            private_dir = tmp_path / ".benchmark_private" / "runs" / "openai" / "model" / "stamp"
            runner_utils.write_run_artifacts(
                public_dir=public_dir,
                private_dir=private_dir,
                public_grade={"score": 1.0, "max_points": 2.0, "percent": 50.0, "per_question": {"Q1": {"earned": 1.0, "max": 2.0}}},
                summary={"score": 1.0, "max_points": 2.0, "percent": 50.0},
                meta={"model": "gpt-test"},
                struggle={"losses_ranked": []},
                private_payload={
                    "model_response_turn1_raw.txt": "raw response",
                    "model_response_turn1_trace.json": [{"type": "content"}],
                    "model_submission_final.json": {"answers": []},
                    "usage_turn1.json": {"output_tokens": 12},
                },
                trusted_payload=None,
            )
            self.assertTrue((public_dir / "summary.json").exists())
            self.assertTrue((public_dir / "grade_result.json").exists())
            self.assertTrue((public_dir / "run_meta.json").exists())
            self.assertFalse((public_dir / "struggle_report.json").exists())
            self.assertFalse((public_dir / "model_response_turn1_raw.txt").exists())
            self.assertTrue((private_dir / "model_response_turn1_raw.txt").exists())
            self.assertTrue((private_dir / "model_submission_final.json").exists())
            self.assertTrue((private_dir / "struggle_report.json").exists())

    def test_secret_loader_activates_only_when_file_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(runner_utils.load_secret_benchmark_module(root))
            private_dir = root / ".benchmark_private"
            private_dir.mkdir()
            (private_dir / "secret_benchmark.py").write_text(
                "def grade_submission(payload):\n"
                "    return {'score': 9, 'max_points': 9, 'percent': 100.0}\n",
                encoding="utf-8",
            )
            module = runner_utils.load_secret_benchmark_module(root)
            self.assertIsNotNone(module)
            self.assertEqual(module.grade_submission({"answers": []})["score"], 9)

    def test_diagnostic_match_report_flags_exact_and_canonical_matches(self):
        public_key = grader.compute_public_answer_key()
        report = runner_utils.build_diagnostic_match_report(
            {
                "Q-C1": {"smiles": public_key["Q-C1"]["public_reference_answer"]["smiles"]},
                "Q-C10": {"smiles_list": public_key["Q-C10"]["public_reference_answer"]["smiles_list"]},
            },
            public_key,
            grader.canon_or_none,
            grader.canon_list_sorted,
        )
        self.assertTrue(report["Q-C1"]["exact_match"])
        self.assertTrue(report["Q-C1"]["canonical_match"])
        self.assertTrue(report["Q-C10"]["exact_match"])


class AnswerKeyTests(unittest.TestCase):
    def test_public_answer_key_text_hides_scored_answers_and_mentions_diagnostics(self):
        public_key = grader.compute_public_answer_key()
        text = keygen.render_answer_key_text(public_key)
        self.assertIn("Trusted scoring material is withheld", text)
        self.assertIn("unscored diagnostic", text)
        self.assertNotIn('"heavy_atoms": 168', text)


if __name__ == "__main__":
    unittest.main()
