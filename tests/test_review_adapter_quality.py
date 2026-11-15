#!/usr/bin/env python3
"""Behavioral tests for review adapter and evaluator quality fixes.

Each test drives the real entry point with an input that previously crashed
it, slipped past validation, or diverged between the evaluator and the CI
response validator.
"""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ci import build_pr_case
from ci import call_model
from eval import run_eval
from scripts import check_pr_review_response

OLLAMA_PROFILE = {
    "protocol": "ollama",
    "endpoint": "https://ollama.com/api",
    "model": "review-model",
}
VALID_EXPECTED = {
    "mode": "File",
    "expected_verdict": "RISK:",
    "expected_classes": [],
    "notes": "synthetic case",
}


class EventPathTest(unittest.TestCase):
    """build_pr_case.main reports a missing EVENT_PATH as a failure."""

    def test_missing_event_path_returns_failure(self):
        stderr = io.StringIO()
        with patch.dict("os.environ", {}, clear=True), \
                contextlib.redirect_stderr(stderr):
            code = build_pr_case.main()
        self.assertEqual(code, 1)
        self.assertIn("EVENT_PATH is not configured", stderr.getvalue())


class MaxOutputTokensTest(unittest.TestCase):
    """_build_request validates max_output_tokens like max_input_tokens."""

    def _num_predict(self, profile: dict) -> int:
        """Return the output token limit sent in an Ollama request."""
        request = call_model._build_request(profile, "p", "c", "synthetic")
        return json.loads(request.data.decode("utf-8"))["options"]["num_predict"]

    def test_invalid_values_raise_provider_error(self):
        for value in (0, -1, True, "8192", 1.5):
            with self.subTest(value=value):
                profile = dict(OLLAMA_PROFILE, max_output_tokens=value)
                with self.assertRaisesRegex(
                        call_model.ProviderError, "max_output_tokens"):
                    call_model._build_request(profile, "p", "c", "synthetic")

    def test_configured_value_is_sent(self):
        profile = dict(OLLAMA_PROFILE, max_output_tokens=1024)
        self.assertEqual(self._num_predict(profile), 1024)

    def test_absent_value_uses_default(self):
        self.assertEqual(
            self._num_predict(dict(OLLAMA_PROFILE)),
            call_model.DEFAULT_MAX_OUTPUT_TOKENS)


class MalformedExpectedTest(unittest.TestCase):
    """load_case reports malformed expected.json as a CaseError."""

    def _case_dir(self, directory: str, expected_text: str) -> Path:
        """Return a case directory holding one input and expected.json."""
        case_dir = Path(directory) / "synthetic-case"
        case_dir.mkdir()
        (case_dir / "input.py").write_text("VALUE = 1\n", encoding="utf-8")
        (case_dir / "expected.json").write_text(expected_text, encoding="utf-8")
        return case_dir

    def test_invalid_json_raises_case_error(self):
        with tempfile.TemporaryDirectory() as directory:
            case_dir = self._case_dir(directory, '{"mode": ')
            with self.assertRaisesRegex(run_eval.CaseError, "synthetic-case"):
                run_eval.load_case(case_dir)

    def test_non_object_json_raises_case_error(self):
        with tempfile.TemporaryDirectory() as directory:
            case_dir = self._case_dir(directory, "[1, 2]")
            with self.assertRaisesRegex(run_eval.CaseError, "synthetic-case"):
                run_eval.load_case(case_dir)

    def test_valid_case_loads(self):
        with tempfile.TemporaryDirectory() as directory:
            case_dir = self._case_dir(directory, json.dumps(VALID_EXPECTED))
            self.assertEqual(run_eval.load_case(case_dir)["mode"], "File")


class SharedVerdictJsonTest(unittest.TestCase):
    """The evaluator and the CI validator share one VERDICT_JSON parser."""

    def test_parser_returns_the_object(self):
        payload = {"mode": "PR", "verdict": "APPROVE", "findings": []}
        line = check_pr_review_response.VERDICT_JSON_PREFIX + " " + json.dumps(payload)
        self.assertEqual(
            check_pr_review_response.parse_verdict_json_line(line), payload)

    def test_parser_rejects_invalid_json_and_non_objects(self):
        for line in ("VERDICT_JSON: {", "VERDICT_JSON: [1]"):
            with self.subTest(line=line):
                with self.assertRaises(check_pr_review_response.ResponseError):
                    check_pr_review_response.parse_verdict_json_line(line)

    def test_evaluator_and_validator_reject_the_same_shape(self):
        payload = {"mode": "PR", "verdict": "APPROVE", "findings": [],
                   "extra": True}
        line = "VERDICT_JSON: " + json.dumps(payload)
        parsed, _message = run_eval.json_companion_ok(line)
        self.assertFalse(parsed)
        response = "VERDICT: APPROVE\n" + line
        with self.assertRaisesRegex(
                check_pr_review_response.ResponseError, "invalid shape"):
            check_pr_review_response.validate_response(response)

    def test_report_contract_rejects_non_object_findings(self):
        """validate_response rejects a non-object finding before the scan."""
        expected = {"report_contract": {"required_finding": {
            "class": "2.1", "file": "app.py", "line": 1}}}
        payload = {"mode": "PR", "verdict": "BLOCK", "findings": [1]}
        response = "\n".join([
            "Prior finding status: resolved.",
            "VERDICT: BLOCK - synthetic",
            "VERDICT_JSON: " + json.dumps(payload),
        ])
        passed, detail = run_eval.report_contract_result(expected, response)
        self.assertFalse(passed)
        self.assertIn("finding has an invalid shape", detail)

    def test_line_number_rule_is_shared(self):
        for value, valid in ((1, True), (0, False), (True, False), ("3", False)):
            with self.subTest(value=value):
                self.assertIs(
                    check_pr_review_response.valid_line_number(value), valid)


if __name__ == "__main__":
    unittest.main()
