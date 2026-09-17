#!/usr/bin/env python3
"""Workflow integrity tests.

Text-level assertions on .github/workflows/ci.yml and security-review.yml. No
YAML parser is available. Each assertion targets one regression the prose
rules call out: unpinned actions, inherited secrets, missing scripts, direct
interpolation of pull request content into shell commands, and a merge gate
that reads the wrong verdict.
"""
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CI_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
REVIEW_PATH = REPO_ROOT / ".github" / "workflows" / "security-review.yml"
CALLER_PATH = REPO_ROOT / ".github" / "workflows" / "security-review-pr.yml"
SHA_PIN_RE = re.compile(r"@[0-9a-f]{40}\b")
SCRIPT_REF_RE = re.compile(r"scripts/\w+\.py")
USES_LINE_RE = re.compile(r"^\s+uses:")
SECRETS_INHERIT_RE = re.compile(r"^\s+secrets:\s*inherit\b")

PR_INTERPOLATION_PATTERNS = (
    "${{ github.event.pull_request.title }}",
    "${{ github.event.pull_request.body }}",
)


class UsesPinningTest(unittest.TestCase):
    """Every action reference is pinned to a full commit SHA."""

    def test_every_uses_line_is_sha_pinned(self):
        for path in (CI_PATH, REVIEW_PATH):
            text = path.read_text(encoding="utf-8")
            uses_lines = [
                line for line in text.splitlines() if USES_LINE_RE.match(line)
            ]
            self.assertTrue(uses_lines)
            for line in uses_lines:
                with self.subTest(file=path.name, line=line.strip()):
                    self.assertRegex(line, SHA_PIN_RE)


class SecretsTest(unittest.TestCase):
    """The reusable workflow must not receive every caller secret."""

    def test_no_secrets_inherit(self):
        for path in (CI_PATH, REVIEW_PATH):
            text = path.read_text(encoding="utf-8")
            for line in text.splitlines():
                with self.subTest(file=path.name, line=line.strip()):
                    self.assertIsNone(SECRETS_INHERIT_RE.match(line))


class ScriptReferenceTest(unittest.TestCase):
    """Scripts ci.yml names exist on disk."""

    def test_referenced_scripts_exist(self):
        text = CI_PATH.read_text(encoding="utf-8")
        references = set(SCRIPT_REF_RE.findall(text))
        self.assertTrue(references)
        for reference in references:
            with self.subTest(script=reference):
                self.assertTrue((REPO_ROOT / reference).is_file())

    def test_ci_references_run_eval(self):
        text = CI_PATH.read_text(encoding="utf-8")
        self.assertIn("eval/run_eval.py", text)


class InterpolationSafetyTest(unittest.TestCase):
    """Pull request title and body reach shell through env vars only.

    Direct interpolation of pull request content into a run block executes
    attacker-controlled text as shell. The workflows assign it to an env
    var and the run block reads the var.
    """

    def _run_blocks(self, text: str) -> list:
        blocks = []
        for match in re.finditer(r"run: \|(.*?)(?=\n      - |\Z)", text, re.DOTALL):
            blocks.append(match.group(1))
        return blocks

    def test_pr_fields_not_interpolated_in_shell(self):
        for path in (CI_PATH, REVIEW_PATH):
            text = path.read_text(encoding="utf-8")
            for block in self._run_blocks(text):
                for pattern in PR_INTERPOLATION_PATTERNS:
                    with self.subTest(file=path.name, pattern=pattern):
                        self.assertNotIn(pattern, block)


class ReviewDedupeTest(unittest.TestCase):
    """One model call per head revision.

    Duplicate triggers for one head cancel. A head with a completed
    verdict-carrying check run skips the review entirely.
    """

    def setUp(self):
        self.caller = CALLER_PATH.read_text(encoding="utf-8")

    def test_parallel_runs_for_one_head_cancel(self):
        self.assertIn(
            "security-review-${{ github.event.workflow_run.head_sha }}",
            self.caller,
        )
        self.assertIn("cancel-in-progress: true", self.caller)

    def test_completed_verdict_skips_the_review(self):
        self.assertIn('check_name: "security-review"', self.caller)
        self.assertIn("already_reviewed", self.caller)
        self.assertIn("VERDICT: (APPROVE|BLOCK|NEEDS-HUMAN)", self.caller)

    def test_review_job_honors_the_dedupe_output(self):
        self.assertIn(
            "needs.resolve-pr.outputs.already_reviewed != 'true'", self.caller
        )


class CheckRunVisibilityTest(unittest.TestCase):
    """The review publishes a check run on the pull request head.

    A workflow_run review executes on the default branch. Without a check
    run on the head revision the result never appears in the pull request
    checks box. Assertions scope to the publish step block so a matching
    string elsewhere in the file cannot satisfy them. A JavaScript
    execution harness would need a new dependency, so the assertions stay
    text-level per the file convention.
    """

    def setUp(self):
        self.review = REVIEW_PATH.read_text(encoding="utf-8")
        self.caller = CALLER_PATH.read_text(encoding="utf-8")
        self.step = self.review.split("name: Publish check run", 1)[1]

    def test_review_job_grants_checks_write(self):
        self.assertIn("checks: write", self.review)

    def test_caller_grants_checks_write(self):
        self.assertIn("checks: write", self.caller)

    def test_check_run_targets_the_resolved_head(self):
        self.assertIn("github.rest.checks.create", self.step)
        self.assertIn("steps.resolve.outputs.head_sha", self.step)

    def test_check_run_publishes_on_every_outcome(self):
        self.assertIn("if: ${{ always() }}", self.step)

    def test_summary_sanitizes_the_model_influenced_verdict(self):
        self.assertIn("value.replace(", self.step)
        self.assertIn("slice(0, 200)", self.step)

    def test_publication_has_a_timeout_and_one_retry(self):
        self.assertIn("timeout-minutes: 1", self.step)
        self.assertIn("attempt < 2", self.step)

    def test_publication_failure_does_not_mask_a_passed_review(self):
        self.assertIn("core.warning(", self.step)


