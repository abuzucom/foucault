#!/usr/bin/env python3
"""Tests for CI adapter bug fixes: model providers, thinking blocks, diff limit, sys import."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ci import build_pr_case
from ci import call_model

OVERSIZED_DIFF_LIMIT_BYTES = 16


def _git(repo: Path, *arguments: str) -> str:
    """Run Git in an isolated fixture repository and return stdout."""
    environment = dict(os.environ)
    environment.update({
        "GIT_AUTHOR_NAME": "adapter test",
        "GIT_AUTHOR_EMAIL": "1234567+adapter-test@users.noreply.github.com",
        "GIT_COMMITTER_NAME": "adapter test",
        "GIT_COMMITTER_EMAIL": "1234567+adapter-test@users.noreply.github.com",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_SYSTEM": os.devnull,
    })
    result = subprocess.run(
        ["git", *arguments], cwd=repo, env=environment,
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def _two_commit_repository(repo: Path) -> tuple[str, str]:
    """Return (base, head) commits whose diff exceeds the lowered limit."""
    _git(repo, "init", "-q", "-b", "main")
    (repo / "file.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "--all")
    _git(repo, "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "file.txt").write_text("head change exceeding the limit\n", encoding="utf-8")
    _git(repo, "commit", "-qam", "head")
    return base, _git(repo, "rev-parse", "HEAD")


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
        # A real repository and the real bounded reader. The byte limit is
        # lowered so a small fixture diff exceeds it.
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
            ):
                os.chdir(repo)
                try:
                    with self.assertRaises(RuntimeError) as context:
                        build_pr_case.build_case()
                finally:
                    os.chdir(previous)
        self.assertIn("limit", str(context.exception))

    def test_sys_is_imported_directly(self):
        self.assertIn("sys", build_pr_case.__dict__)


if __name__ == "__main__":
    unittest.main()
