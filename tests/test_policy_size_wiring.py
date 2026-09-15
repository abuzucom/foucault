import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class PolicySizeWiringTests(unittest.TestCase):
    def test_pre_commit_runs_policy_size_checker(self):
        text = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
        self.assertIn("python scripts/check_policy_size.py", text)

    def test_ci_runs_policy_size_checker(self):
        text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("python3 scripts/check_policy_size.py", text)


if __name__ == "__main__":
    unittest.main()