class ResponseRetryTest(unittest.TestCase):
    """A structurally invalid response earns one retry, not a failure."""

    def setUp(self):
        self.review = REVIEW_PATH.read_text(encoding="utf-8")
        self.model_step = self.review.split("name: Run model call", 1)[1].split(
            "name: Validate report structure", 1
        )[0]
        self.validation_step = self.review.split(
            "name: Validate report structure", 1
        )[1].split("name: Parse verdict", 1)[0]

    def test_model_step_retries_once_on_invalid_response(self):
        retry_pattern = (
            r"if ! python3 scripts/check_pr_review_response\.py response\.txt "
            r"> /dev/null; then\s+"
            r"echo \"first response failed validation; one retry\" >&2\s+"
            r"python3 ci/run_model_command\.py \"\$MODEL_CALL_COMMAND\" "
            r"> response\.txt"
        )
        self.assertRegex(self.model_step, retry_pattern)
        self.assertEqual(
            self.model_step.count("python3 ci/run_model_command.py"), 2
        )

    def test_validation_failure_logs_only_structural_error(self):
        self.assertIn("validation_error=", self.validation_step)
        self.assertIn("failed structural validation", self.validation_step)
        self.assertNotIn("tail -n 5", self.validation_step)
        self.assertNotIn("cut -c1-500", self.validation_step)


class CommentTargetTest(unittest.TestCase):
    """The review comment targets the resolved pull request number.

    A workflow_run event carries no context.issue payload. Reading
    context.issue.number posts to issues//comments and 404s.
    """

    def setUp(self):
        text = REVIEW_PATH.read_text(encoding="utf-8")
        self.step = text.split("name: Post PR comment", 1)[1]

    def test_comment_uses_the_resolved_pr_number(self):
        self.assertIn("process.env.PR_NUMBER", self.step)
        self.assertNotIn("context.issue.number", self.step)

    def test_comment_step_reads_the_resolve_output(self):
        self.assertIn("PR_NUMBER: ${{ steps.resolve.outputs.pr_number }}", self.step)


class VerdictGateTest(unittest.TestCase):
    """The merge gate reads the report's own verdict and holds on doubt."""

    def setUp(self):
        self.review = REVIEW_PATH.read_text(encoding="utf-8")
        step = self.review.split("name: Parse verdict", 1)[1]
        self.step = step.split("name: Post PR comment", 1)[0]

    def _grep_lines(self) -> list:
        return [
            line for line in self.step.splitlines()
            if "grep" in line and not line.lstrip().startswith("#")
        ]

    def test_gate_reads_the_last_verdict_line(self):
        """A quoted verdict earlier in the report must not win.

        A report quotes the diff under review. Reading the first match lets
        a planted VERDICT: APPROVE line in a pull request body decide the
        gate. Section 6 puts the authoritative verdict last.
        """
        self.assertIn("tail -1", self.step)
        self.assertNotIn("head -1", self.step)

    def _executable_lines(self) -> list:
        """Return the step's lines that run, excluding comments."""
        return [
            line for line in self.step.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

    def test_gate_blocks_on_needs_human(self):
        """An escalation is not a pass.

        AUDIT.md section 1.8 escalates to NEEDS-HUMAN where the review
        cannot determine safety. Treating that as unblocked merges the exact
        change the review declined to clear.

        Read the executable lines rather than the whole step. The comment
        above the case statement names NEEDS-HUMAN, so an assertion over the
        step text stays green after a revert to a BLOCK-only gate.
        """
        executable = self._executable_lines()
        self.assertTrue(any("NEEDS-HUMAN" in line for line in executable))

    def test_gate_reads_the_verdict_token_alone(self):
        """The reason must not decide the gate.

        Searching the whole line fails closed on
        'VERDICT: APPROVE - resolved earlier BLOCK findings' and fails open
        on 'VERDICT: REJECT', which matches no alternative and merges.
        """
        executable = "\n".join(self._executable_lines())
        self.assertIn("case ", executable)
        self.assertIn("APPROVE)", executable)
        self.assertNotIn("grep -qE 'BLOCK|NEEDS-HUMAN'", executable)

    def test_unrecognized_token_fails_the_step(self):
        """A malformed verdict is not a verdict.

        fail_on_block governs which verdicts block, not whether output
        carrying no valid verdict counts as a pass.
        """
        executable = "\n".join(self._executable_lines())
        self.assertIn("Unrecognized verdict token", executable)
        self.assertIn("exit 1", executable)

    def test_gate_reads_the_pr_mode_token_alone(self):
        """The workflow always runs PR mode, so only VERDICT: gates it.

        Accepting a RISK: line lets a report answering in another mode
        satisfy a merge gate that mode never addressed. File and Wholesale
        modes make no merge claim at all.
        """
        verdict_greps = [line for line in self._grep_lines() if "VERDICT" in line]
        self.assertEqual(len(verdict_greps), 1)
        self.assertIn("'^VERDICT:'", verdict_greps[0])
        self.assertNotIn("RISK", verdict_greps[0])


if __name__ == "__main__":
    unittest.main()
