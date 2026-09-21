import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from scripts import audit_diff_report
from scripts.check_audit_policy import find_violations


class AuditPolicyTest(unittest.TestCase):
    def test_current_policy_passes(self):
        self.assertEqual(find_violations(Path("AUDIT.md")), [])

    def test_missing_required_control_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AUDIT.md"
            path.write_text("## 0. Review Modes\n", encoding="ascii")
            findings = find_violations(path)
        self.assertTrue(any("missing required" in item for item in findings))

    def test_long_prose_line_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AUDIT.md"
            path.write_text("x" * 121, encoding="ascii")
            findings = find_violations(path)
        self.assertTrue(any("exceeds" in item for item in findings))

    def test_long_table_row_is_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AUDIT.md"
            path.write_text("| " + "x" * 130, encoding="ascii")
            findings = find_violations(path)
        self.assertFalse(any("exceeds" in item for item in findings))

    def test_non_ascii_policy_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AUDIT.md"
            path.write_bytes("cafe\u00e9".encode("utf-8"))
            findings = find_violations(path)
        self.assertTrue(any("ASCII" in item for item in findings))

    def test_crlf_policy_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AUDIT.md"
            path.write_bytes(b"## 0. Review Modes\r\n")
            findings = find_violations(path)
        self.assertTrue(any("LF" in item for item in findings))

    def test_oversized_policy_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AUDIT.md"
            path.write_bytes(b"x" * (32 * 1024 + 1))
            findings = find_violations(path)
        self.assertTrue(any("exceeds" in item for item in findings))

    def test_duplicate_heading_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AUDIT.md"
            path.write_text("## Duplicate\n## Duplicate\n", encoding="ascii")
            findings = find_violations(path)
        self.assertTrue(any("duplicate" in item for item in findings))

    def test_git_show_rejects_non_object_id(self):
        with mock.patch.object(audit_diff_report.trusted_git, "run_git") as runner:
            result = audit_diff_report.git_show("--output=bad")
        self.assertIsNone(result)
        runner.assert_not_called()

    def test_git_show_uses_trusted_git_and_end_of_options(self):
        completed = mock.Mock(stdout="policy\n")
        with mock.patch.object(
            audit_diff_report.trusted_git, "run_git", return_value=completed
        ) as runner:
            result = audit_diff_report.git_show("a" * 40)
        self.assertEqual(result, "policy\n")
        runner.assert_called_once_with(
            Path.cwd(), ["show", "--end-of-options", "a" * 40 + ":AUDIT.md"],
            check=True,
        )

    def test_git_show_reports_missing_revision(self):
        error = audit_diff_report.subprocess.CalledProcessError(128, "git")
        with mock.patch.object(
            audit_diff_report.trusted_git, "run_git", side_effect=error
        ):
            result = audit_diff_report.git_show("b" * 40)
        self.assertIsNone(result)

    def test_audit_diff_report_runs_as_script(self):
        revision = audit_diff_report.trusted_git.run_git(
            Path.cwd(), ["rev-parse", "HEAD"], check=True
        ).stdout.strip()
        with tempfile.TemporaryDirectory() as directory:
            summary = Path(directory) / "summary.md"
            environment = dict(os.environ)
            environment.update(
                BASE_SHA=revision,
                HEAD_SHA=revision,
                GITHUB_STEP_SUMMARY=str(summary),
            )
            result = subprocess.run(
                [sys.executable, "scripts/audit_diff_report.py"],
                cwd=Path.cwd(),
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
