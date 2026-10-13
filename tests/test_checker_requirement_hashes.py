#!/usr/bin/env python3
"""Require hash-pinned checker dependencies."""
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS_PATH = REPO_ROOT / "requirements-checkers.txt"
EXACT_PIN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*==[A-Za-z0-9.+!-]+\Z")
SHA256_HASH = re.compile(r"--hash=sha256:[0-9a-f]{64}\Z")
# pip treats "#" as a comment only at line start or after whitespace.
COMMENT = re.compile(r"(?:^|\s)#.*")


def read_requirement_entries(path: Path) -> list[list[str]]:
    """Return each requirement as tokens, joining backslash continuations."""
    entries = []
    pending = ""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = COMMENT.sub("", raw_line).strip()
        if line.endswith("\\"):
            pending += line[:-1] + " "
            continue
        logical = (pending + line).strip()
        pending = ""
        if logical:
            entries.append(logical.split())
    if pending.strip():
        entries.append(pending.split())
    return entries


class CheckerRequirementHashTest(unittest.TestCase):
    """pip enables hash checking only while every requirement carries a hash."""

    def test_requirements_file_is_not_empty(self):
        self.assertTrue(read_requirement_entries(REQUIREMENTS_PATH))

    def test_every_requirement_uses_an_exact_version(self):
        for tokens in read_requirement_entries(REQUIREMENTS_PATH):
            with self.subTest(requirement=tokens[0]):
                self.assertRegex(tokens[0], EXACT_PIN)

    def test_every_requirement_carries_sha256_hashes(self):
        for tokens in read_requirement_entries(REQUIREMENTS_PATH):
            options = tokens[1:]
            with self.subTest(requirement=tokens[0]):
                self.assertTrue(options, "requirement has no --hash option")
                for option in options:
                    self.assertRegex(option, SHA256_HASH)


if __name__ == "__main__":
    unittest.main()
