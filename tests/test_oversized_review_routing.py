#!/usr/bin/env python3
"""Oversized review input routes to a large model or a capacity verdict."""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

import yaml

from ci import build_pr_case
from ci import call_model
from scripts.check_pr_review_response import validate_response

try:
    from tests.test_ci_adapter_fixes import (
        OVERSIZED_DIFF_LIMIT_BYTES,
        _two_commit_repository,
    )
except ImportError:
    from test_ci_adapter_fixes import (
        OVERSIZED_DIFF_LIMIT_BYTES,
        _two_commit_repository,
    )

REPO_ROOT = Path(__file__).resolve().parent.parent
REVIEW_PATH = REPO_ROOT / ".github" / "workflows" / "security-review.yml"
BUILD_STEP = "Build provenance-labeled case text"
MODEL_STEP = "Run model call"
REPORT_STEP = "Write capacity review report"
VALIDATE_STEP = "Validate report structure"
SCRIPT_TIMEOUT_SECONDS = 20
ACTIVE_BUDGET_TOKENS = 100
LARGE_BUDGET_TOKENS = 1000
OLLAMA_ENDPOINT = "https://ollama.com/api"


def _config(active_budget: int | None = ACTIVE_BUDGET_TOKENS,
            large: bool = True) -> dict:
    """Return a provider registry with an optional large-input profile."""
    active = {"protocol": "ollama", "endpoint": OLLAMA_ENDPOINT,
              "model": "review-model"}
    if active_budget is not None:
        active["max_input_tokens"] = active_budget
    config = {"active_provider": "ollama", "providers": {"ollama": active}}
    if large:
        config["large_input_provider"] = "ollama-large"
        config["providers"]["ollama-large"] = {
            "protocol": "ollama", "endpoint": OLLAMA_ENDPOINT,
            "model": "large-model", "max_input_tokens": LARGE_BUDGET_TOKENS,
        }
    return config


class _FakeResponse:
    """Minimal urlopen response carrying one Ollama chat reply."""

    def __init__(self, text: str):
        self.headers = {}
        self._raw = json.dumps({"message": {"content": text}}).encode("utf-8")

    def read(self, _limit: int) -> bytes:
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


class ProfileSelectionTest(unittest.TestCase):
    """select_profile picks the smallest configured model that fits."""

    def _select(self, tokens: int, **config_options) -> dict:
        with patch.object(call_model, "_load_config",
                          return_value=_config(**config_options)):
            return call_model.select_profile(tokens)

    def test_input_within_active_budget_uses_active_provider(self):
        self.assertEqual(self._select(ACTIVE_BUDGET_TOKENS)["name"], "ollama")

    def test_input_over_active_budget_uses_large_provider(self):
        profile = self._select(ACTIVE_BUDGET_TOKENS + 1)
        self.assertEqual(profile["name"], "ollama-large")
        self.assertEqual(profile["model"], "large-model")

    def test_input_over_every_budget_raises_capacity_error(self):
        with self.assertRaises(call_model.InputTooLargeError):
            self._select(LARGE_BUDGET_TOKENS + 1)

    def test_missing_budget_keeps_the_active_provider(self):
        profile = self._select(10 * LARGE_BUDGET_TOKENS, active_budget=None)
        self.assertEqual(profile["name"], "ollama")

    def test_missing_large_provider_raises_capacity_error(self):
        with self.assertRaises(call_model.InputTooLargeError):
            self._select(ACTIVE_BUDGET_TOKENS + 1, large=False)

    def test_capacity_error_is_a_provider_error(self):
        self.assertTrue(
            issubclass(call_model.InputTooLargeError, call_model.ProviderError))

    def test_estimate_rounds_up(self):
        self.assertEqual(call_model.estimate_tokens("ab", "cd"), 2)


