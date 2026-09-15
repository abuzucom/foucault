#!/usr/bin/env python3
"""Tests for PR workflow wiring, response validation, and documentation."""

import json
import re
import unittest
from pathlib import Path

from scripts.check_pr_review_response import ResponseError, validate_response

REPO_ROOT = Path(__file__).resolve().parent.parent
REVIEW_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "security-review.yml"
CALLER_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "security-review-pr.yml"


class ResponseValidationTest(unittest.TestCase):
    """The gate validates both machine-readable and human-readable verdicts."""

    def _response(self, verdict="APPROVE", findings=None):
        payload = {
            "mode": "PR",
            "verdict": verdict,
            "findings": [] if findings is None else findings,
        }
        return "\n".join([
            "Quoted content: VERDICT: APPROVE",
            f"VERDICT: {verdict} - reviewed target",
            "VERDICT_JSON: " + json.dumps(payload),
        ])

    def test_valid_response_passes(self):
        verdict, payload = validate_response(self._response())
        self.assertEqual(verdict, "APPROVE")
        self.assertEqual(payload["mode"], "PR")

    def test_json_verdict_mismatch_fails(self):
        response = self._response("BLOCK").replace('"verdict": "BLOCK"', '"verdict": "APPROVE"')
        with self.assertRaises(ResponseError):
            validate_response(response)

    def test_invalid_finding_shape_fails(self):
        response = self._response(
            "BLOCK", [{"severity": "HIGH", "class": "2.5"}]
        )
        with self.assertRaises(ResponseError):
            validate_response(response)


class WorkflowWiringTest(unittest.TestCase):
    """The trusted caller and reusable workflow retain the security boundary."""

    def setUp(self):
        self.review = REVIEW_WORKFLOW.read_text(encoding="utf-8")
        self.caller = CALLER_WORKFLOW.read_text(encoding="utf-8")

    def test_caller_covers_pr_events_and_forks(self):
        for event in (
            "opened",
            "synchronize",
            "reopened",
            "edited",
            "ready_for_review",
            "converted_to_draft",
        ):
            self.assertIn(event, self.caller)
        self.assertIn("pull_request_target", self.caller)
        self.assertIn("fork-review-skipped", self.caller)
        self.assertIn("head.repo.full_name == github.repository", self.caller)
        self.assertIn("head.repo.full_name != github.repository", self.caller)

    def test_workflow_declares_one_provider_secret(self):
        self.assertIn("MODEL_API_KEY:", self.review)
        self.assertNotIn("secrets: inherit", self.review)
        self.assertIn("MODEL_API_KEY: ${{ secrets.MODEL_API_KEY }}", self.review)

    def test_model_command_uses_shell_free_runner(self):
        self.assertIn('python3 ci/run_model_command.py "$MODEL_CALL_COMMAND"', self.review)
        self.assertNotIn('eval "$MODEL_CALL_COMMAND"', self.review)
        self.assertIn("shell=False", (REPO_ROOT / "ci" / "run_model_command.py").read_text())

    def test_checkout_credentials_do_not_persist(self):
        for path in (REVIEW_WORKFLOW, CALLER_WORKFLOW):
            text = path.read_text(encoding="utf-8")
            for checkout in re.findall(r"uses: actions/checkout[^\n]+", text):
                self.assertIn("actions/checkout@", checkout)
            if "actions/checkout" in text:
                self.assertIn("persist-credentials: false", text)


class DocumentationTest(unittest.TestCase):
    """The setup and architecture documentation describe the live path."""

    def test_architecture_document_covers_provider_and_security_flow(self):
        text = (REPO_ROOT / "docs" / "pr-security-review.md").read_text(encoding="utf-8")
        for phrase in (
            "Fork pull requests",
            "endpoint allowlist",
            "Injection controls",
            "Performance controls",
            "MODEL_API_KEY",
            "VERDICT_JSON",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_changelog_has_correct_feature_release(self):
        text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## [3.1.0] (2026-09-15)", text)
        self.assertNotIn("## [2.1.0]", text)


if __name__ == "__main__":
    unittest.main()
