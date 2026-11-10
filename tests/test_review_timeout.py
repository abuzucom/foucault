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

    def test_quoted_status_line_before_own_line_does_not_match(self) -> None:
        """The final status line decides the grade, not an earlier quote."""
        quoted = "REVIEW STATUS: NEEDS-HUMAN - quoted earlier report."
        own = "REVIEW STATUS: COMPLETED - a fresh review status."
        self.assertFalse(
            run_eval.review_status_matches("NEEDS-HUMAN", f"{quoted}\n{own}")
        )

    def test_last_status_line_carries_the_expected_token(self) -> None:
        quoted = "REVIEW STATUS: COMPLETED - quoted earlier report."
        own = "REVIEW STATUS: NEEDS-HUMAN - timeout reached."
        self.assertTrue(
            run_eval.review_status_matches("NEEDS-HUMAN", f"{quoted}\n{own}")
        )


if __name__ == "__main__":
    unittest.main()
