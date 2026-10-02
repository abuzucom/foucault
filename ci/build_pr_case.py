#!/usr/bin/env python3
"""Build the provenance-labeled PR review envelope."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

MAX_METADATA_BYTES = 1_000_000
MAX_DIFF_BYTES = 2_000_000
SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
REPOSITORY_PATTERN = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")


def _read_pull_request_from_api() -> dict[str, object]:
    """Read complete PR metadata for a workflow_run event."""
    number = os.environ.get("PR_NUMBER", "")
    repository_name = os.environ.get("PR_REPOSITORY", "")
    token = os.environ.get("GH_TOKEN", "")
    if not re.fullmatch(r"[1-9][0-9]*", number):
        raise RuntimeError("pull request number is invalid")
    if not REPOSITORY_PATTERN.fullmatch(repository_name):
        raise RuntimeError("pull request repository is invalid")
    if not token:
        raise RuntimeError("GitHub token is unavailable")
    owner, repository = repository_name.split("/", 1)
    request_url = (
        "https://api.github.com/repos/"
        + quote(owner, safe="")
        + "/"
        + quote(repository, safe="")
        + "/pulls/"
        + number
    )
    request = Request(
        request_url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read(MAX_METADATA_BYTES + 1)
    except (HTTPError, URLError, OSError) as error:
        raise RuntimeError("pull request metadata request failed") from error
    if len(raw) > MAX_METADATA_BYTES:
        raise RuntimeError("pull request metadata is too large")
    try:
        result = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError("pull request metadata is invalid") from error
    if not isinstance(result, dict):
        raise RuntimeError("pull request metadata is not an object")
    return result


def _get_pull_request(event: dict[str, object]) -> dict[str, object]:
    """Return full pull request metadata from either supported event shape."""
    pull_request = event.get("pull_request")
    if isinstance(pull_request, dict):
        return pull_request
    workflow_run = event.get("workflow_run")
    if isinstance(workflow_run, dict):
        return _read_pull_request_from_api()
    raise RuntimeError("event has no pull request metadata")


def _digest(text: str) -> str:
    """Return the normalized SHA-256 digest used by the evaluator envelope."""
    return hashlib.sha256(text.replace("\r\n", "\n").encode()).hexdigest()


def build_case() -> dict[str, object]:
    """Build one PR envelope from trusted lifecycle data and target evidence."""
    with open(os.environ["EVENT_PATH"], encoding="utf-8") as event_file:
        event = json.load(event_file)
    if not isinstance(event, dict):
        raise RuntimeError("event payload is not an object")
    pull_request = _get_pull_request(event)
    base_sha = os.environ.get("BASE_SHA", "")
    head_sha = os.environ.get("HEAD_SHA", "")
    if not SHA_PATTERN.fullmatch(base_sha) or not SHA_PATTERN.fullmatch(head_sha):
        raise RuntimeError("pull request revisions are invalid")
    title = pull_request.get("title")
    body = pull_request.get("body")
    if not isinstance(title, str) or not isinstance(body, (str, type(None))):
        raise RuntimeError("pull request title or body is invalid")
    with subprocess.Popen(
        ["git", "diff", base_sha, head_sha],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as process:
        raw_diff = process.stdout.read(MAX_DIFF_BYTES + 1) if process.stdout else b""
        if len(raw_diff) > MAX_DIFF_BYTES:
            process.kill()
            process.wait()
            raise RuntimeError("pull request diff exceeds the configured limit")
        process.wait()
        if process.returncode != 0:
            raise RuntimeError("git diff command failed")
    try:
        diff = raw_diff.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RuntimeError("pull request diff is not valid UTF-8") from error
    target = "Title: " + title + "\n\n" + (body or "")
    target += "\n\n---\n" + diff
    return {
        "mode": "PR",
        "TRUSTED_HOOK_CONTEXT": {
            "read_only": True,
            "sha256": _digest(""),
            "text": "",
        },
        "REVIEW_TARGET": {"sha256": _digest(target), "text": target},
    }


def main() -> int:
    """Write one review envelope to case_text.txt."""
    try:
        envelope = build_case()
        Path("case_text.txt").write_text(
            json.dumps(envelope, ensure_ascii=True, sort_keys=True),
            encoding="utf-8",
        )
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as error:
        print(f"case construction failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
