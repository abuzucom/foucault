#!/usr/bin/env python3
"""Build the retry review envelope after a response fails validation.

Usage: build_retry_case.py CASE_FILE ERROR_FILE OUTPUT_FILE

The retry envelope copies the first envelope and adds the validator problems
to TRUSTED_HOOK_CONTEXT. REVIEW_TARGET stays byte-identical. The validator
emits fixed messages with line numbers. The builder still bounds the text
and keeps printable ASCII only. A pipeline file then cannot carry terminal
escapes or unbounded text into the trusted channel.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# The case builder lives beside this script. Tests import this module from
# the repository root. The explicit path entry serves both entry points.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_pr_case  # resolved through the path set above

MAX_PROBLEM_CHARS = 2_000
# Reading a bounded prefix keeps a runaway error file out of memory.
MAX_ERROR_FILE_CHARS = MAX_PROBLEM_CHARS * 4
EXPECTED_ARGUMENTS = 3
NON_PRINTABLE_ASCII = re.compile(r"[^\x20-\x7e]")
REPEATED_SPACES = re.compile(r" {2,}")
RETRY_NOTE = (
    "Retry attempt. The previous report failed structural validation. Emit a corrected "
    "full report that satisfies the reporting contract. The validator problems follow."
)
UNKNOWN_PROBLEM = "validator problem unavailable"


def sanitize_problems(text: str) -> str:
    """Return the validator text as one bounded line of printable ASCII."""
    flattened = text.replace("\r", " ").replace("\n", " ")
    printable = NON_PRINTABLE_ASCII.sub("", flattened)
    collapsed = REPEATED_SPACES.sub(" ", printable).strip()
    return collapsed[:MAX_PROBLEM_CHARS] or UNKNOWN_PROBLEM


def build_retry_case(case: object, problems: str) -> dict[str, object]:
    """Return a copy of the case with the problems in trusted context."""
    if not isinstance(case, dict):
        raise ValueError("case is not an object")
    trusted = case.get("TRUSTED_HOOK_CONTEXT")
    if not isinstance(trusted, dict) or not isinstance(case.get("REVIEW_TARGET"), dict):
        raise ValueError("case lacks TRUSTED_HOOK_CONTEXT or REVIEW_TARGET")
    text = RETRY_NOTE + "\n" + sanitize_problems(problems)
    retry_trusted = {**trusted, "text": text, "sha256": build_pr_case._digest(text)}
    return {**case, "TRUSTED_HOOK_CONTEXT": retry_trusted}


def main(arguments: list[str]) -> int:
    """Write the retry envelope from the first case and the validator output."""
    if len(arguments) != EXPECTED_ARGUMENTS:
        print("usage: build_retry_case.py CASE_FILE ERROR_FILE OUTPUT_FILE", file=sys.stderr)
        return 2
    case_path, error_path, output_path = (Path(argument) for argument in arguments)
    try:
        case = json.loads(case_path.read_text(encoding="utf-8"))
        with error_path.open(encoding="utf-8", errors="replace") as error_file:
            problems = error_file.read(MAX_ERROR_FILE_CHARS)
        retry = build_retry_case(case, problems)
        output_path.write_text(json.dumps(retry, ensure_ascii=True, sort_keys=True), encoding="utf-8")
    except (OSError, UnicodeError, ValueError) as error:
        print(f"retry case construction failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
