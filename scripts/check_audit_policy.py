#!/usr/bin/env python3
"""Validate AUDIT.md structure, required controls, and prose width."""

from __future__ import annotations

import re
import sys
from pathlib import Path

MAX_BYTES = 32 * 1024
MAX_PROSE_WIDTH = 120
ALLOWED_LONG_PREFIXES = (
    "|",
    "VERDICT_JSON:",
    "- **PR:**",
    "- **File / Wholesale:**",
    "- **Piece:**",
)
REQUIRED_TEXT = (
    "## 0. Review Modes",
    "## 5. Hard Blockers",
    "## 6. Reporting Format",
    "VERDICT: APPROVE | BLOCK | NEEDS-HUMAN",
    "NEEDS-HUMAN",
    "parameterized queries",
    "separate argument arrays",
    "untrusted-data sinks",
    "evidence provenance",
)


def find_violations(path: Path) -> list[str]:
    """Return policy violations for one AUDIT.md file."""
    if not path.is_file():
        return [f"missing policy: {path}"]
    raw = path.read_bytes()
    violations: list[str] = []
    if len(raw) > MAX_BYTES:
        violations.append(f"policy exceeds {MAX_BYTES} bytes")
    if b"\r\n" in raw or b"\r" in raw:
        violations.append("policy must use LF line endings")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError:
        violations.append("policy must contain ASCII prose")
        text = raw.decode("ascii", errors="replace")
    for required in REQUIRED_TEXT:
        if required not in text:
            violations.append(f"missing required policy text: {required}")
    headings = re.findall(r"^#{2,3} .+$", text, re.MULTILINE)
    if len(headings) != len(set(headings)):
        violations.append("duplicate policy heading")
    in_fence = False
    for line_number, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or len(line) <= MAX_PROSE_WIDTH:
            continue
        if line.startswith(ALLOWED_LONG_PREFIXES):
            continue
        violations.append(
            f"line {line_number} exceeds {MAX_PROSE_WIDTH} characters"
        )
    return violations


def main() -> int:
    """Print violations and return a blocking status."""
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("AUDIT.md")
    violations = find_violations(path)
    if violations:
        for violation in violations:
            print(f"error: {violation}", file=sys.stderr)
        return 1
    print(f"ok       {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
