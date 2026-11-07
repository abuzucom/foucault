import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))

import run_eval


class ReviewTimeoutTest(unittest.TestCase):
    def test_timeout_status_requires_needs_human_line(self) -> None:
        response = "REVIEW STATUS: NEEDS-HUMAN - timeout reached."
        self.assertTrue(run_eval.review_status_matches("NEEDS-HUMAN", response))

    def test_missing_timeout_status_does_not_match(self) -> None:
        response = "VERDICT: NEEDS-HUMAN - incomplete review."
        self.assertFalse(run_eval.review_status_matches("NEEDS-HUMAN", response))


if __name__ == "__main__":
    unittest.main()
