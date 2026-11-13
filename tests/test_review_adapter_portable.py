#!/usr/bin/env python3
"""Behavioral tests for the review adapter scripts that adopters copy.

The file imports only `ci/` and `scripts/` modules. Adopting repositories
copy it unchanged with `ci/build_pr_case.py`, `ci/call_model.py`, and
`scripts/check_pr_review_response.py`.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from ci import build_pr_case
from ci import call_model
from scripts.check_pr_review_response import ResponseError, validate_response

ACTIVE_BUDGET_TOKENS = 100
LARGE_BUDGET_TOKENS = 1000
OLLAMA_ENDPOINT = "https://ollama.com/api"
OVERFLOW_BODY = b'{"error": "prompt is too long: 9000 tokens > 8000 maximum"}'
UNRELATED_BODY = b'{"error": "invalid value for field: temperature"}'
BOUNDED_READ_LIMIT_BYTES = 64
SUBPROCESS_TIMEOUT_SECONDS = 20


def _config(large: bool = True) -> dict:
    """Return a provider registry with an optional large-input profile."""
    config = {
        "active_provider": "ollama",
        "providers": {"ollama": {
            "protocol": "ollama", "endpoint": OLLAMA_ENDPOINT,
            "model": "review-model", "max_input_tokens": ACTIVE_BUDGET_TOKENS,
        }},
    }
    if large:
        config["large_input_provider"] = "ollama-large"
        config["providers"]["ollama-large"] = {
            "protocol": "ollama", "endpoint": OLLAMA_ENDPOINT,
            "model": "large-model", "max_input_tokens": LARGE_BUDGET_TOKENS,
        }
    return config


def _http_error(code: int, body: bytes = b"") -> HTTPError:
    """Return a provider rejection carrying one response body."""
    return HTTPError(OLLAMA_ENDPOINT, code, "rejected", {}, io.BytesIO(body))


class _FakeResponse:
    """Minimal urlopen response carrying one Ollama chat reply."""

    def __init__(self, text: str):
        self.headers = {}
        self._raw = json.dumps({"message": {"content": text}}).encode("utf-8")

    def read(self, _limit: int) -> bytes:
        """Return the encoded reply."""
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


def _call_with_responses(responses: list, large: bool = True,
                         models: list[str] | None = None) -> str:
    """Run call_model against scripted provider results.

    Append the model name of every request sent to models when given.
    """
    sent = models if models is not None else []

    def fake_urlopen(request, timeout):
        del timeout
        sent.append(json.loads(request.data.decode("utf-8"))["model"])
        result = responses.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result

    with patch.dict("os.environ", {"MODEL_API_KEY": "synthetic"}), \
            patch.object(call_model, "_load_config",
                         return_value=_config(large=large)), \
            patch.object(call_model, "urlopen", fake_urlopen):
        return call_model.call_model("p", "PR", "c")


class ProfileSelectionTest(unittest.TestCase):
    """select_profile picks the smallest configured model that fits."""

    def _select(self, tokens: int, large: bool = True) -> dict:
        with patch.object(call_model, "_load_config",
                          return_value=_config(large=large)):
            return call_model.select_profile(tokens)

    def test_input_within_active_budget_uses_active_provider(self) -> None:
        """An estimate at the active budget stays on the active model."""
        self.assertEqual(self._select(ACTIVE_BUDGET_TOKENS)["model"], "review-model")

    def test_input_over_active_budget_uses_large_provider(self) -> None:
        """An estimate above the active budget routes to the large model."""
        self.assertEqual(
            self._select(ACTIVE_BUDGET_TOKENS + 1)["model"], "large-model")

    def test_input_over_every_budget_is_capacity_error(self) -> None:
        """An estimate above every budget raises the capacity error."""
        with self.assertRaises(call_model.InputTooLargeError):
            self._select(LARGE_BUDGET_TOKENS + 1)

    def test_missing_large_provider_is_capacity_error(self) -> None:
        """Without a large model an oversized estimate has no target."""
        with self.assertRaises(call_model.InputTooLargeError):
            self._select(ACTIVE_BUDGET_TOKENS + 1, large=False)


class HttpRejectionRoutingTest(unittest.TestCase):
    """Only a context rejection retries on the large-input model."""

    def test_http_400_with_overflow_body_retries_on_large_model(self) -> None:
        """A 400 that names the context limit reroutes once."""
        models: list[str] = []
        text = _call_with_responses(
            [_http_error(400, OVERFLOW_BODY), _FakeResponse("large reply")],
            models=models)
        self.assertEqual(text, "large reply")
        self.assertEqual(models, ["review-model", "large-model"])

    def _assert_plain_rejection(self, body: bytes) -> None:
        """Assert a 400 with body fails on the active model alone."""
        models: list[str] = []
        with self.assertRaises(call_model.ProviderError) as raised:
            _call_with_responses(
                [_http_error(400, body), _FakeResponse("unused")], models=models)
        self.assertNotIsInstance(raised.exception, call_model.InputTooLargeError)
        self.assertEqual(
            str(raised.exception), "provider request failed with HTTP 400")
        self.assertEqual(models, ["review-model"])

    def test_http_400_with_unrelated_body_fails_without_reroute(self) -> None:
        """A 400 for any other reason fails on the active model."""
        self._assert_plain_rejection(UNRELATED_BODY)

    def test_http_400_with_empty_body_fails_without_reroute(self) -> None:
        """A 400 without a body carries no overflow evidence."""
        self._assert_plain_rejection(b"")

    def test_http_400_naming_a_token_count_field_fails_without_reroute(
            self) -> None:
        """A malformed token count parameter is not a context limit."""
        self._assert_plain_rejection(b'{"error": "invalid token count parameter"}')

    def test_http_400_with_ollama_context_size_wording_reroutes(self) -> None:
        """Ollama and llama.cpp report overflow as the context size."""
        body = (b'{"error": "the request exceeds the available context size, '
                b'try increasing it"}')
        models: list[str] = []
        text = _call_with_responses(
            [_http_error(400, body), _FakeResponse("large reply")], models=models)
        self.assertEqual(text, "large reply")
        self.assertEqual(models, ["review-model", "large-model"])

    def test_http_400_overflow_marker_matches_case_insensitively(self) -> None:
        """Provider wording varies in letter case."""
        body = b'{"error": {"message": "Maximum Context length is 8192"}}'
        text = _call_with_responses(
            [_http_error(400, body), _FakeResponse("large reply")])
        self.assertEqual(text, "large reply")

    def test_http_400_overflow_body_without_large_model_is_capacity_error(
            self) -> None:
        """A context rejection with no larger model is a capacity failure."""
        with self.assertRaises(call_model.InputTooLargeError):
            _call_with_responses([_http_error(400, OVERFLOW_BODY)], large=False)

    def test_http_413_retries_without_body_evidence(self) -> None:
        """413 always means the request was too large."""
        text = _call_with_responses(
            [_http_error(413), _FakeResponse("large reply")])
        self.assertEqual(text, "large reply")

    def test_rejection_message_omits_the_provider_body(self) -> None:
        """Provider bodies stay out of error messages and logs."""
        with self.assertRaises(call_model.ProviderError) as raised:
            _call_with_responses([_http_error(400, UNRELATED_BODY)])
        self.assertNotIn("temperature", str(raised.exception))


class CapacityExitCodeTest(unittest.TestCase):
    """main returns the capacity exit code when no model can hold the input."""

    def test_capacity_error_returns_capacity_exit_code(self) -> None:
        """The workflow reads exit code 3 as a NEEDS-HUMAN capacity verdict."""
        with tempfile.TemporaryDirectory() as directory:
            prompt_path = Path(directory) / "prompt.txt"
            case_path = Path(directory) / "case.txt"
            prompt_path.write_text("p", encoding="utf-8")
            case_path.write_text(
                "c" * (call_model.CHARS_PER_TOKEN_ESTIMATE * 2 * LARGE_BUDGET_TOKENS),
                encoding="utf-8")
            environment = {
                "MODEL_API_KEY": "synthetic",
                "AUDIT_PROMPT_FILE": str(prompt_path),
                "CASE_TEXT_FILE": str(case_path),
            }
            with patch.dict("os.environ", environment), \
                    patch.object(call_model, "_load_config",
                                 return_value=_config()), \
                    contextlib.redirect_stderr(io.StringIO()):
                exit_code = call_model.main()
        self.assertEqual(exit_code, 3)
        self.assertEqual(call_model.CAPACITY_EXIT_CODE, 3)


class BoundedDiffReadTest(unittest.TestCase):
    """_read_bounded_stdout returns bounded output or rejects it."""

    def _emit(self, byte_count: int) -> list[str]:
        """Return a command that writes byte_count bytes to stdout."""
        return [sys.executable, "-c",
                f"import sys; sys.stdout.write('x' * {byte_count})"]

    def test_output_within_bound_is_returned(self) -> None:
        """Output at the bound is returned whole."""
        output = build_pr_case._read_bounded_stdout(
            self._emit(BOUNDED_READ_LIMIT_BYTES), BOUNDED_READ_LIMIT_BYTES,
            timeout=SUBPROCESS_TIMEOUT_SECONDS)
        self.assertEqual(output, "x" * BOUNDED_READ_LIMIT_BYTES)

    def test_output_over_bound_raises_diff_too_large(self) -> None:
        """One byte over the bound is rejected."""
        with self.assertRaises(build_pr_case.DiffTooLargeError):
            build_pr_case._read_bounded_stdout(
                self._emit(BOUNDED_READ_LIMIT_BYTES + 1), BOUNDED_READ_LIMIT_BYTES,
                timeout=SUBPROCESS_TIMEOUT_SECONDS)

    def test_failing_command_raises_runtime_error(self) -> None:
        """A nonzero exit is a failure, not an empty diff."""
        command = [sys.executable, "-c", "raise SystemExit(1)"]
        with self.assertRaises(RuntimeError):
            build_pr_case._read_bounded_stdout(
                command, BOUNDED_READ_LIMIT_BYTES,
                timeout=SUBPROCESS_TIMEOUT_SECONDS)

    def test_command_past_timeout_raises_runtime_error(self) -> None:
        """A command that outlives the timeout is killed and reported."""
        command = [sys.executable, "-c", "import time; time.sleep(30)"]
        with self.assertRaisesRegex(RuntimeError, "timed out"):
            build_pr_case._read_bounded_stdout(
                command, BOUNDED_READ_LIMIT_BYTES, timeout=0.5)


class NarrationBoundaryTest(unittest.TestCase):
    """The validator rejects narration and accepts impersonal statements."""

    def _response(self, report: str) -> str:
        payload = {"mode": "PR", "verdict": "APPROVE", "findings": []}
        return "\n".join([
            report,
            "VERDICT: APPROVE",
            "VERDICT_JSON: " + json.dumps(payload),
        ])

    def test_impersonal_statements_remain_valid(self) -> None:
        """Abbreviations and section labels are not first-person narration."""
        statements = (
            "i.e. the diff adds a test.",
            "Trace: base to sink is parameterized.",
            "Inspect results: none.",
            "Need to know: none.",
            "Items checked: 4.",
        )
        for statement in statements:
            with self.subTest(statement=statement):
                verdict, _payload = validate_response(self._response(statement))
                self.assertEqual(verdict, "APPROVE")

    def test_first_person_narration_fails(self) -> None:
        """First-person openers and self-directed steps stay rejected."""
        statements = (
            "I need to inspect the archive helper.",
            "We trace the filename into the command.",
            "- I checked the caller.",
            "Let me trace the filename into the command.",
            "Now I inspect the caller.",
            "I'll inspect the caller.",
            "I've traced the call.",
        )
        for statement in statements:
            with self.subTest(statement=statement):
                with self.assertRaisesRegex(ResponseError, "process narration"):
                    validate_response(self._response(statement))


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parent.parent)
    unittest.main()
