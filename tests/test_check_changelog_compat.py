"""Test changelog range compatibility with historical headings."""
import importlib.util
import unittest
from pathlib import Path

CHECKER_PATH = Path(__file__).resolve().parent.parent / "scripts" / "check_changelog.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_changelog", CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = _load_checker()


class ChangelogCompatibilityTest(unittest.TestCase):
    """Ensure range checks compare against the historical heading format."""

    def test_range_accepts_a_legacy_base_heading(self):
        base = "## [2.0.1]: historical release\n\n- Existing entry.\n"
        head = "## [3.0.2] (2026-09-14)\n\n- Fixed the range check.\n"
        findings = checker.find_range_violations(
            base, head, ["CHANGELOG.md", "scripts/check_changelog.py"])
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
