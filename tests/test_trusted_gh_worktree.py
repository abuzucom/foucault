#!/usr/bin/env python3
"""Behavioral tests for trusted_gh.py repository-context discovery."""
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import trusted_gh


class WorktreePointerTest(unittest.TestCase):
    """_git_config_path and _git_dir read a worktree pointer identically."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def _linked_worktree(self, commondir: bool) -> Path:
        """Return a .git pointer file for one synthetic linked worktree."""
        common = self.root / "main.git"
        admin = common / "worktrees" / "feature"
        admin.mkdir(parents=True)
        (common / "config").write_text("[core]\n", encoding="utf-8")
        if commondir:
            (admin / "commondir").write_text("../..\n", encoding="utf-8")
        worktree = self.root / "feature"
        worktree.mkdir()
        pointer = worktree / ".git"
        pointer.write_text(f"gitdir: {admin}\n", encoding="utf-8")
        return pointer

    def test_linked_worktree_uses_common_config(self):
        pointer = self._linked_worktree(commondir=True)
        self.assertEqual(
            trusted_gh._git_config_path(pointer),
            self.root / "main.git" / "config")

    def test_worktree_without_commondir_uses_admin_config(self):
        pointer = self._linked_worktree(commondir=False)
        self.assertEqual(
            trusted_gh._git_config_path(pointer),
            trusted_gh._git_dir(pointer) / "config")

    def test_invalid_pointer_fails_the_same_way_in_both_readers(self):
        worktree = self.root / "broken"
        worktree.mkdir()
        pointer = worktree / ".git"
        for content in ("gitdir:\n", "worktree: elsewhere\n",
                        f"gitdir: {self.root / 'missing'}\n"):
            with self.subTest(content=content):
                pointer.write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError) as config_error:
                    trusted_gh._git_config_path(pointer)
                with self.assertRaises(ValueError) as dir_error:
                    trusted_gh._git_dir(pointer)
                self.assertEqual(
                    str(config_error.exception), str(dir_error.exception))


class ParentSearchDepthTest(unittest.TestCase):
    """_find_git_entry stops after the named parent search depth."""

    def test_search_stops_at_the_named_depth(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / ".git").mkdir()
            deep = root
            for index in range(trusted_gh.MAX_PARENT_SEARCH_DEPTH):
                deep = deep / f"d{index}"
            deep.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "repository context"):
                trusted_gh._find_git_entry(deep)
            self.assertEqual(
                trusted_gh._find_git_entry(deep.parent), root / ".git")


if __name__ == "__main__":
    unittest.main()
