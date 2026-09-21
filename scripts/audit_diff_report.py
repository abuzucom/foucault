#!/usr/bin/env python3
"""Write a compact AUDIT.md change report to the GitHub job summary."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from scripts import trusted_git


REVISION_PATTERN = re.compile(r"^[0-9a-fA-F]{40,64}$")


def git_show(revision: str) -> str | None:
    """Read AUDIT.md at an immutable object ID."""
    if not REVISION_PATTERN.fullmatch(revision):
        print(f"invalid Git revision: {revision!r}", file=sys.stderr)
        return None
    try:
        result = trusted_git.run_git(
            Path.cwd(),
            ["show", "--end-of-options", f"{revision}:AUDIT.md"],
            check=True,
        )
    except subprocess.CalledProcessError as error:
        print(
            f"unable to read AUDIT.md at {revision}: Git show failed "
            f"with exit code {error.returncode}",
            file=sys.stderr,
        )
        return None
    except (FileNotFoundError, OSError, ValueError) as error:
        print(f"unable to read AUDIT.md at {revision}: {error}", file=sys.stderr)
        return None
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
    if before is None or after is None:
        with open(summary, "a", encoding="utf-8", newline="\n") as stream:
            stream.write(
                "## AUDIT.md policy diff\n\n"
                "- Policy diff unavailable: a base or head revision could not be read.\n"
            )
        return 1
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    changed = sum(left != right for left, right in zip(before_lines, after_lines))
    changed += abs(len(before_lines) - len(after_lines))
    report = (
        "## AUDIT.md policy diff\n\n"
        f"- Base bytes: {len(before.encode('utf-8'))}\n"
        f"- Head bytes: {len(after.encode('utf-8'))}\n"
        f"- Approximate changed line positions: {changed}\n"
        f"- Evaluator cases: run `python3 eval/run_eval.py`\n"
    )
    with open(summary, "a", encoding="utf-8", newline="\n") as stream:
        stream.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
