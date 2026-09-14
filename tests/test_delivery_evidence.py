#!/usr/bin/env python3
"""Tests for evidence-based delivery claims."""
import unittest
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import delivery_evidence


COMMIT = "70c515ed52a91bb2eff762130527a7865c382aab"


def make_evidence(**overrides):
    """Return a complete evidence record with safe defaults."""
    evidence = {
        "checkout_path": "K:\\GitHub\\foucault",
        "current_branch": "main",
        "commit": COMMIT,
        "remote_ref": "fix/security-enforcement-drift",
        "command_result": "succeeded",
        "pr_number": None,
        "is_draft": None,
        "remote_ref_verified": False,
        "pr_verified": False,
        "draft_status_verified": False,
    }
    evidence.update(overrides)
    return evidence


class DeliveryEvidenceTest(unittest.TestCase):
    """Claims require direct evidence from the relevant remote state."""

    def test_feature_branch_claim_stays_unverified_on_main_checkout(self):
        evidence = make_evidence()
        errors = delivery_evidence.claim_errors(evidence, "push")
        self.assertIn("remote ref has not been read back", errors)
        self.assertEqual(
            delivery_evidence.verification_status(evidence, "push"),
            "unverified",
        )

    def test_pull_request_claim_requires_readback(self):
        evidence = make_evidence(pr_number=46, is_draft=True)
        errors = delivery_evidence.claim_errors(evidence, "pull_request")
        self.assertIn("remote ref has not been read back", errors)
        self.assertIn("pull request has not been read back", errors)
        self.assertIn("draft status has not been read back", errors)

    def test_failed_command_is_distinct_from_unverified_state(self):
        evidence = make_evidence(command_result="failed")
        self.assertEqual(
            delivery_evidence.verification_status(evidence, "push"),
            "failed",
        )

    def test_verified_draft_pull_request_requires_all_readbacks(self):
        evidence = make_evidence(
            pr_number=46,
            is_draft=True,
            remote_ref_verified=True,
            pr_verified=True,
            draft_status_verified=True,
        )
        self.assertEqual(
            delivery_evidence.verification_status(evidence, "pull_request"),
            "verified",
        )

    def test_invalid_commit_id_stays_unverified(self):
        evidence = make_evidence(commit="70c515e")
        self.assertIn("commit must be a 40 or 64 character hexadecimal ID",
                      delivery_evidence.validate_evidence(evidence))


if __name__ == "__main__":
    unittest.main()
