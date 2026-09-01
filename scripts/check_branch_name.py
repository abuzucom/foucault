#!/usr/bin/env python3
"""Enforce the <type>/<kebab-description> branch naming convention.

Copy this portable checker into any repository. Use it as a pre-push hook or
CI step on `pull_request` events. Default checks exempt `main`, `master`, and a
detached HEAD. Strict agent preflight rejects those states. A mismatch exits 1.
"""
import argparse
import os
import re
import subprocess
import sys

try:
    from scripts.trusted_git import run_git
except ModuleNotFoundError:
    from trusted_git import run_git

DEFAULT_PREFIXES = ("feat", "fix", "chore", "docs", "test")
EXEMPT_BRANCHES = ("main", "master", "HEAD")


def _pattern(prefixes: tuple[str, ...]) -> re.Pattern:
    """Build the <type>/<kebab-description> pattern for the given prefixes."""
    prefix_group = "|".join(re.escape(prefix) for prefix in prefixes)
    return re.compile(rf"^(?:{prefix_group})/[a-z0-9]+(?:-[a-z0-9]+)*$")


def find_violations(
    branch: str,
    prefixes: tuple[str, ...] = DEFAULT_PREFIXES,
    strict: bool = False,
) -> list[str]:
    """Return a violation message if `branch` breaks the naming convention."""
    if not strict and (not branch or branch in EXEMPT_BRANCHES):
        return []
    if _pattern(prefixes).match(branch):
        return []
    allowed = ", ".join(f"{prefix}/" for prefix in prefixes)
    return [f"branch '{branch}' does not match <type>/<kebab-description> ({allowed})"]


def _current_branch(repo=None) -> str:
    """Return the PR head branch in CI, or the local checked-out branch."""
    head_ref = os.environ.get("GITHUB_HEAD_REF", "")
    if head_ref:
        return head_ref
    repository = repo or os.getcwd()
    result = run_git(
        repository,
        ["rev-parse", "--abbrev-ref", "HEAD"],
        runner=subprocess.run,
    )
    branch = result.stdout.strip()
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode,
            "git rev-parse",
            output=result.stdout,
            stderr=result.stderr,
        )
    if not branch:
        raise ValueError("git rev-parse returned an empty branch name")
    return branch


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("branch", nargs="?", help="branch to check (default: current branch)")
    parser.add_argument("--repo", default=os.getcwd(), help="repository to inspect (default: cwd)")
    parser.add_argument(
        "--prefixes",
        default=",".join(DEFAULT_PREFIXES),
        help="comma-separated allowed prefixes",
    )
    parser.add_argument(
        "--strict-agent-preflight",
        action="store_true",
        help="reject primary branches and detached HEAD for agent preflight",
    )
    args = parser.parse_args()
    try:
        branch = args.branch or _current_branch(args.repo)
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        print(
            f"Error. Branch lookup failed. Restore readable Git metadata and retry. {error}",
            file=sys.stderr,
        )
        return 1
    prefixes = tuple(prefix.strip() for prefix in args.prefixes.split(",") if prefix.strip())

    violations = find_violations(
        branch,
        prefixes,
        strict=args.strict_agent_preflight,
    )
    if violations:
        for message in violations:
            print(message, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
