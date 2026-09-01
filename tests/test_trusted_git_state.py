#!/usr/bin/env python3
"""Tests for bounded and sanitized Git state output."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "read_git_state.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import read_git_state


class GitStateTextTest(unittest.TestCase):
    """Untrusted Git values become bounded printable ASCII."""

    def test_control_characters_are_rendered(self):
        rendered = read_git_state.sanitize_text("safe\x1b[31m\n", limit=64)
        self.assertEqual(rendered, r"safe\x1b[31m\n")

    def test_long_values_are_bounded(self):
        rendered = read_git_state.sanitize_text("x" * 20, limit=8)
        self.assertEqual(rendered, "xxxxx...")

    def test_url_credentials_are_redacted(self):
        url = "https://account:secret@example.com/repository.git"
        self.assertEqual(
            read_git_state.redact_remote_url(url),
            "https://<redacted>@example.com/repository.git",
        )

    def test_scp_style_account_is_redacted(self):
        url = "account@example.com:organization/repository.git"
        self.assertEqual(
            read_git_state.redact_remote_url(url),
            "<redacted>@example.com:organization/repository.git",
        )

    def test_scp_style_account_before_path_at_sign_is_redacted(self):
        url = "user@host:path/with@symbol"
        self.assertEqual(
            read_git_state.redact_remote_url(url),
            "<redacted>@host:path/with@symbol",
        )


class GitStateParsingTest(unittest.TestCase):
    """Structured state excludes raw paths and diagnostics."""

    def test_detached_branch_has_no_branch_name(self):
        state = read_git_state.parse_branch(returncode=1, stdout="")
        self.assertEqual(
            state,
            {"branch": None, "detached": True},
        )

    def test_status_reports_flags_without_paths(self):
        output = "# branch.head feat/example\n1 .M N... path\n? new-file\n"
        state = read_git_state.parse_status(output)
        self.assertEqual(
            state,
            {"dirty": True, "tracked_changes": True, "untracked": True},
        )

    def test_revision_rejects_unexpected_output(self):
        with self.assertRaises(ValueError):
            read_git_state.parse_revision("not-a-revision\n")


class GitStateCliTest(unittest.TestCase):
    """The command reads live state through the trusted Git path."""

    def test_branch_operation_returns_json(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "branch"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads(result.stdout)
        self.assertEqual(state["operation"], "branch")
        self.assertIsInstance(state["detached"], bool)
        self.assertNotIn("stderr", state)


if __name__ == "__main__":
    unittest.main()
