#!/usr/bin/env python3
"""Behavioral tests for checker crash and boundary handling.

Each class drives one checker through its real entry point with inputs that
previously crashed it, misrouted it, or slipped past a boundary.
"""
import contextlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import check_audit_policy
from scripts import check_changelog
from scripts import check_gate_adoption
from scripts import delivery_evidence
from scripts import sync
from scripts.trusted_git import run_git

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
COMMIT = "70c515ed52a91bb2eff762130527a7865c382aab"
VERSIONED_CHANGELOG = (
    "# Changelog\n\n## [1.0.0] (2026-01-01)\n\n### Added\n\n- First.\n"
)
UNVERSIONED_CHANGELOG = "# Changelog\n\n## [Unreleased]\n\n- Pending.\n"
AUDIT_LINE = b"x" * 99 + b"\n"
SUPPORTING_FILE_BYTES = 20 * 1024


def _git(repository: Path, *arguments: str) -> None:
    """Run one trusted Git command in a synthetic repository."""
    run_git(repository, list(arguments), check=True)


class StagedChangelogTest(unittest.TestCase):
    """check_staged reports an unversioned changelog instead of raising."""

    def _repository(self, directory: str) -> Path:
        """Return a repository whose HEAD holds a versioned changelog."""
        repository = Path(directory)
        _git(repository, "init", "-q")
        _git(repository, "config", "user.name", "Synthetic Tester")
        _git(repository, "config", "user.email", "tester@example.invalid")
        _git(repository, "config", "commit.gpgsign", "false")
        (repository / "CHANGELOG.md").write_text(
            VERSIONED_CHANGELOG, encoding="utf-8")
        _git(repository, "add", "CHANGELOG.md")
        _git(repository, "commit", "-q", "-m", "chore: seed changelog")
        return repository

    def test_unversioned_staged_changelog_reports_findings(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = self._repository(directory)
            (repository / "CHANGELOG.md").write_text(
                UNVERSIONED_CHANGELOG, encoding="utf-8")
            (repository / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
            _git(repository, "add", "CHANGELOG.md", "module.py")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = check_changelog.check_staged(repository)
        self.assertEqual(code, 1)
        self.assertIn("[Unreleased] is not allowed", stderr.getvalue())
        self.assertIn("no versioned release heading", stderr.getvalue())
        # A missing version is not a version that failed to advance.
        self.assertNotIn("version must advance", stderr.getvalue())


class SyncArgumentTest(unittest.TestCase):
    """sync.main rejects unknown flags and keeps the documented modes."""

    def test_unknown_flag_exits_without_writing(self):
        with mock.patch.object(sync, "sync_copies") as copier, \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                sync.main(["--chek"])
        self.assertEqual(raised.exception.code, 2)
        copier.assert_not_called()

    def test_abbreviated_flag_exits_without_writing(self):
        with mock.patch.object(sync, "sync_copies") as copier, \
                mock.patch.object(sync, "print_adoptable") as printer, \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                sync.main(["--print"])
        self.assertEqual(raised.exception.code, 2)
        copier.assert_not_called()
        printer.assert_not_called()

    def test_positional_argument_exits_without_writing(self):
        with mock.patch.object(sync, "sync_copies") as copier, \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                sync.main(["some/path"])
        self.assertEqual(raised.exception.code, 2)
        copier.assert_not_called()

    def test_two_mode_flags_exit_without_running(self):
        with mock.patch.object(sync, "sync_copies") as copier, \
                mock.patch.object(sync, "write_shared") as writer, \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                sync.main(["--check", "--write-shared"])
        self.assertEqual(raised.exception.code, 2)
        copier.assert_not_called()
        writer.assert_not_called()

    def test_check_flag_runs_check_only(self):
        with mock.patch.object(sync, "sync_copies", return_value=0) as copier:
            self.assertEqual(sync.main(["--check"]), 0)
        copier.assert_called_once_with(check_only=True)

    def test_no_flag_writes_copies(self):
        with mock.patch.object(sync, "sync_copies", return_value=0) as copier:
            self.assertEqual(sync.main([]), 0)
        copier.assert_called_once_with(check_only=False)

    def test_check_shared_flag_dispatches(self):
        with mock.patch.object(sync, "check_shared", return_value=0) as checker:
            self.assertEqual(sync.main(["--check-shared"]), 0)
        checker.assert_called_once()


class SyncManifestTest(unittest.TestCase):
    """check_shared reports a manifest that is not a JSON object."""

    def test_list_manifest_reports_unreadable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / sync.SHARED_MANIFEST).write_text("[1, 2]\n", encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = sync.check_shared(root)
        self.assertEqual(code, 1)
        self.assertIn("is not a JSON object", stderr.getvalue())


class SyncBundleSizeTest(unittest.TestCase):
    """An oversized assembled bundle names the bundle, not AGENTS.md."""

    def test_oversized_bundle_names_assembled_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / sync.SOURCE).write_text("canonical\n", encoding="ascii")
            for relative_name in sync.SUPPORTING_POLICY_FILES:
                path = root / relative_name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"d" * SUPPORTING_FILE_BYTES + b"\n")
            with self.assertRaisesRegex(ValueError, "assembled policy"):
                sync.policy_bytes(root)


