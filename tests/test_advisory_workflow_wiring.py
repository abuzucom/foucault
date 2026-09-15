#!/usr/bin/env python3
"""Cover safe advisory prose-check wiring in GitHub Actions."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


class AdvisoryWorkflowTest(unittest.TestCase):
    """Workflow source keeps untrusted metadata outside shell text."""

    def test_ci_workflow_runs_pull_request_checker(self):
        text = CI_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 scripts/check_pull_request_message.py", text)
        self.assertIn("if: github.event_name == 'pull_request'", text)
        self.assertNotIn("github.event.pull_request.title", text)
        self.assertNotIn("github.event.pull_request.body", text)

    def test_ci_workflow_runs_authorship_checkers(self):
        text = CI_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 scripts/check_banned_agents.py", text)
        self.assertIn("python3 scripts/check_git_identity.py", text)
        self.assertIn("python3 scripts/check_commit_attribution.py", text)
        self.assertIn("GH_TOKEN", text)
        self.assertIn("fetch-depth: 0", text)
        self.assertIn("BASE_SHA", text)
        self.assertIn("HEAD_SHA", text)

    def test_ci_workflow_avoids_ref_interpolation_in_commands(self):
        text = CI_WORKFLOW.read_text(encoding="utf-8")
        run_blocks = re.findall(r"run:\s*[|>-]?\s*\n((?:\s{10,}.*\n)+)", text)
        combined = "\n".join(run_blocks)
        self.assertNotIn("github.event.pull_request.base.ref", combined)
        self.assertNotIn("github.event.pull_request.head.sha", combined)
        self.assertIn("BASE_SHA", text)
        self.assertIn("HEAD_SHA", text)

    def test_every_checkout_disables_persisted_credentials(self):
        text = CI_WORKFLOW.read_text(encoding="utf-8")
        checkout_count = text.count("actions/checkout@")
        self.assertGreater(checkout_count, 0)
        self.assertEqual(
            checkout_count,
            text.count("persist-credentials: false"),
        )

    def test_changelog_range_jobs_fetch_full_history(self):
        text = CI_WORKFLOW.read_text(encoding="utf-8")
        section = text.split("  checks:", 1)[1]
        self.assertIn("fetch-depth: 0", section)
        self.assertIn("python3 scripts/check_changelog.py --base", section)


if __name__ == "__main__":
    unittest.main()
