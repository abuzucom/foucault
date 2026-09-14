#!/usr/bin/env python3
"""Tests for trusted GitHub CLI lookup and delivery-safe output."""
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPOSITORY_ROOT / "scripts" / "trusted_gh.py"
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import trusted_gh


class AccountParsingTest(unittest.TestCase):
    """Authenticated account output stays bounded and structured."""

    def test_numeric_id_and_login_parse(self):
        account = trusted_gh.parse_account("1234567\toctocat\n")
        self.assertEqual(account, {"id": 1234567, "login": "octocat"})

    def test_malformed_account_output_fails(self):
        values = ("", "id\toctocat", "1\tbad/login", "1\toctocat\textra")
        for value in values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    trusted_gh.parse_account(value)

    def test_account_output_has_a_bound(self):
        with self.assertRaises(ValueError):
            trusted_gh.parse_account("1\t" + "a" * 300)


class ExecutableLookupTest(unittest.TestCase):
    """Repository-local programs cannot replace GitHub CLI."""

    def test_repository_gh_is_excluded(self):
        environment = {"PATH": str(REPOSITORY_ROOT / "scripts")}
        with patch.dict(os.environ, environment, clear=False):
            with patch.object(
                    trusted_gh, "_candidate_names",
                    return_value=("trusted_gh.py",)):
                with self.assertRaises(FileNotFoundError):
                    trusted_gh.resolve_gh(REPOSITORY_ROOT)


class EnvironmentSafetyTest(unittest.TestCase):
    """The wrapper removes only the managed proxy placeholder."""

    def test_managed_proxy_is_removed(self):
        with patch.dict(os.environ, {
            "HTTP_PROXY": "http://127.0.0.1:9",
            "HTTPS_PROXY": "https://proxy.example:443",
        }, clear=False):
            environment = trusted_gh._safe_environment(REPOSITORY_ROOT)
        self.assertNotIn("HTTP_PROXY", environment)
        self.assertEqual(environment["HTTPS_PROXY"], "https://proxy.example:443")


class RunnerSafetyTest(unittest.TestCase):
    """The runner uses argument arrays and external execution directories."""

    def test_runner_does_not_build_a_shell_command(self):
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return subprocess.CompletedProcess(command, 0, "", "")

        with patch.object(trusted_gh, "resolve_gh", return_value="C:\\Tools\\gh.exe"):
            with patch.object(trusted_gh, "_safe_directory", return_value=Path("C:\\Temp")):
                result = trusted_gh.run_gh(
                    REPOSITORY_ROOT,
                    ["pr", "view", "45", "--json", "isDraft"],
                    runner=runner,
                )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(calls[0][0], [
            "C:\\Tools\\gh.exe", "pr", "view", "45", "--json", "isDraft",
        ])
        self.assertNotIn("shell", calls[0][1])


class OutputSafetyTest(unittest.TestCase):
    """Sensitive output requests and failure messages stay bounded."""

    def test_token_output_is_denied(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "run", "auth", "token"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("token output is denied", result.stderr)

    def test_proxy_failures_have_a_safe_category(self):
        self.assertEqual(
            trusted_gh._classify_failure("proxy connection refused"),
            "proxy failure",
        )

    def test_error_redacts_secret_values(self):
        message = trusted_gh._safe_error(ValueError("token=secret-value"))
        self.assertEqual(message, "token=<redacted>")


class TrustedRunnerSafetyTest(unittest.TestCase):
    """The wrapper rejects destructive forge commands before account lookup."""

    def test_repository_deletion_denies(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "run", "repo", "delete", "OWNER/REPO"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("removes work", result.stderr)

    def test_literal_newline_escape_in_pr_body_is_rejected(self):
        result = subprocess.run(
            [
                sys.executable, str(SCRIPT), "run", "pr", "edit", "45",
                "--body", "line1\\n\\nline2",
            ],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("literal escape text", result.stderr)


if __name__ == "__main__":
    unittest.main()