class SyncAdoptableEncodingTest(unittest.TestCase):
    """print_adoptable returns 1 for non-ASCII policy content."""

    def test_non_ascii_supporting_file_returns_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / sync.SOURCE).write_text("canonical\n", encoding="ascii")
            for relative_name in sync.SUPPORTING_POLICY_FILES:
                path = root / relative_name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("detail\n", encoding="ascii")
            (root / sync.SUPPORTING_POLICY_FILES[0]).write_bytes(b"caf\xc3\xa9\n")
            with contextlib.redirect_stderr(io.StringIO()), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(sync.print_adoptable(root), 1)


class DeliveryPrimaryBranchTest(unittest.TestCase):
    """A push claim from a primary branch never verifies."""

    def _evidence(self, branch: str) -> dict:
        """Return fully verified push evidence for one branch."""
        return {
            "checkout_path": "/synthetic/checkout",
            "current_branch": branch,
            "commit": COMMIT,
            "remote_ref": branch,
            "command_result": "succeeded",
            "pr_number": None,
            "is_draft": None,
            "remote_ref_verified": True,
            "pr_verified": False,
            "draft_status_verified": False,
        }

    def test_primary_branches_stay_unverified(self):
        for branch in ("main", "master"):
            with self.subTest(branch=branch):
                evidence = self._evidence(branch)
                self.assertEqual(
                    delivery_evidence.claim_errors(evidence, "push"),
                    ["current branch is a primary branch"])
                self.assertEqual(
                    delivery_evidence.verification_status(evidence, "push"),
                    "unverified")

    def test_feature_branch_push_verifies(self):
        evidence = self._evidence("fix/checker-crash-handling")
        self.assertEqual(
            delivery_evidence.verification_status(evidence, "push"), "verified")


class AuditPolicySizeTest(unittest.TestCase):
    """AUDIT.md must stay below 32768 bytes (product rule 4)."""

    def _write(self, path: Path, size: int) -> None:
        """Write short ASCII lines totaling exactly size bytes."""
        full_lines, remainder = divmod(size, len(AUDIT_LINE))
        body = AUDIT_LINE * full_lines
        if remainder:
            body += b"x" * (remainder - 1) + b"\n"
        path.write_bytes(body)

    def test_policy_at_ceiling_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AUDIT.md"
            self._write(path, check_audit_policy.MAX_BYTES)
            findings = check_audit_policy.find_violations(path)
        self.assertIn(
            f"policy must be smaller than {check_audit_policy.MAX_BYTES} bytes",
            findings)

    def test_policy_below_ceiling_has_no_size_finding(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AUDIT.md"
            self._write(path, check_audit_policy.MAX_BYTES - 1)
            findings = check_audit_policy.find_violations(path)
        self.assertFalse(any("must be smaller" in item for item in findings))


class GateAdoptionDataTest(unittest.TestCase):
    """The adoption check names an absent branch-name ban list."""

    def test_missing_ban_list_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "adopter"
            root.mkdir()
            for relative in (
                "hooks", "scripts", "tests", ".claude", ".codex", ".gemini",
                ".agents",
            ):
                shutil.copytree(REPOSITORY_ROOT / relative, root / relative)
            for relative in check_gate_adoption.REQUIRED_POLICY:
                shutil.copy(REPOSITORY_ROOT / relative, root / relative)
            (root / "scripts" / "branch_name_bans.txt").unlink()
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = check_gate_adoption.main(["--root", str(root)])
        self.assertEqual(code, 1)
        self.assertIn(
            "scripts/branch_name_bans.txt is absent", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
