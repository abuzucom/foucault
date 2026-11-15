#!/usr/bin/env python3
"""A cancelled security review publishes a cancelled check, not a failure."""

from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
REVIEW_PATH = REPO_ROOT / ".github" / "workflows" / "security-review.yml"
PUBLISH_STEP = "Publish check run"
SCRIPT_TIMEOUT_SECONDS = 20
HEAD_SHA = "1" * 40
RUN_URL = "https://github.com/abuzucom/foucault/actions/runs/7"
VERDICT_LINE = "VERDICT: APPROVE - no findings"

# The harness hands the step the github, context, and core globals that
# actions/github-script provides. A failing createCheck simulates an API
# outage on every attempt.
NODE_HARNESS = r"""
const [scriptText, failCreate] = process.argv.slice(-2);
const requests = [];
const warnings = [];
const github = {
  rest: {
    checks: {
      create: async (params) => {
        requests.push(params);
        if (failCreate === "true") { throw new Error("api unavailable"); }
      },
    },
  },
};
const context = { repo: { owner: "abuzucom", repo: "foucault" } };
const core = { warning: (message) => { warnings.push(message); } };
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
new AsyncFunction("github", "context", "core", scriptText)(github, context, core)
  .then(() => process.stdout.write(
    JSON.stringify({ requests, warnings, failure: null })))
  .catch((error) => process.stdout.write(
    JSON.stringify({ requests, warnings, failure: String(error) })));
"""


def _publish_script() -> str:
    """Return the review job's check-run publication script."""
    document = yaml.safe_load(REVIEW_PATH.read_text(encoding="utf-8"))
    for step in document["jobs"]["review"]["steps"]:
        if step.get("name") == PUBLISH_STEP:
            return step["with"]["script"]
    raise AssertionError(f"workflow step {PUBLISH_STEP!r} is missing")


class CancelledCheckTest(unittest.TestCase):
    """Execute the publication script for each job status."""

    def setUp(self):
        self.node = shutil.which("node")
        if self.node is None:
            self.skipTest("node is required to execute the github-script step")
        self.script = _publish_script()

    def _publish(self, job_status: str, verdict_line: str = "",
                 fail_create: bool = False) -> dict:
        """Run the step once and return the recorded API calls."""
        env = {
            "PATH": str(Path(self.node).parent),
            "HEAD_SHA": HEAD_SHA,
            "JOB_STATUS": job_status,
            "VERDICT_LINE": verdict_line,
            "RUN_URL": RUN_URL,
        }
        result = subprocess.run(
            [self.node, "-e", NODE_HARNESS, self.script,
             "true" if fail_create else "false"],
            capture_output=True,
            text=True,
            check=True,
            env=env,
            timeout=SCRIPT_TIMEOUT_SECONDS,
        )
        return json.loads(result.stdout)

    def test_cancelled_run_publishes_a_cancelled_check(self):
        report = self._publish("cancelled")
        self.assertIsNone(report["failure"])
        request = report["requests"][-1]
        self.assertEqual(request["conclusion"], "cancelled")
        self.assertEqual(request["output"]["title"], "security-review: cancelled")
        self.assertIn("cancelled before a verdict", request["output"]["summary"])
        self.assertNotIn("failed", request["output"]["summary"])

    def test_cancelled_summary_carries_no_verdict(self):
        """The caller treats a VERDICT summary as a completed review."""
        request = self._publish("cancelled")["requests"][-1]
        self.assertNotIn("VERDICT:", request["output"]["summary"])

    def test_failed_run_still_publishes_a_failure(self):
        request = self._publish("failure")["requests"][-1]
        self.assertEqual(request["conclusion"], "failure")
        self.assertIn("review failed before a verdict", request["output"]["summary"])

    def test_passed_run_still_publishes_success_with_the_verdict(self):
        request = self._publish("success", VERDICT_LINE)["requests"][-1]
        self.assertEqual(request["conclusion"], "success")
        self.assertIn(VERDICT_LINE, request["output"]["summary"])

    def test_cancelled_publication_error_warns_instead_of_throwing(self):
        report = self._publish("cancelled", fail_create=True)
        self.assertIsNone(report["failure"])
        self.assertEqual(len(report["warnings"]), 1)

    def test_failed_publication_error_still_throws(self):
        report = self._publish("failure", fail_create=True)
        self.assertIn("api unavailable", report["failure"])


if __name__ == "__main__":
    unittest.main()
