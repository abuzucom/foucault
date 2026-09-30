#!/usr/bin/env python3
"""Regression coverage for immutable review-policy and input-size controls."""

import sys
import unittest
from pathlib import Path

from ci import build_pr_case


REPO_ROOT = Path(__file__).resolve().parents[1]
REVIEW_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "security-review.yml"


class ReviewHardeningTest(unittest.TestCase):
    """Verify policy loading and diff capture fail closed."""

    def test_audit_ref_requires_a_full_commit_sha(self):
        workflow = REVIEW_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("const auditRefPattern = /^[0-9a-f]{40}$/;", workflow)
        self.assertIn("audit policy revision is invalid", workflow)

    def test_bounded_diff_reader_rejects_oversized_output(self):
        command = [
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write(b'x' * 32)",
        ]
        with self.assertRaises(RuntimeError):
            build_pr_case._read_bounded_stdout(command, 16)


if __name__ == "__main__":
    unittest.main()
