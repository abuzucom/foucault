import tempfile
import unittest
from pathlib import Path

from scripts.check_audit_policy import find_violations


class AuditPolicyTest(unittest.TestCase):
    def test_current_policy_passes(self):
        self.assertEqual(find_violations(Path("AUDIT.md")), [])

    def test_missing_required_control_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AUDIT.md"
            path.write_text("## 0. Review Modes\n", encoding="ascii")
            findings = find_violations(path)
        self.assertTrue(any("missing required" in item for item in findings))

    def test_long_prose_line_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AUDIT.md"
            path.write_text("x" * 121, encoding="ascii")
            findings = find_violations(path)
        self.assertTrue(any("exceeds" in item for item in findings))

    def test_long_table_row_is_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AUDIT.md"
            path.write_text("| " + "x" * 130, encoding="ascii")
            findings = find_violations(path)
        self.assertFalse(any("exceeds" in item for item in findings))


if __name__ == "__main__":
    unittest.main()
