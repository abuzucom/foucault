#!/usr/bin/env python3
"""Behavioral tests for three security notes in foucault-adapted files.

S-15: trusted_gh.py wrote gh stdout without removing terminal controls.
S-16: the weak-hash and secret checkers skipped hooks/, eval/, and tools/.
S-17: pre-commit installed PyYAML without hash verification.
"""
import io
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import trusted_gh

CI_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"
PRE_COMMIT = REPOSITORY_ROOT / ".pre-commit-config.yaml"
ESCAPE_TITLE = "\x1b]0;spoofed\x07title\x1b[2J"
CHECKER_HOOKS = ("check-weak-hashing", "check-secrets-heuristic")
CHECKER_STEPS = ("Weak hashing", "Secret heuristics")
REQUIRED_SCAN_FILES = (
    "hooks/_gate_core.py",
    "hooks/require_consent.py",
    "eval/run_eval.py",
    "tools/hook-trace/sitecustomize.py",
)


def _write_repository(root: Path) -> None:
    """Write minimal checkout metadata with a GitHub origin."""
    git_dir = root / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text(
        "ref: refs/heads/feature/test\n", encoding="utf-8")
    (git_dir / "config").write_text(
        '[remote "origin"]\n\turl = https://github.com/owner/repo.git\n',
        encoding="utf-8")


def _pre_commit_hooks() -> dict:
    """Return pre-commit hooks keyed by id."""
    document = yaml.safe_load(PRE_COMMIT.read_text(encoding="utf-8"))
    return {
        hook["id"]: hook
        for repository in document["repos"]
        for hook in repository["hooks"]
    }


class TrustedGhStdoutTest(unittest.TestCase):
    """gh stdout reaches the terminal without control sequences."""

    def _run_with_stdout(self, output: str) -> str:
        """Return what _run_requested_command writes for one gh stdout."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write_repository(root)
            completed = subprocess.CompletedProcess([], 0, output, "")
            captured = io.StringIO()
            with patch.object(trusted_gh, "authenticated_account",
                              return_value={"id": 1, "login": "user"}), \
                    patch.object(trusted_gh, "run_gh", return_value=completed), \
                    redirect_stdout(captured):
                code = trusted_gh._run_requested_command(
                    root, ["issue", "view", "1"])
        self.assertEqual(code, 0)
        return captured.getvalue()

    def test_escape_sequences_in_stdout_are_replaced(self):
        written = self._run_with_stdout(f"title: {ESCAPE_TITLE}\n")
        self.assertNotIn("\x1b", written)
        self.assertNotIn("\x07", written)
        self.assertIn("title", written)

    def test_newlines_and_tabs_in_stdout_survive(self):
        written = self._run_with_stdout("number\t1\nstate\topen\n")
        self.assertEqual(written, "number\t1\nstate\topen\n")


class CheckerScopeTest(unittest.TestCase):
    """The weak-hash and secret checkers cover every executable tree."""

    def test_ci_steps_scan_hooks_eval_and_tools(self):
        workflow = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
        steps = {
            step.get("name"): step.get("run", "")
            for step in workflow["jobs"]["checks"]["steps"]
        }
        for name in CHECKER_STEPS:
            with self.subTest(step=name):
                command = steps[name]
                # globstar makes ** match every directory depth, so the CI
                # scope equals the recursive pre-commit regex.
                self.assertIn("shopt -s globstar", command)
                for pattern in ("hooks/**/*.py", "eval/*.py", "tools/**/*.py"):
                    self.assertIn(pattern, command)

    def test_pre_commit_hooks_match_hooks_eval_and_tools(self):
        hooks = _pre_commit_hooks()
        for hook_id in CHECKER_HOOKS:
            pattern = re.compile(hooks[hook_id]["files"])
            for path in REQUIRED_SCAN_FILES:
                with self.subTest(hook=hook_id, path=path):
                    self.assertIsNotNone(pattern.search(path))

    def test_pre_commit_weak_hash_hook_skips_eval_fixtures(self):
        pattern = re.compile(_pre_commit_hooks()["check-weak-hashing"]["files"])
        self.assertIsNone(pattern.search("eval/cases/weak-hash-file/target.py"))


class PreCommitDependencyTest(unittest.TestCase):
    """No pre-commit hook installs a package without hash verification."""

    def test_no_hook_declares_unhashed_dependencies(self):
        for hook_id, hook in _pre_commit_hooks().items():
            with self.subTest(hook=hook_id):
                self.assertNotIn("additional_dependencies", hook)

    def test_yaml_hooks_use_the_hash_checked_environment(self):
        hooks = _pre_commit_hooks()
        for hook_id in ("check-persist-credentials", "check-dockerfile-root",
                        "hook-tests"):
            with self.subTest(hook=hook_id):
                self.assertEqual(hooks[hook_id]["language"], "system")


if __name__ == "__main__":
    unittest.main()
