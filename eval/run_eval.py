#!/usr/bin/env python3
"""Golden-corpus harness for AUDIT.md.

Validates every case under eval/cases/ against its expected.json. Model
invocation is pluggable: this script never calls a model API directly and
ships no credentials. Point --model-call at a Python callable to run cases
live; omit it to run --check-structure only (the default), which validates
fixture and expected.json shape without asking a model anything.

Usage:
    python eval/run_eval.py
    python eval/run_eval.py --model-call mymodule:call_model
    python eval/run_eval.py --case sql-injection-pr --model-call mymodule:call_model

A --model-call target is a callable with the signature:
    call_model(system_prompt: str, mode: str, case_text: str) -> str
returning the model's raw text response (the human-readable report,
including its final VERDICT:/RISK: line and, where AUDIT.md section 6
requires it, the VERDICT_JSON companion block).
"""

from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_PATH = REPO_ROOT / "AUDIT.md"
CASES_DIR = Path(__file__).resolve().parent / "cases"

VALID_MODES = {"PR", "File", "Piece", "Wholesale"}
CASE_INPUT_NAMES = ("diff.patch", "input.py", "input.txt", "input.js")

VERDICT_LINE_RE = re.compile(
    r"^(VERDICT|RISK(?: \(partial\))?):\s*(.+)$", re.MULTILINE
)
VERDICT_JSON_RE = re.compile(r"VERDICT_JSON:\s*(\{.*\})", re.DOTALL)


class CaseError(Exception):
    pass


def load_case(case_dir: Path) -> dict:
    expected_path = case_dir / "expected.json"
    if not expected_path.is_file():
        raise CaseError(f"{case_dir.name}: missing expected.json")
    expected = json.loads(expected_path.read_text(encoding="utf-8"))

    for key in ("mode", "expected_verdict", "expected_classes", "notes"):
        if key not in expected:
            raise CaseError(f"{case_dir.name}: expected.json missing '{key}'")
    if expected["mode"] not in VALID_MODES:
        raise CaseError(
            f"{case_dir.name}: mode '{expected['mode']}' not one of {sorted(VALID_MODES)}"
        )

    input_files = [
        case_dir / name for name in CASE_INPUT_NAMES if (case_dir / name).is_file()
    ]
    if not input_files:
        raise CaseError(f"{case_dir.name}: no recognized input file present")

    context_path = case_dir / "context.md"
    context_text = context_path.read_text(encoding="utf-8") if context_path.is_file() else ""

    case_text = "\n\n".join(p.read_text(encoding="utf-8") for p in input_files)
    return {
        "name": case_dir.name,
        "mode": expected["mode"],
        "expected": expected,
        "context": context_text,
        "case_text": case_text,
    }


def discover_cases(only: str | None = None) -> list[dict]:
    if not CASES_DIR.is_dir():
        raise CaseError(f"cases directory not found: {CASES_DIR}")
    dirs = sorted(p for p in CASES_DIR.iterdir() if p.is_dir())
    if only:
        dirs = [p for p in dirs if p.name == only]
        if not dirs:
            raise CaseError(f"no case named '{only}' under {CASES_DIR}")
    return [load_case(d) for d in dirs]


def verdict_matches(expected_verdict: str, response_text: str) -> tuple[bool, str]:
    match = VERDICT_LINE_RE.search(response_text)
    if not match:
        return False, "no VERDICT:/RISK: line found in response"
    actual_line = f"{match.group(1)}: {match.group(2)}".strip()
    if expected_verdict in actual_line:
        return True, actual_line
    return False, actual_line


def json_companion_ok(response_text: str) -> tuple[bool, str]:
    match = VERDICT_JSON_RE.search(response_text)
    if not match:
        return False, "no VERDICT_JSON: block found"
    try:
        json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        return False, f"VERDICT_JSON block did not parse: {exc}"
    return True, "VERDICT_JSON parsed"


def resolve_model_call(spec: str):
    module_name, _, func_name = spec.partition(":")
    if not module_name or not func_name:
        raise CaseError("--model-call must be in the form module:function")
    sys.path.insert(0, str(REPO_ROOT))
    module = importlib.import_module(module_name)
    return getattr(module, func_name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", help="run only the named case")
    parser.add_argument(
        "--model-call",
        help="module:function callable invoked as call(system_prompt, mode, case_text) -> str",
    )
    args = parser.parse_args()

    if not AUDIT_PATH.is_file():
        print(f"AUDIT.md not found at {AUDIT_PATH}", file=sys.stderr)
        return 1
    system_prompt = AUDIT_PATH.read_text(encoding="utf-8")

    try:
        cases = discover_cases(args.case)
    except CaseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not args.model_call:
        print(f"structure check only: {len(cases)} case(s) validated, no model call configured")
        for case in cases:
            print(f"  ok  {case['name']} (mode={case['mode']})")
        return 0

    model_call = resolve_model_call(args.model_call)

    failures = 0
    for case in cases:
        response = model_call(system_prompt, case["mode"], case["context"] + "\n\n" + case["case_text"])
        ok, detail = verdict_matches(case["expected"]["expected_verdict"], response)
        status = "pass" if ok else "FAIL"
        print(f"  {status}  {case['name']}: expected '{case['expected']['expected_verdict']}', got '{detail}'")
        if not ok:
            failures += 1

        if case["expected"].get("expect_json"):
            json_ok, json_detail = json_companion_ok(response)
            json_status = "pass" if json_ok else "FAIL"
            print(f"  {json_status}  {case['name']} (VERDICT_JSON): {json_detail}")
            if not json_ok:
                failures += 1

    total = len(cases)
    print(f"\n{total - failures}/{total} verdict checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
