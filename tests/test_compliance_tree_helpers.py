#!/usr/bin/env python3
"""Behavioral tests for the immutable compliance scanner's Git helpers.

check_compliance_tree.py keeps its own PATH and directory helpers so the
scanner runs without trusted_git.py. These tests hold both copies to the
same rules.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_compliance_tree
import trusted_git


class SafeSearchPathTest(unittest.TestCase):
    """The scanner's PATH filter matches trusted_git.py."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name).resolve()
        self.repo = root / "candidate"
        self.outside = root / "outside"
        self.repo.mkdir()
        self.outside.mkdir()

    def _filtered(self, entries: list[str]) -> tuple[str, str]:
        """Return both filters' results for one PATH value."""
        path_value = os.pathsep.join(entries)
        with mock.patch.dict(os.environ, {"PATH": path_value}):
            return (check_compliance_tree._safe_search_path(self.repo),
                    trusted_git._safe_search_path(self.repo))

    def test_relative_entries_are_dropped(self):
        scanner, trusted = self._filtered(["bin", ".", str(self.outside)])
        self.assertEqual(scanner, str(self.outside))
        self.assertEqual(scanner, trusted)

    def test_quoted_entries_match_trusted_git(self):
        scanner, trusted = self._filtered([f'"{self.outside}"'])
        self.assertEqual(scanner, trusted)
        self.assertEqual(scanner, str(self.outside))

    def test_candidate_entries_are_dropped(self):
        scanner, trusted = self._filtered(
            [str(self.repo / "bin"), str(self.outside)])
        self.assertEqual(scanner, str(self.outside))
        self.assertEqual(scanner, trusted)


class SafeExecutionDirectoryTest(unittest.TestCase):
    """The scanner's process directory matches trusted_git.py."""

    def test_temporary_directory_follows_tempfile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            repo = root / "candidate"
            scratch = root / "scratch"
            tools = root / "tools"
            for path in (repo, scratch, tools):
                path.mkdir()
            executable = tools / "git"
            environment = {
                key: value for key, value in os.environ.items()
                if key not in ("TEMP", "TMP", "TMPDIR")
            }
            with mock.patch.dict(os.environ, environment, clear=True), \
                    mock.patch.object(tempfile, "tempdir", str(scratch)):
                scanner = check_compliance_tree._safe_execution_directory(
                    repo, str(executable))
                trusted = trusted_git._safe_directory(repo, executable)
        self.assertEqual(scanner, scratch)
        self.assertEqual(scanner, trusted)


class UnsafeExecutionDirectoryTest(unittest.TestCase):
    """Candidate-controlled directories never become the Git process cwd."""

    def test_candidate_directories_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory).resolve() / "candidate"
            tools = repo / "tools"
            tools.mkdir(parents=True)
            with mock.patch.object(tempfile, "tempdir", str(repo)):
                with self.assertRaises(RuntimeError):
                    check_compliance_tree._safe_execution_directory(
                        repo, str(tools / "git"))


class MissingAttributionCheckerTest(unittest.TestCase):
    """_scan_metadata fails closed with a named checker error."""

    def test_missing_attribution_checker_raises_runtime_error(self):
        commits = []
        banned = mock.Mock()
        banned.find_violations.return_value = []
        banned.load_commits.return_value = commits
        checkers = {"check_banned_agents": banned,
                    "check_branch_name": mock.Mock()}
        values = {"--tree": "a" * 40, "--base": "b" * 40}
        with self.assertRaisesRegex(
                RuntimeError, "check_commit_attribution"):
            check_compliance_tree._scan_metadata(
                values, Path("."), checkers)


class NamedConstantTest(unittest.TestCase):
    """The trusted workflow schema reads its shape from named constants."""

    def test_trusted_steps_match_the_declared_shape(self):
        steps = check_compliance_tree._trusted_steps()
        self.assertEqual(len(steps), check_compliance_tree.TRUSTED_STEP_COUNT)
        python_step = steps[check_compliance_tree.PYTHON_SETUP_STEP_INDEX]
        self.assertEqual(
            python_step["uses"], check_compliance_tree.SETUP_PYTHON_ACTION)
        for checkout in steps[:2]:
            self.assertEqual(
                checkout["with"]["fetch-depth"],
                check_compliance_tree.TRUSTED_FETCH_DEPTH)


if __name__ == "__main__":
    unittest.main()
