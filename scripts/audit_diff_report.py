#!/usr/bin/env python3
"""Write a compact AUDIT.md change report to the GitHub job summary."""

from __future__ import annotations

import os
import subprocess
import sys


def git_show(revision: str) -> str:
    """Read AUDIT.md at a validated Git revision."""
    result = subprocess.run(
        ["git", "show", f"{revision}:AUDIT.md"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def main() -> int:
    """Compare base and head policy text and write the job summary."""
    base = os.environ.get("BASE_SHA")
    head = os.environ.get("HEAD_SHA")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not base or not head or not summary:
        print("required GitHub summary environment is missing", file=sys.stderr)
        return 1
    before = git_show(base)
    after = git_show(head)
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    changed = sum(left != right for left, right in zip(before_lines, after_lines))
    changed += abs(len(before_lines) - len(after_lines))
    report = (
        "## AUDIT.md policy diff\n\n"
        f"- Base bytes: {len(before.encode('utf-8'))}\n"
        f"- Head bytes: {len(after.encode('utf-8'))}\n"
        f"- Changed line positions: {changed}\n"
        f"- Evaluator cases: run `python3 eval/run_eval.py`\n"
    )
    with open(summary, "a", encoding="utf-8", newline="\n") as stream:
        stream.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
