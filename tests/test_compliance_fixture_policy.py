#!/usr/bin/env python3
"""Verify evaluator fixtures remain vulnerable without weakening production scans."""

import unittest
from pathlib import Path

from scripts import check_compliance_tree
from scripts import check_secrets_heuristic
from scripts import check_weak_hashing


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = "eval/cases/weak-hash-password-file/input.py"


class ComplianceFixturePolicyTest(unittest.TestCase):
    """Keep evaluator vulnerabilities available to the model review corpus."""

    def setUp(self):
        self.checkers = {
            "check_secrets_heuristic": check_secrets_heuristic,
            "check_weak_hashing": check_weak_hashing,
        }
        self.fixture_text = (REPOSITORY_ROOT / FIXTURE_PATH).read_text(
            encoding="utf-8"
        )

    def test_fixture_stays_vulnerable_to_direct_weak_hash_checker(self):
        violations = check_weak_hashing.find_violations(
            self.fixture_text, FIXTURE_PATH
        )
        self.assertEqual(len(violations), 1)
        self.assertIn("MD5/SHA-1", violations[0])

    def test_fixture_is_outside_production_weak_hash_scan(self):
        violations = check_compliance_tree._scan_blob(
            FIXTURE_PATH, self.fixture_text, "100644", self.checkers
        )
        self.assertEqual(violations, [])

    def test_production_code_remains_in_scope(self):
        violations = check_compliance_tree._scan_blob(
            "src/passwords.py",
            self.fixture_text,
            "100644",
            self.checkers,
        )
        self.assertEqual(len(violations), 1)
        self.assertIn("MD5/SHA-1", violations[0])


if __name__ == "__main__":
    unittest.main()
