#!/usr/bin/env python3
"""Execute a trusted model adapter command without shell interpretation."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN_SHELL_TOKENS = (";", "&", "|", ">", "<", "`", "$", "(", ")")
FORWARDED_ENVIRONMENT = {
    "AUDIT_PROMPT_FILE",
    "CASE_TEXT_FILE",
    "MODEL_API_KEY",
    "PATH",
    "HOME",
    "LANG",
    "SystemRoot",
    "TEMP",
    "TMP",
}


def parse_command(command: str) -> list[str]:
    """Parse a Python script command and reject shell syntax."""
    if not command or any(token in command for token in FORBIDDEN_SHELL_TOKENS):
        raise ValueError("model_call_command contains shell syntax")
    try:
        arguments = shlex.split(command, posix=True)
    except ValueError as error:
        raise ValueError("model_call_command has invalid quoting") from error
    if len(arguments) != 2 or arguments[0] not in {"python", "python3"}:
        raise ValueError("model_call_command must name one Python script")
    if "\\" in arguments[1]:
        raise ValueError("model_call_command must use a repository-relative path")
    script_argument = Path(arguments[1])
    if script_argument.is_absolute():
        raise ValueError("model_call_command script must be relative")
    script = (REPO_ROOT / script_argument).resolve()
    if script.suffix != ".py" or REPO_ROOT not in script.parents:
        raise ValueError("model_call_command script must remain in the repository")
    return [sys.executable, str(script)]


def main() -> int:
    """Run the validated adapter and forward only its standard output."""
    try:
        arguments = parse_command(os.environ.get("MODEL_CALL_COMMAND", ""))
        adapter_environment = {
            name: value
            for name, value in os.environ.items()
            if name in FORWARDED_ENVIRONMENT
        }
        result = subprocess.run(
            arguments,
            check=False,
            shell=False,
            capture_output=True,
            text=True,
            env=adapter_environment,
        )
    except (OSError, ValueError) as error:
        print(f"model command rejected: {error}", file=sys.stderr)
        return 2
    if result.returncode:
        print("model command failed", file=sys.stderr)
        return result.returncode
    print(result.stdout, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