class ContextOverflowFallbackTest(unittest.TestCase):
    """A rejected request on the active model retries on the large model."""

    def _http_error(self, code: int) -> HTTPError:
        return HTTPError(OLLAMA_ENDPOINT, code, "rejected", {}, None)

    def _call(self, side_effect, **config_options):
        requests = []

        def fake_urlopen(request, timeout):
            del timeout
            requests.append(json.loads(request.data.decode("utf-8")))
            result = side_effect.pop(0)
            if isinstance(result, BaseException):
                raise result
            return result

        with patch.dict("os.environ", {"MODEL_API_KEY": "synthetic"}), \
                patch.object(call_model, "_load_config",
                             return_value=_config(**config_options)), \
                patch.object(call_model, "urlopen", fake_urlopen):
            text = call_model.call_model("p", "PR", "c")
        return text, requests

    def test_http_400_retries_on_large_model(self):
        text, requests = self._call(
            [self._http_error(400), _FakeResponse("large reply")])
        self.assertEqual(text, "large reply")
        self.assertEqual(
            [body["model"] for body in requests], ["review-model", "large-model"])

    def test_http_413_retries_on_large_model(self):
        text, _requests = self._call(
            [self._http_error(413), _FakeResponse("large reply")])
        self.assertEqual(text, "large reply")

    def test_http_400_without_large_model_is_capacity_error(self):
        with self.assertRaises(call_model.InputTooLargeError):
            self._call([self._http_error(400)], large=False)

    def test_http_413_when_large_budget_is_exceeded_is_capacity_error(self):
        # The active profile has no budget and accepts any estimate. The
        # large budget cannot hold it, so no retry target exists.
        requests = []

        def fake_urlopen(request, timeout):
            del timeout
            requests.append(json.loads(request.data.decode("utf-8")))
            raise self._http_error(413)

        case_text = "c" * (3 * LARGE_BUDGET_TOKENS)
        with patch.dict("os.environ", {"MODEL_API_KEY": "synthetic"}), \
                patch.object(call_model, "_load_config",
                             return_value=_config(active_budget=None)), \
                patch.object(call_model, "urlopen", fake_urlopen):
            with self.assertRaises(call_model.InputTooLargeError):
                call_model.call_model("p", "PR", case_text)
        self.assertEqual([body["model"] for body in requests], ["review-model"])

    def test_large_model_rejection_after_fallback_is_capacity_error(self):
        with self.assertRaises(call_model.InputTooLargeError):
            self._call([self._http_error(400), self._http_error(413)])

    def test_large_model_rejection_on_direct_route_is_capacity_error(self):
        # The case is routed to the large profile by size alone. The
        # estimate for "p" plus a long case exceeds the active budget.
        requests = []

        def fake_urlopen(request, timeout):
            del timeout
            requests.append(json.loads(request.data.decode("utf-8")))
            raise self._http_error(400)

        case_text = "c" * (3 * ACTIVE_BUDGET_TOKENS)
        with patch.dict("os.environ", {"MODEL_API_KEY": "synthetic"}), \
                patch.object(call_model, "_load_config",
                             return_value=_config()), \
                patch.object(call_model, "urlopen", fake_urlopen):
            with self.assertRaises(call_model.InputTooLargeError):
                call_model.call_model("p", "PR", case_text)
        self.assertEqual([body["model"] for body in requests], ["large-model"])

    def test_http_401_does_not_switch_models(self):
        with self.assertRaises(call_model.ProviderError):
            self._call([self._http_error(401)])


