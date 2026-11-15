#!/usr/bin/env python3
"""A failed security review still posts a comment into the pull request."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
REVIEW_PATH = REPO_ROOT / ".github" / "workflows" / "security-review.yml"
FAILURE_STEP = "Post review comment without a verdict"
SCRIPT_TIMEOUT_SECONDS = 20
PR_NUMBER = "42"
HEAD_SHA = "1" * 40
BASE_SHA = "2" * 40
RUN_URL = "https://github.com/abuzucom/foucault/actions/runs/7"
GITHUB_COMMENT_LIMIT = 65536

# The harness hands the step the same github, context, core, and require
# globals that actions/github-script provides. It records each comment.
NODE_HARNESS = r"""
const [scriptText] = process.argv.slice(-1);
const comments = [];
const github = {
  rest: {
    issues: {
      createComment: async (params) => { comments.push(params); },
    },
  },
};
const context = { repo: { owner: "abuzucom", repo: "foucault" } };
const core = { warning: () => {}, setFailed: () => {} };
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
new AsyncFunction("github", "context", "core", "require", scriptText)(
  github, context, core, require)
  .then(() => process.stdout.write(JSON.stringify({ comments, failure: null })))
  .catch((error) => process.stdout.write(
    JSON.stringify({ comments, failure: String(error) })));
"""


def _review_steps() -> list:
    """Return the reusable review job's steps."""
    document = yaml.safe_load(REVIEW_PATH.read_text(encoding="utf-8"))
    return document["jobs"]["review"]["steps"]


def _named_step(steps: list, name: str) -> dict:
    """Return the step whose name matches exactly."""
    for step in steps:
        if step.get("name") == name:
            return step
    raise AssertionError(f"workflow step {name!r} is missing")


class FailureCommentWiringTest(unittest.TestCase):
    """The failure comment runs exactly when no verdict reached the PR."""

    def setUp(self):
        self.steps = _review_steps()
        self.names = [step.get("name") for step in self.steps]
        self.step = _named_step(self.steps, FAILURE_STEP)

    def test_step_runs_only_on_a_failure_without_a_verdict(self):
        condition = self.step["if"]
        self.assertIn("failure()", condition)
        self.assertIn("inputs.pr_comment", condition)
        self.assertIn("steps.verdict.outputs.line == ''", condition)
        self.assertIn("steps.resolve.outputs.pr_number != ''", condition)

    def test_step_follows_the_verdict_comment(self):
        self.assertLess(
            self.names.index("Post PR comment"), self.names.index(FAILURE_STEP)
        )
        self.assertLess(
            self.names.index(FAILURE_STEP), self.names.index("Publish check run")
        )

    def test_step_reads_the_resolved_pull_request(self):
        env = self.step["env"]
        self.assertEqual(env["PR_NUMBER"], "${{ steps.resolve.outputs.pr_number }}")
        self.assertEqual(env["HEAD_SHA"], "${{ steps.resolve.outputs.head_sha }}")
        self.assertEqual(env["BASE_SHA"], "${{ steps.resolve.outputs.base_sha }}")

    def test_fork_review_shares_the_step(self):
        document = yaml.safe_load(REVIEW_PATH.read_text(encoding="utf-8"))
        fork_names = [
            step.get("name") for step in document["jobs"]["fork-review"]["steps"]
        ]
        self.assertIn(FAILURE_STEP, fork_names)


class FailureCommentBehaviorTest(unittest.TestCase):
    """Execute the failure comment script against recorded API calls."""

    def setUp(self):
        self.node = shutil.which("node")
        if self.node is None:
            self.skipTest("node is required to execute the github-script step")
        self.script = _named_step(_review_steps(), FAILURE_STEP)["with"]["script"]

    def _post(self, response_text: str | None) -> dict:
        """Run the step in a directory holding an optional response.txt."""
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            if response_text is not None:
                (directory / "response.txt").write_text(response_text, encoding="utf-8")
            env = {
                "PATH": str(Path(self.node).parent),
                "PR_NUMBER": PR_NUMBER,
                "HEAD_SHA": HEAD_SHA,
                "BASE_SHA": BASE_SHA,
                "RUN_URL": RUN_URL,
            }
            result = subprocess.run(
                [self.node, "-e", NODE_HARNESS, self.script],
                capture_output=True,
                text=True,
                check=True,
                cwd=directory,
                env=env,
                timeout=SCRIPT_TIMEOUT_SECONDS,
            )
        report = json.loads(result.stdout)
        self.assertIsNone(report["failure"])
        self.assertEqual(len(report["comments"]), 1)
        return report["comments"][0]

    def test_invalid_response_is_posted_to_the_pull_request(self):
        comment = self._post("Mode: PR\n\nNo findings.\n")
        self.assertEqual(comment["issue_number"], int(PR_NUMBER))
        self.assertEqual(comment["owner"], "abuzucom")
        self.assertEqual(comment["repo"], "foucault")
        self.assertIn("No findings.", comment["body"])
        self.assertIn("no valid VERDICT line", comment["body"])
        self.assertIn(HEAD_SHA, comment["body"])
        self.assertIn(BASE_SHA, comment["body"])
        self.assertIn(RUN_URL, comment["body"])

    def test_response_fence_outruns_backtick_runs(self):
        comment = self._post("text\n`````\n@someone ![x](http://example.invalid)\n")
        self.assertIn("``````\n", comment["body"])
        self.assertTrue(comment["body"].rstrip().endswith("``````"))

    def test_missing_response_posts_a_fixed_failure_notice(self):
        comment = self._post(None)
        self.assertIn("before the model returned a response", comment["body"])
        self.assertIn(RUN_URL, comment["body"])

    def test_blank_response_posts_a_fixed_failure_notice(self):
        comment = self._post("  \n\n")
        self.assertIn("before the model returned a response", comment["body"])

    def test_oversized_response_fits_in_one_comment(self):
        comment = self._post("x" * (GITHUB_COMMENT_LIMIT * 2))
        self.assertLessEqual(len(comment["body"]), GITHUB_COMMENT_LIMIT)
        self.assertIn("truncated", comment["body"])


if __name__ == "__main__":
    unittest.main()
