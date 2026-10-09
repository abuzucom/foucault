#!/usr/bin/env python3
"""Verify label and environment gates for fork pull request reviews."""

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CALLER_PATH = REPO_ROOT / ".github" / "workflows" / "security-review-pr.yml"
COMPLIANCE_PATH = REPO_ROOT / ".github" / "workflows" / "immutable-conflict-check.yml"
REVIEW_PATH = REPO_ROOT / ".github" / "workflows" / "security-review.yml"
DOC_PATH = REPO_ROOT / "docs" / "pr-security-review.md"


class ForkReviewGateTest(unittest.TestCase):
    """The caller gates fork reviews before the protected model job."""

    def setUp(self):
        self.caller = CALLER_PATH.read_text(encoding="utf-8")
        self.compliance = COMPLIANCE_PATH.read_text(encoding="utf-8")
        self.review = REVIEW_PATH.read_text(encoding="utf-8")
        self.docs = DOC_PATH.read_text(encoding="utf-8")

    def test_label_event_retries_only_approved_fork_reviews(self):
        self.assertIn("pull_request_target:", self.compliance)
        self.assertIn(
            "types: [opened, synchronize, reopened, ready_for_review, edited, "
            "converted_to_draft, labeled]",
            self.compliance,
        )
        self.assertIn("workflow_run:", self.caller)
        self.assertIn('label.name === "safe-to-review"', self.caller)
        self.assertIn("fork_review_approved", self.caller)
        self.assertIn("compliance_passed", self.caller)

    def test_same_repository_path_keeps_the_default_review_job(self):
        self.assertIn("fork_review:", self.review)
        self.assertIn("default: false", self.review)
        self.assertIn("if: inputs.fork_review != true", self.review)
        self.assertIn("if: inputs.fork_review == true", self.review)
        self.assertIn("fork_review: false", self.caller)

    def test_fork_job_waits_for_environment_approval(self):
        self.assertIn("environment: fork-review", self.review)
        self.assertIn("steps: *security_review_steps", self.review)
        self.assertIn("steps: &security_review_steps", self.review)
        self.assertIn("MODEL_API_KEY: ${{ secrets.MODEL_API_KEY }}", self.review)
        self.assertIn("required reviewers", self.docs.lower())
        self.assertIn("fork-review", self.docs)

    def test_fork_review_requires_the_label_and_passed_compliance(self):
        self.assertIn("outputs.fork_review_approved == 'true'", self.caller)
        self.assertIn("outputs.compliance_passed == 'true'", self.caller)
        self.assertIn("fork_review: true", self.caller)
        self.assertIn("safe-to-review", self.caller)


if __name__ == "__main__":
    unittest.main()
