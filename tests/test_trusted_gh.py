#!/usr/bin/env python3
"""Tests for trusted GitHub CLI lookup and delivery-safe output."""
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
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

    def test_command_error_output_redacts_secrets_and_controls(self):
        message = trusted_gh._safe_output("token=secret-value\nstatus: failed\x1b[31m")
        self.assertEqual(message, "token=<redacted>\nstatus: failed?[31m")

    def test_runner_decodes_malformed_output_with_utf8_replacement(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(trusted_gh, "resolve_gh", return_value=sys.executable):
                with patch.object(trusted_gh, "_safe_directory", return_value=root):
                    result = trusted_gh.run_gh(
                        root,
                        ["-c", "import sys; sys.stdout.buffer.write(bytes([129]))"],
                    )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "\ufffd")


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

    def test_attached_newline_escape_in_pr_body_is_rejected(self):
        result = subprocess.run(
            [
                sys.executable, str(SCRIPT), "run", "pr", "edit", "45",
                "--body=line1\\n\\nline2",
            ],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("literal escape text", result.stderr)

    def test_auth_status_short_token_flag_is_denied(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "run", "auth", "status", "-t"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("token output is denied", result.stderr)

    def test_auth_status_attached_token_flag_is_denied(self):
        result = subprocess.run(
            [
                sys.executable, str(SCRIPT), "run", "auth", "status",
                "--show-token=true",
            ],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("token output is denied", result.stderr)

    def test_auth_status_short_flag_bundle_is_denied(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "run", "auth", "status", "-at"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("token output is denied", result.stderr)


class RepositoryContextTest(unittest.TestCase):
    """Repository-bound commands receive safe explicit context."""

    def write_config(self, root, remote):
        git_dir = root / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text(
            "ref: refs/heads/feature/test\n", encoding="utf-8"
        )
        (git_dir / "config").write_text(
            '[remote "origin"]\n\turl = ' + remote + "\n",
            encoding="utf-8",
        )

    def test_origin_target_from_https_remote(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_config(root, "https://github.com/AbuZuCom/agents.git")
            self.assertEqual(trusted_gh.repository_target(root), "AbuZuCom/agents")

    def test_origin_target_accepts_ssh_url(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_config(root, "ssh://git@github.com/owner/repo.git")
            self.assertEqual(trusted_gh.repository_target(root), "owner/repo")

    def test_origin_target_from_worktree_pointer(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            git_dir = root / "metadata" / "worktree"
            git_dir.mkdir(parents=True)
            (git_dir / "config").write_text(
                '[remote "origin"]\n\turl = git@github.com:owner/repo.git\n',
                encoding="utf-8",
            )
            (git_dir / "HEAD").write_text(
                "ref: refs/heads/feature/test\n", encoding="utf-8"
            )
            (root / ".git").write_text(
                "gitdir: metadata/worktree\n", encoding="utf-8"
            )
            self.assertEqual(trusted_gh.repository_target(root), "owner/repo")

    def test_invalid_origin_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_config(root, "https://example.test/owner/repo.git")
            with self.assertRaises(ValueError):
                trusted_gh.repository_target(root)

    def test_repo_argument_is_added_to_repository_command(self):
        captured = {}

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_config(root, "https://github.com/owner/repo.git")
            with patch.object(
                trusted_gh,
                "authenticated_account",
                return_value={"id": 1, "login": "user"},
            ):
                def run_gh(repository, arguments):
                    captured["arguments"] = arguments
                    return subprocess.CompletedProcess(arguments, 0, "", "")

                with patch.object(trusted_gh, "run_gh", side_effect=run_gh):
                    trusted_gh._run_requested_command(root, ["pr", "create"])
        self.assertEqual(captured["arguments"], [
            "pr", "create", "--head", "owner:feature/test", "--repo", "owner/repo"
        ])

    def test_explicit_repo_argument_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_config(root, "https://github.com/owner/repo.git")
            self.assertEqual(
                trusted_gh.with_repository_context(
                    root, ["pr", "view", "-R", "other/repo"]
                ),
                ["pr", "view", "-R", "other/repo"],
            )

    def test_global_options_before_command_receive_context(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_config(root, "https://github.com/owner/repo.git")
            arguments = trusted_gh.with_repository_context(
                root, ["--hostname", "github.com", "pr", "create"]
            )
            self.assertIn("--head", arguments)

    def test_head_equals_form_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_config(root, "https://github.com/owner/repo.git")
            arguments = trusted_gh.with_repository_context(
                root, ["pr", "create", "--head=owner:other"]
            )
            self.assertEqual(arguments.count("--head=owner:other"), 1)

    def test_injected_flags_precede_end_of_options(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_config(root, "https://github.com/owner/repo.git")
            arguments = trusted_gh.with_repository_context(
                root, ["pr", "view", "--", "12"]
            )
            self.assertEqual(
                arguments, ["pr", "view", "--repo", "owner/repo", "--", "12"]
            )

    def test_repo_commands_do_not_receive_unsupported_context_flag(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_config(root, "https://github.com/owner/repo.git")
            self.assertEqual(
                trusted_gh.with_repository_context(root, ["repo", "view"]),
                ["repo", "view"],
            )

    def test_invalid_branch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_config(root, "https://github.com/owner/repo.git")
            (root / ".git" / "HEAD").write_text(
                "ref: refs/heads/bad//branch\n", encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                trusted_gh.repository_branch(root)

    def test_failure_message_does_not_expose_exception_text(self):
        with patch.object(
            trusted_gh, "authenticated_account", side_effect=OSError("token-secret-value")
        ):
            with patch.object(
                trusted_gh.sys, "argv", ["trusted_gh.py", "run", "api", "user"]
            ):
                output = io.StringIO()
                with redirect_stderr(output):
                    result = trusted_gh.main()
        self.assertEqual(result, 1)
        self.assertNotIn("token-secret-value", output.getvalue())

if __name__ == "__main__":
    unittest.main()
