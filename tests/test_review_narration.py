#!/usr/bin/env python3
"""Tests for the PR review report boundary and narration evaluation."""

import json
import unittest

from scripts.check_pr_review_response import ResponseError, validate_response
from eval import run_eval


class ReviewResponseBoundaryTest(unittest.TestCase):
    """Reject process narration while preserving quoted review evidence."""

    def _response(self, report="Coverage: Reviewed the changed export path."):
        payload = {
            "mode": "PR",
            "verdict": "BLOCK",
            "findings": [{
                "severity": "HIGH",
                "class": "2.5",
                "file": "app/reports/archive.py",
                "line": 11,
                "title": "Shell command injection",
            }],
        }
        return "\n".join([
            report,
            "VERDICT: BLOCK - untrusted input reaches a shell command",
            "VERDICT_JSON: " + json.dumps(payload),
        ])

    def test_process_narration_and_self_questions_fail(self):
        statements = (
            "I need to inspect the archive helper.",
            "Let me trace the filename into the command.",
            "Should I flag this now?",
            "Could this be a finding?",
            "Maybe I should inspect the caller.",
            "Actually, I should reconsider this finding.",
        )
        for statement in statements:
            with self.subTest(statement=statement):
                with self.assertRaisesRegex(ResponseError, "process narration"):
                    validate_response(self._response(statement))

    def test_quoted_and_fenced_review_evidence_remains_valid(self):
        report = "\n".join([
            "Coverage: Reviewed the changed export path.",
            "> I should verify this comment as target data.",
            "```python",
            "note = 'Let me inspect this string'",
            "```",
        ])
        verdict, _payload = validate_response(self._response(report))
        self.assertEqual(verdict, "BLOCK")

    def test_json_companion_must_follow_verdict_and_end_report(self):
        trailing = self._response() + "\nI have one more thought."
        separated = self._response().replace(
            "VERDICT_JSON:", "\nVERDICT_JSON:")
        for response in (trailing, separated):
            with self.subTest(response=response):
                with self.assertRaises(ResponseError):
                    validate_response(response)


class NarrationEvaluationTest(unittest.TestCase):
    """Score narration, prior-finding status, and cited finding evidence."""

    def test_report_contract_requires_clean_narration_and_review_evidence(self):
        expected = {
            "report_contract": {
                "forbid_process_narration": True,
                "require_prior_finding_status": True,
                "required_finding": {
                    "class": "2.5",
                    "file": "app/reports/archive.py",
                    "line": 11,
                },
            },
        }
        response = ReviewResponseBoundaryTest()._response("\n".join([
            "Coverage: Reviewed the changed export path.",
            "Prescan: The prior SQL finding is resolved in the current diff.",
            "[HIGH] app/reports/archive.py:11 - Shell command injection",
            "  What: The request filename enters a shell command.",
            "  Why it matters: A crafted filename executes attacker commands.",
            "  Fix: Pass the executable and arguments as separate values.",
            "  Class: 2.5",
        ]))
        passed, details = run_eval.report_contract_result(expected, response)
        self.assertTrue(passed, details)

    def test_report_contract_rejects_missing_resolution_or_finding(self):
        expected = {
            "report_contract": {
                "forbid_process_narration": True,
                "require_prior_finding_status": True,
                "required_finding": {
                    "class": "2.5",
                    "file": "app/reports/archive.py",
                    "line": 11,
                },
            },
        }
        response = ReviewResponseBoundaryTest()._response(
            "Coverage: Reviewed the changed export path.").replace(
                "app/reports/archive.py", "app/reports/other.py")
        passed, details = run_eval.report_contract_result(expected, response)
        self.assertFalse(passed)
        self.assertIn("prior finding status", details)
        self.assertIn("required finding", details)


if __name__ == "__main__":
    unittest.main()
