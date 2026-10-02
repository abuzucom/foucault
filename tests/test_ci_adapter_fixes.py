#!/usr/bin/env python3
"""Tests for CI adapter bug fixes: model providers, thinking blocks, diff limit, sys import."""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from ci import build_pr_case
from ci import call_model


class GeminiThinkingConfigTest(unittest.TestCase):
    """Google requests disable thinking tokens and filter thought parts."""

    def setUp(self):
        self.profile = {
            "name": "google",
            "protocol": "google",
            "endpoint": "https://generativelanguage.googleapis.com/v1beta",
            "model": "gemini-2.5-flash",
            "max_output_tokens": 8192,
        }

    def test_google_request_sets_zero_thinking_budget(self):
        request = call_model._build_request(
            self.profile, "system prompt", "case text", "test-key"
        )
        body = json.loads(request.data.decode("utf-8"))
        generation_config = body.get("generationConfig", {})
        thinking_config = generation_config.get("thinkingConfig", {})
        self.assertEqual(thinking_config.get("thinkingBudget"), 0)

    def test_google_extract_text_filters_thought_parts(self):
        response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"thought": True, "text": "Chain of thought text"},
                            {"text": "VERDICT: APPROVE"},
                        ]
                    }
                }
            ]
        }
        extracted = call_model._extract_text("google", response)
        self.assertEqual(extracted, "VERDICT: APPROVE")

    def test_google_extract_text_raises_when_all_parts_are_thoughts(self):
        response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"thought": True, "text": "Only reasoning tokens"}
                        ]
                    }
                }
            ]
        }
        with self.assertRaises(call_model.ProviderError):
            call_model._extract_text("google", response)


class BuildPrCaseDiffBoundTest(unittest.TestCase):
    """build_case bounds git diff output and imports sys directly."""

    def test_oversized_diff_raises_runtime_error(self):
        oversized = b"x" * (build_pr_case.MAX_DIFF_BYTES + 1)
        mock_proc = MagicMock()
        mock_proc.stdout.read.return_value = oversized
        mock_proc.returncode = 0
        with patch.dict(
            "os.environ",
            {
                "EVENT_PATH": "dummy",
                "BASE_SHA": "0" * 40,
                "HEAD_SHA": "1" * 40,
            },
        ):
            with patch(
                "builtins.open",
                unittest.mock.mock_open(
                    read_data=json.dumps({"pull_request": {"title": "T", "body": "B"}})
                ),
            ):
                with patch("subprocess.Popen", return_value=mock_proc):
                    with self.assertRaises(RuntimeError) as context:
                        build_pr_case.build_case()
                    self.assertIn("limit", str(context.exception))

    def test_sys_is_imported_directly(self):
        self.assertIn("sys", build_pr_case.__dict__)


if __name__ == "__main__":
    unittest.main()
