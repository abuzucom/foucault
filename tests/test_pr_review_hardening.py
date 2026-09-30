#!/usr/bin/env python3
"""Regression coverage for immutable review-policy and input-size controls."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ci import build_pr_case


REPO_ROOT = Path(__file__).resolve().parents[1]
REVIEW_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "security-review.yml"


EXPECTED_AUDIT_REF_PATTERN = r"^[0-9a-f]{40}$"


def _validate_audit_ref(audit_ref: str) -> None:
    """Validate audit policy revision against the independent specification."""
    node_bin = shutil.which("node")
    if node_bin:
        script = (
            "const pattern = new RegExp(process.argv[1]);\n"
            "const ref = process.argv[2];\n"
            "if (!pattern.test(ref || '')) {\n"
            "  console.error('audit policy revision is invalid');\n"
            "  process.exit(1);\n"
            "}\n"
        )
        result = subprocess.run(
            [node_bin, "-e", script, EXPECTED_AUDIT_REF_PATTERN, audit_ref],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            if "audit policy revision is invalid" in result.stderr:
                raise ValueError("audit policy revision is invalid")
            raise RuntimeError(f"node error: {result.stderr}")
        return
    if not re.fullmatch(EXPECTED_AUDIT_REF_PATTERN, audit_ref or ""):
        raise ValueError("audit policy revision is invalid")


class ReviewHardeningTest(unittest.TestCase):
    """Verify policy loading and diff capture fail closed."""

    def test_audit_ref_requires_a_full_commit_sha(self):
        workflow = REVIEW_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("const auditRefPattern = /^[0-9a-f]{40}$/;", workflow)
        self.assertIn("audit policy revision is invalid", workflow)

    def test_workflow_audit_ref_pattern_matches_expected_specification(self):
        """Verify the workflow regex matches the independent specification."""
        workflow = REVIEW_WORKFLOW.read_text(encoding="utf-8")
        pattern_match = re.search(r"const auditRefPattern = /([^/]+)/;", workflow)
        self.assertIsNotNone(pattern_match)
        self.assertEqual(pattern_match.group(1), EXPECTED_AUDIT_REF_PATTERN)

    def test_audit_ref_validation_behavior(self):
        """Verify audit ref pattern accepts full commit SHA and rejects others."""
        valid_sha = "0123456789abcdef0123456789abcdef01234567"
        self.assertIsNone(_validate_audit_ref(valid_sha))

        invalid_refs = [
            "",
            "main",
            "v1.0.0",
            "0123456789abcdef0123456789abcdef0123456",
            "0123456789abcdef0123456789abcdef012345678",
            "0123456789ABCDEF0123456789ABCDEF01234567",
            "0123456789abcdef0123456789abcdef0123456g",
            " " + valid_sha,
            valid_sha + "\n",
            "; rm -rf /",
        ]
        for invalid_ref in invalid_refs:
            with self.subTest(invalid_ref=invalid_ref):
                with self.assertRaises(ValueError) as context:
                    _validate_audit_ref(invalid_ref)
                self.assertIn("audit policy revision is invalid", str(context.exception))

    def test_bounded_diff_reader_rejects_oversized_output(self):
        command = [
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write(b'x' * 32)",
        ]
        with self.assertRaises(RuntimeError):
            build_pr_case._read_bounded_stdout(command, 16)

    def test_bounded_diff_reader_times_out(self):
        """Verify bounded diff reader aborts commands exceeding timeout."""
        command = [
            sys.executable,
            "-c",
            "import time; time.sleep(2)",
        ]
        with self.assertRaises(RuntimeError) as context:
            build_pr_case._read_bounded_stdout(command, 16, timeout=0.1)
        self.assertIn("timed out", str(context.exception))

    def test_build_case_validates_git_revisions(self):
        """Verify build_case rejects invalid revision parameters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            event_path = Path(temp_dir) / "event.json"
            event_path.write_text(
                json.dumps({
                    "pull_request": {
                        "title": "Fix title",
                        "body": "Fix body",
                        "base": {"sha": "not-a-valid-sha"},
                        "head": {"sha": "also-not-valid"},
                    }
                }),
                encoding="utf-8",
            )
            saved_env = os.environ.copy()
            try:
                os.environ["EVENT_PATH"] = str(event_path)
                os.environ.pop("BASE_SHA", None)
                os.environ.pop("HEAD_SHA", None)
                with self.assertRaises(RuntimeError) as context:
                    build_pr_case.build_case()
                self.assertIn("pull request revisions are invalid", str(context.exception))

                os.environ["BASE_SHA"] = "invalid-base-sha"
                os.environ["HEAD_SHA"] = "0123456789abcdef0123456789abcdef01234567"
                with self.assertRaises(RuntimeError) as context:
                    build_pr_case.build_case()
                self.assertIn("pull request revisions are invalid", str(context.exception))
            finally:
                os.environ.clear()
                os.environ.update(saved_env)


if __name__ == "__main__":
    unittest.main()