class CapacityExitCodeTest(unittest.TestCase):
    """Both scripts report a capacity failure with a distinct exit code."""

    def test_adapter_returns_capacity_exit_code(self):
        with tempfile.TemporaryDirectory() as temp:
            prompt = Path(temp) / "prompt.txt"
            case = Path(temp) / "case.txt"
            prompt.write_text("p", encoding="utf-8")
            case.write_text("x" * (4 * LARGE_BUDGET_TOKENS), encoding="utf-8")
            environment = {
                "AUDIT_PROMPT_FILE": str(prompt),
                "CASE_TEXT_FILE": str(case),
                "MODEL_API_KEY": "synthetic",
            }
            stderr = io.StringIO()
            with patch.dict("os.environ", environment), \
                    patch.object(call_model, "_load_config",
                                 return_value=_config()), \
                    contextlib.redirect_stderr(stderr):
                code = call_model.main()
        self.assertEqual(code, call_model.CAPACITY_EXIT_CODE)
        self.assertIn("exceeds", stderr.getvalue())
        self.assertNotIn("xxxx", stderr.getvalue())

    def test_case_builder_returns_capacity_exit_code(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            base, head = _two_commit_repository(repo)
            event_path = root / "event.json"
            event_path.write_text(
                json.dumps({"pull_request": {"title": "T", "body": "B"}}),
                encoding="utf-8",
            )
            environment = {
                "EVENT_PATH": str(event_path),
                "BASE_SHA": base,
                "HEAD_SHA": head,
            }
            previous = os.getcwd()
            with patch.dict("os.environ", environment), patch.object(
                build_pr_case, "MAX_DIFF_BYTES", OVERSIZED_DIFF_LIMIT_BYTES
            ), contextlib.redirect_stderr(io.StringIO()):
                os.chdir(repo)
                try:
                    code = build_pr_case.main()
                finally:
                    os.chdir(previous)
            self.assertFalse((repo / "case_text.txt").exists())
        self.assertEqual(code, build_pr_case.CAPACITY_EXIT_CODE)


class CapacityWorkflowStepsTest(unittest.TestCase):
    """The workflow turns a capacity exit code into a recorded verdict."""

    def setUp(self):
        self.bash = shutil.which("bash")
        self.python = shutil.which("python3")
        if self.bash is None or self.python is None:
            self.skipTest("bash and python3 are required to run workflow steps")
        document = yaml.safe_load(REVIEW_PATH.read_text(encoding="utf-8"))
        self.steps = document["jobs"]["review"]["steps"]

    def _step(self, name: str) -> dict:
        for step in self.steps:
            if step.get("name") == name:
                return step
        raise AssertionError(f"workflow step {name!r} is missing")

    def _run_step(self, name: str, directory: Path,
                  stubs: dict[str, str]) -> tuple[int, str]:
        for relative, source in stubs.items():
            path = directory / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source, encoding="utf-8")
        output = directory / "github_output.txt"
        output.write_text("", encoding="utf-8")
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "GITHUB_OUTPUT": str(output),
            "MODEL_CALL_COMMAND": "python3 ci/call_model.py",
        }
        result = subprocess.run(
            [self.bash, "-c", self._step(name)["run"]], cwd=directory,
            env=environment, capture_output=True, text=True, check=False,
            timeout=SCRIPT_TIMEOUT_SECONDS,
        )
        return result.returncode, output.read_text(encoding="utf-8")

    def _exit_stub(self, code: int) -> str:
        return f"import sys\nsys.exit({code})\n"

    def test_build_step_maps_capacity_exit_to_output(self):
        expectations = {0: (0, False), 1: (1, False), 3: (0, True)}
        for stub_code, (step_code, oversized) in expectations.items():
            with self.subTest(stub_code=stub_code), \
                    tempfile.TemporaryDirectory() as temp:
                code, output = self._run_step(
                    BUILD_STEP, Path(temp),
                    {"ci/build_pr_case.py": self._exit_stub(stub_code)})
                self.assertEqual(code, step_code)
                self.assertEqual("oversized=true" in output, oversized)

    def test_model_step_maps_capacity_exit_to_output(self):
        checker = (REPO_ROOT / "scripts" / "check_pr_review_response.py").read_text(
            encoding="utf-8")
        for stub_code, oversized in ((3, True), (1, False)):
            with self.subTest(stub_code=stub_code), \
                    tempfile.TemporaryDirectory() as temp:
                code, output = self._run_step(MODEL_STEP, Path(temp), {
                    "ci/run_model_command.py": self._exit_stub(stub_code),
                    "scripts/check_pr_review_response.py": checker,
                })
                self.assertEqual(code == 0, oversized)
                self.assertEqual("oversized=true" in output, oversized)

    def test_model_step_skips_an_oversized_case(self):
        self.assertIn("steps.case.outputs.oversized != 'true'",
                      self._step(MODEL_STEP)["if"])

    def test_report_step_runs_for_either_capacity_signal(self):
        condition = self._step(REPORT_STEP)["if"]
        self.assertIn("steps.case.outputs.oversized == 'true'", condition)
        self.assertIn("steps.model.outputs.oversized == 'true'", condition)

    def test_report_step_precedes_validation(self):
        names = [step.get("name") for step in self.steps]
        self.assertEqual(names.index(REPORT_STEP), names.index(MODEL_STEP) + 1)
        self.assertEqual(names.index(VALIDATE_STEP), names.index(REPORT_STEP) + 1)

    def test_report_is_a_valid_needs_human_response(self):
        with tempfile.TemporaryDirectory() as temp:
            code, _output = self._run_step(REPORT_STEP, Path(temp), {})
            response = (Path(temp) / "response.txt").read_text(encoding="utf-8")
        self.assertEqual(code, 0)
        verdict, payload = validate_response(response)
        self.assertEqual(verdict, "NEEDS-HUMAN")
        self.assertEqual(payload["findings"], [])


if __name__ == "__main__":
    unittest.main()
