#!/usr/bin/env python3
"""Tests for the provider adapter and shell-free command runner."""

import contextlib
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from ci import call_model
from ci import run_model_command

REPO_ROOT = Path(__file__).resolve().parents[1]


class ProviderRequestTest(unittest.TestCase):
    """Provider requests carry structured data and exact endpoints."""

    def _profile(self, protocol):
        return {
            "protocol": protocol,
            "endpoint": {
                "ollama": "https://ollama.com/api",
                "openai-compatible": "https://api.openai.com/v1",
                "anthropic": "https://api.anthropic.com/v1",
                "google": "https://generativelanguage.googleapis.com/v1beta",
            }[protocol],
            "model": "review-model",
            "max_output_tokens": 128,
        }

    def test_ollama_request_uses_json_and_bearer_auth(self):
        request = call_model._build_request(
            self._profile("ollama"), "policy", '{"mode":"PR"}', "secret"
        )
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(request.full_url, "https://ollama.com/api/chat")
        self.assertEqual(request.headers["Authorization"], "Bearer secret")
        self.assertEqual(body["messages"][1]["content"], '{"mode":"PR"}')
        self.assertFalse(body["stream"])

    def test_native_response_extractors_cover_all_protocols(self):
        responses = {
            "ollama": {"message": {"content": "ollama"}},
            "openai-compatible": {"choices": [{"message": {"content": "openai"}}]},
            "anthropic": {"content": [{"type": "text", "text": "anthropic"}]},
            "google": {
                "candidates": [{"content": {"parts": [{"text": "google"}]}}]
            },
        }
        for protocol, response in responses.items():
            with self.subTest(protocol=protocol):
                self.assertEqual(
                    call_model._extract_text(protocol, response), protocol.split("-")[0]
                )

    def test_unapproved_endpoint_is_rejected(self):
        with self.assertRaises(call_model.ProviderError):
            call_model._validate_endpoint("https://attacker.example/api")

    def test_protocol_endpoint_pairs_are_fixed(self):
        with patch.object(call_model, "_load_config", return_value={
            "active_provider": "ollama",
            "providers": {"ollama": {
                "protocol": "ollama",
                "endpoint": "https://api.openai.com/v1",
                "model": "review-model",
            }},
        }):
            with self.assertRaises(call_model.ProviderError):
                call_model._load_profile()

    def test_large_input_is_rejected_before_request(self):
        with patch.dict("os.environ", {"MODEL_API_KEY": "secret"}):
            with self.assertRaises(call_model.ProviderError):
                call_model.call_model("x", "PR", "x" * call_model.MAX_INPUT_CHARS)


class RetryDelayTest(unittest.TestCase):
    """The single retry waits a bounded, jittered delay honoring Retry-After."""

    def test_retry_after_header_is_honored(self):
        self.assertEqual(call_model._retry_delay_seconds("5"), 5.0)

    def test_retry_after_header_is_bounded(self):
        self.assertEqual(
            call_model._retry_delay_seconds("999"),
            call_model.MAX_RETRY_DELAY_SECONDS,
        )

    def test_negative_retry_after_falls_back_to_the_jittered_default(self):
        delay = call_model._retry_delay_seconds("-1")
        self.assertGreaterEqual(delay, call_model.RETRY_DELAY_SECONDS)
        self.assertLessEqual(
            delay,
            call_model.RETRY_DELAY_SECONDS + call_model.RETRY_DELAY_JITTER_SECONDS,
        )

    def test_invalid_retry_after_falls_back_to_the_jittered_default(self):
        delay = call_model._retry_delay_seconds("not-a-number")
        self.assertGreaterEqual(delay, call_model.RETRY_DELAY_SECONDS)
        self.assertLessEqual(
            delay,
            call_model.RETRY_DELAY_SECONDS + call_model.RETRY_DELAY_JITTER_SECONDS,
        )

    def test_missing_retry_after_uses_the_jittered_default(self):
        delay = call_model._retry_delay_seconds(None)
        self.assertGreaterEqual(delay, call_model.RETRY_DELAY_SECONDS)
        self.assertLessEqual(
            delay,
            call_model.RETRY_DELAY_SECONDS + call_model.RETRY_DELAY_JITTER_SECONDS,
        )


class CommandValidationTest(unittest.TestCase):
    """Adapter commands cannot introduce shell interpretation."""

    def test_python_script_command_becomes_an_argument_array(self):
        arguments = run_model_command.parse_command("python3 ci/call_model.py")
        self.assertEqual(arguments[0], sys.executable)
        self.assertEqual(Path(arguments[1]), REPO_ROOT / "ci" / "call_model.py")

    def test_shell_syntax_is_rejected(self):
        for command in (
            "python3 ci/call_model.py; whoami",
            "python3 ci/call_model.py | sh",
            "python3 ci/call_model.py $(whoami)",
            "python3 -c print(1)",
        ):
            with self.subTest(command=command):
                with self.assertRaises(ValueError):
                    run_model_command.parse_command(command)

    def test_script_must_stay_inside_repository(self):
        with self.assertRaises(ValueError):
            run_model_command.parse_command("python3 ../outside.py")


class FailureDiagnosticsTest(unittest.TestCase):
    """Adapter failures forward sanitized diagnostics."""

    def _run_failure(self, stderr):
        completed = subprocess.CompletedProcess(
            args=["adapter"], returncode=1, stdout="", stderr=stderr
        )
        with patch.dict(
            "os.environ", {"MODEL_CALL_COMMAND": "python3 ci/call_model.py"}
        ):
            with patch.object(
                run_model_command.subprocess, "run", return_value=completed
            ):
                buffer = io.StringIO()
                with contextlib.redirect_stderr(buffer):
                    status = run_model_command.main()
        return status, buffer.getvalue()

    def test_failure_forwards_adapter_reason(self):
        status, output = self._run_failure(
            "model call failed: provider request failed with HTTP 401\n"
        )
        self.assertEqual(status, 1)
        self.assertIn("model command failed", output)
        self.assertIn("HTTP 401", output)

    def test_diagnostics_redact_credential_assignments(self):
        sanitized = run_model_command.sanitize_diagnostics(
            "token=abc123\nAuthorization: topsecret\n"
        )
        self.assertNotIn("abc123", sanitized)
        self.assertNotIn("topsecret", sanitized)

    def test_diagnostics_strip_control_characters(self):
        sanitized = run_model_command.sanitize_diagnostics("ok\x1b[31mred\x1b[0m")
        self.assertNotIn("\x1b", sanitized)


if __name__ == "__main__":
    unittest.main()
