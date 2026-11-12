#!/usr/bin/env python3
"""Cover the credential the review workflow gives its head fetch.

The review job checks out without persisted credentials. A private caller
then cannot fetch its own pull request head. The fetch step passes the
workflow token to that one `git fetch` through `GIT_CONFIG_*` variables,
and only for a head in the base repository. These tests execute the step
script against a recording `git` stub, so no network access occurs.
"""
import base64
import json
import os
import shutil
import stat
import subprocess
import sys
import unittest
from pathlib import Path

import yaml

try:
    from tests.retrying_temp_directory import RetryingTemporaryDirectory
except ImportError:
    from retrying_temp_directory import RetryingTemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent
REVIEW_PATH = REPO_ROOT / ".github" / "workflows" / "security-review.yml"
FETCH_STEP_NAME = "Fetch pull request head object"
TOKEN_VARIABLE = "FETCH_TOKEN"
# Synthetic value. It grants access to nothing.
SYNTHETIC_TOKEN = "synthetic-workflow-token"
HEAD_SHA = "3" * 40
BASE_REPOSITORY = "acme/private-app"
FORK_REPOSITORY = "outsider/private-app"
EXTRAHEADER_KEY = "http.https://github.com/.extraheader"
SCRIPT_TIMEOUT_SECONDS = 60
STUB_SOURCE = """#!{python}
import json, os, sys
record = {{
    "arguments": sys.argv[1:],
    "config": {{name: value for name, value in os.environ.items()
               if name.startswith("GIT_CONFIG_")}},
    "token_variable": os.environ.get("{variable}"),
}}
with open(os.environ["STUB_RECORD"], "w", encoding="utf-8") as handle:
    json.dump(record, handle)
"""


def load_fetch_step() -> dict:
    """Return the head fetch step of the reusable review job."""
    with REVIEW_PATH.open(encoding="utf-8") as handle:
        workflow = yaml.safe_load(handle)
    for step in workflow["jobs"]["review"]["steps"]:
        if step.get("name") == FETCH_STEP_NAME:
            return step
    raise AssertionError(f"workflow step {FETCH_STEP_NAME!r} is missing")


class FetchCredentialFixture(unittest.TestCase):
    """Run the fetch step script with a recording stand-in for git."""

    def setUp(self):
        self.bash = shutil.which("bash")
        if self.bash is None:
            self.skipTest("bash is required to execute the workflow step")
        self.step = load_fetch_step()
        self.tmp = RetryingTemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.record = self.root / "record.json"
        stub = self.root / "bin" / "git"
        stub.parent.mkdir()
        stub.write_text(
            STUB_SOURCE.format(python=sys.executable, variable=TOKEN_VARIABLE),
            encoding="utf-8")
        stub.chmod(stub.stat().st_mode | stat.S_IXUSR)

    def run_step(self, head_repository: str, token: str) -> dict:
        """Execute the step script and return what the git stub recorded."""
        path = os.pathsep.join(
            [str(self.root / "bin"), os.environ.get("PATH", "")])
        environment = {
            "PATH": path,
            "STUB_RECORD": str(self.record),
            "PR_HEAD_REPO_URL": f"https://github.com/{head_repository}.git",
            "HEAD_REPO_FULL_NAME": head_repository,
            "BASE_REPOSITORY": BASE_REPOSITORY,
            "HEAD_SHA": HEAD_SHA,
            TOKEN_VARIABLE: token,
        }
        result = subprocess.run(
            [self.bash, "-c", self.step["run"]], cwd=self.root,
            env=environment, capture_output=True, text=True, check=False,
            timeout=SCRIPT_TIMEOUT_SECONDS)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(token or SYNTHETIC_TOKEN, result.stdout + result.stderr)
        return json.loads(self.record.read_text(encoding="utf-8"))


class SameRepositoryFetchTest(FetchCredentialFixture):
    """A head in the base repository fetches with the workflow token."""

    def test_the_fetch_receives_a_basic_credential_header(self):
        record = self.run_step(BASE_REPOSITORY, SYNTHETIC_TOKEN)
        encoded = base64.b64encode(
            f"x-access-token:{SYNTHETIC_TOKEN}".encode("utf-8")).decode("ascii")
        self.assertEqual(record["config"]["GIT_CONFIG_COUNT"], "1")
        self.assertEqual(record["config"]["GIT_CONFIG_KEY_0"], EXTRAHEADER_KEY)
        self.assertEqual(
            record["config"]["GIT_CONFIG_VALUE_0"],
            f"AUTHORIZATION: basic {encoded}")

    def test_the_fetch_targets_origin_at_the_head_revision(self):
        record = self.run_step(BASE_REPOSITORY, SYNTHETIC_TOKEN)
        self.assertEqual(
            record["arguments"], ["fetch", "--no-tags", "origin", HEAD_SHA])

    def test_the_token_stays_out_of_the_argument_vector(self):
        record = self.run_step(BASE_REPOSITORY, SYNTHETIC_TOKEN)
        self.assertNotIn(SYNTHETIC_TOKEN, " ".join(record["arguments"]))

    def test_the_raw_token_variable_does_not_reach_git(self):
        record = self.run_step(BASE_REPOSITORY, SYNTHETIC_TOKEN)
        self.assertIsNone(record["token_variable"])

    def test_an_empty_token_adds_no_credential(self):
        record = self.run_step(BASE_REPOSITORY, "")
        self.assertEqual(record["config"], {})


class ForkFetchTest(FetchCredentialFixture):
    """A fork head fetch never receives the workflow token."""

    def test_the_fork_fetch_carries_no_credential(self):
        record = self.run_step(FORK_REPOSITORY, SYNTHETIC_TOKEN)
        self.assertEqual(record["config"], {})
        self.assertIsNone(record["token_variable"])

    def test_the_fork_fetch_targets_the_fork_url(self):
        record = self.run_step(FORK_REPOSITORY, SYNTHETIC_TOKEN)
        self.assertEqual(
            record["arguments"],
            ["fetch", "--no-tags",
             f"https://github.com/{FORK_REPOSITORY}.git", HEAD_SHA])


class FetchStepWiringTest(unittest.TestCase):
    """The workflow hands the token to the fetch step alone."""

    def test_the_fetch_step_receives_the_workflow_token(self):
        step = load_fetch_step()
        self.assertEqual(step["env"][TOKEN_VARIABLE], "${{ github.token }}")

    def test_the_checkout_still_drops_its_credentials(self):
        with REVIEW_PATH.open(encoding="utf-8") as handle:
            workflow = yaml.safe_load(handle)
        checkouts = [
            step for step in workflow["jobs"]["review"]["steps"]
            if str(step.get("uses", "")).startswith("actions/checkout@")]
        self.assertTrue(checkouts)
        for step in checkouts:
            with self.subTest(step=step.get("name")):
                self.assertIs(step["with"]["persist-credentials"], False)


if __name__ == "__main__":
    unittest.main()
