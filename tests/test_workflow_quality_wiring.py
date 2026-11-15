#!/usr/bin/env python3
"""Workflow and Makefile wiring from the quality review.

The CI prose step and the local lint target check one file list. The
Python toolchain carries a pinned minor version. The review callers keep
one pin per reviewer and no dead concurrency terms.
"""
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
CI_WORKFLOW = WORKFLOWS / "ci.yml"
MAKEFILE = ROOT / "Makefile"
PINNED_PYTHON_WORKFLOWS = (
    "ci.yml",
    "scheduled-validation.yml",
    "immutable-conflict-check.yml",
)
PYTHON_MINOR_PATTERN = re.compile(r"3\.\d+")


def _read(path: Path) -> str:
    """Return one repository file as text."""
    return path.read_text(encoding="utf-8")


def _prose_files() -> list[str]:
    """Return the PROSE_FILES entries from the Makefile."""
    text = _read(MAKEFILE).replace("\\\n", " ")
    match = re.search(r"^PROSE_FILES = (.+)$", text, re.MULTILINE)
    if match is None:
        raise AssertionError("Makefile defines no PROSE_FILES")
    return match.group(1).split()


class ProseFileListTest(unittest.TestCase):
    """make lint is the single prose check in CI and locally."""

    def test_prose_files_cover_every_documentation_page(self):
        expected = {
            path.relative_to(ROOT).as_posix()
            for pattern in ("docs/*.md", "docs/agent-policy/*.md")
            for path in ROOT.glob(pattern)
        }
        self.assertTrue(expected)
        self.assertLessEqual(expected, set(_prose_files()))

    def test_lint_target_runs_the_blocking_ascii_check(self):
        self.assertIn(
            "$(PYTHON) scripts/check_ascii.py $(PROSE_FILES)", _read(MAKEFILE))

    def test_ci_prose_step_calls_make_lint(self):
        workflow = yaml.safe_load(_read(CI_WORKFLOW))
        steps = workflow["jobs"]["checks"]["steps"]
        prose = [step for step in steps if step.get("name") == "Prose style"]
        self.assertEqual(len(prose), 1)
        self.assertEqual(prose[0]["run"].strip(), "make lint PYTHON=python3")

    def test_ci_carries_no_shellcheck_suppression(self):
        self.assertNotIn("shellcheck disable", _read(CI_WORKFLOW))


class PythonPinTest(unittest.TestCase):
    """Every setup-python step names one Python minor version."""

    def test_setup_python_steps_pin_a_minor_version(self):
        for name in PINNED_PYTHON_WORKFLOWS:
            workflow = yaml.safe_load(_read(WORKFLOWS / name))
            for job in workflow["jobs"].values():
                for step in job.get("steps", []):
                    if "setup-python" not in step.get("uses", ""):
                        continue
                    with self.subTest(workflow=name):
                        version = step["with"]["python-version"]
                        self.assertIsInstance(version, str)
                        self.assertRegex(version, PYTHON_MINOR_PATTERN)


class ReviewCallerTest(unittest.TestCase):
    """Review callers keep consistent pins and live expressions."""

    def test_security_caller_concurrency_uses_workflow_run_only(self):
        workflow = yaml.safe_load(_read(WORKFLOWS / "security-review-pr.yml"))
        group = workflow["concurrency"]["group"]
        self.assertEqual(
            group, "security-review-${{ github.event.workflow_run.head_sha }}")

    def test_security_caller_jobs_share_one_audit_ref(self):
        workflow = yaml.safe_load(_read(WORKFLOWS / "security-review-pr.yml"))
        refs = {
            job["with"]["audit_ref"]
            for job in workflow["jobs"].values()
            if "audit_ref" in job.get("with", {})
        }
        self.assertEqual(len(refs), 1)

    def test_quality_caller_declares_matches_once(self):
        text = _read(WORKFLOWS / "quality-review-pr.yml")
        self.assertEqual(text.count("const matches ="), 1)

    def test_model_command_description_states_the_contract(self):
        workflow = yaml.safe_load(_read(WORKFLOWS / "security-review.yml"))
        on_block = workflow.get("on", workflow.get(True))
        description = on_block["workflow_call"]["inputs"][
            "model_call_command"]["description"]
        self.assertIn("python", description)
        self.assertIn("python3", description)
        self.assertIn(".py", description)
        self.assertNotIn("Shell command", description)


class CiHeaderTest(unittest.TestCase):
    """The ci.yml header describes the steps the workflow runs."""

    def test_header_names_the_actions_and_the_hashed_install(self):
        header = _read(CI_WORKFLOW).split("\non:", 1)[0]
        self.assertIn("actions/setup-python", header)
        self.assertIn("requirements-checkers.txt", header)
        self.assertNotIn("No dependency installation", header)


if __name__ == "__main__":
    unittest.main()
