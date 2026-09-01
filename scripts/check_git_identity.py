#!/usr/bin/env python3
"""Enforce a configured, allowed git identity on commits.

A portable, path-generic checker: copy this file into any repo and use it
as a pre-commit hook, a `pull_request` CI step, or a Claude Code hook
through hooks/enforce_git_identity.py. Three modes:

  no flags        the identity the next commit would use, read from config
  --unpushed      commits on HEAD absent from every remote-tracking ref
  --base/--head   commits in a range, for CI on a pull request

The default mode is the reliable one. With `user.name` or `user.email`
unset, git builds an identity from the account name and hostname, prints
its automatic-identity warning, and commits anyway. This mode fails first,
before the guess reaches a commit object.

Limitation: the commit modes cannot recover that signal, because a commit
object records no mark saying its author field was built rather than
configured. They apply the allowlist only.

The default allowlist accepts GitHub noreply addresses, which link a commit
to its account and publish no private address. The committer may also be
`noreply@github.com`, which is what GitHub itself sets on squash merges.
Override with --allow for a repo that commits under another convention.

Blocking: exits 1 on any violation, 2 on a usage error.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from scripts.trusted_git import resolve_git, run_git
except ModuleNotFoundError:
    try:
        from trusted_git import resolve_git, run_git
    except ModuleNotFoundError:
        resolve_git = None
        run_git = None

NOREPLY = re.compile(
    r"\A(?:[0-9]+\+)?[A-Za-z0-9-]+(?:\[bot\])?@users\.noreply\.github\.com\Z",
    re.IGNORECASE,
)
NOREPLY_LOGIN = re.compile(
    r"\A(?:[0-9]+\+)?(?P<login>[A-Za-z0-9-]+)@users\.noreply\.github\.com\Z",
    re.IGNORECASE,
)
GITHUB_COMMITTER = "noreply@github.com"

# Git treats each of these as an explicitly given identity, in this order.
# A checker that read only user.email would block harnesses and CI systems
# that supply one through the environment instead.
NAME_SOURCES = (
    ("env", "GIT_AUTHOR_NAME"),
    ("env", "GIT_COMMITTER_NAME"),
    ("config", "user.name"),
)
EMAIL_SOURCES = (
    ("env", "GIT_AUTHOR_EMAIL"),
    ("env", "GIT_COMMITTER_EMAIL"),
    ("config", "user.email"),
    ("env", "EMAIL"),
)

GH_TIMEOUT_SECONDS = 5

FIX_MESSAGE = (
    "fix: ask the user which name and email to commit under, then set them:\n"
    "  git config user.name  '<login>'\n"
    "  git config user.email '<id>+<login>@users.noreply.github.com'\n"
    "Do not invent an identity, and do not copy one out of this repository's\n"
    "history. An authenticated gh is not a git identity."
)


def _standalone_resolve_git(repo) -> str:
    """Resolve trusted Git when this portable checker was copied alone."""
    repository = Path(repo).resolve()
    if os.name == "nt":
        os.environ["NoDefaultCurrentDirectoryInExePath"] = "1"
    names = ("git.exe", "git.com") if os.name == "nt" else ("git",)
    for raw_directory in os.environ.get("PATH", "").split(os.pathsep):
        if not raw_directory:
            continue
        directory = Path(raw_directory.strip('"'))
        if not directory.is_absolute():
            continue
        for name in names:
            candidate = directory / name
            try:
                Path(os.path.abspath(candidate)).relative_to(repository)
                continue
            except ValueError:
                pass
            try:
                if candidate.is_symlink() or not candidate.is_file():
                    continue
                executable = candidate.resolve(strict=True)
                executable.relative_to(repository)
                continue
            except ValueError:
                if os.name == "nt" or os.access(executable, os.X_OK):
                    return str(executable)
            except OSError:
                continue
    raise FileNotFoundError("trusted Git executable was not found on PATH")


def _standalone_safe_directory(repository: Path, executable: Path) -> str:
    """Return an external working directory for standalone execution."""
    for candidate in (Path(tempfile.gettempdir()), executable.parent):
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(repository)
        except ValueError:
            if resolved.is_dir():
                return str(resolved)
        except OSError:
            continue
    raise OSError("no safe external directory is available for Git execution")


def _standalone_safe_path(repository: Path) -> str:
    """Remove repository-controlled entries from standalone child PATH."""
    safe_entries = []
    for raw_directory in os.environ.get("PATH", "").split(os.pathsep):
        if not raw_directory:
            continue
        directory = Path(raw_directory.strip('"'))
        if not directory.is_absolute():
            continue
        try:
            resolved = directory.resolve(strict=False)
            resolved.relative_to(repository)
        except ValueError:
            safe_entries.append(str(resolved))
        except OSError:
            continue
    return os.pathsep.join(safe_entries)


def _standalone_run_git(repo, arguments: list[str], *, check=False, runner=None):
    """Run trusted Git for a standalone copy of this checker."""
    repository = Path(repo).resolve()
    executable = Path(_standalone_resolve_git(repository))
    environment = dict(os.environ)
    environment.update({"GIT_PAGER": "", "PAGER": "", "GIT_TERMINAL_PROMPT": "0"})
    environment.update(
        {
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PROTOCOL_FROM_USER": "0",
            "PATH": _standalone_safe_path(repository),
        }
    )
    environment.pop("GIT_EXTERNAL_DIFF", None)
    if os.name == "nt":
        environment["NoDefaultCurrentDirectoryInExePath"] = "1"
    command = [
        str(executable),
        "-C",
        str(repository),
        "--no-pager",
        "--no-replace-objects",
        "-c",
        "core.pager=",
        "-c",
        "pager.log=false",
        "-c",
        "log.showSignature=false",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "diff.external=",
        "-c",
        "protocol.ext.allow=never",
        *arguments,
    ]
    execute = runner or subprocess.run
    return execute(
        command,
        cwd=_standalone_safe_directory(repository, executable),
        env=environment,
        capture_output=True,
        text=True,
        check=check,
    )


if resolve_git is None:
    resolve_git = _standalone_resolve_git
    run_git = _standalone_run_git


def _config(key: str, repo=None) -> str:
    """Return a git config value, or an empty string when it is unset."""
    result = run_git(
        repo or os.getcwd(),
        ["config", "--get", key],
        runner=subprocess.run,
    )
    if result.returncode not in (0, 1):
        raise subprocess.CalledProcessError(result.returncode, "git config")
    return result.stdout.strip() if result.returncode == 0 else ""


def _first_explicit(sources: tuple, repo=None) -> str:
    """Return the first value git would treat as an explicitly given field."""
    for kind, key in sources:
        value = os.environ.get(key, "").strip() if kind == "env" else _config(key, repo)
        if value:
            return value
    return ""


def worktree_identity(repo=None) -> dict:
    """Return the identity the next commit would use, and what git would guess."""
    repository = repo or os.getcwd()
    result = run_git(repository, ["version"], runner=subprocess.run)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, "git version")
    name = _first_explicit(NAME_SOURCES, repository)
    email = _first_explicit(EMAIL_SOURCES, repository)
    return {
        "label": "worktree",
        "author_email": email,
        "committer_email": email,
        "unset_name": not name,
        "unset_email": not email,
    }


def log_identities(revisions: list, repo=None) -> list:
    """Return one identity record per commit reachable by `revisions`."""
    repository = repo or os.getcwd()
    result = run_git(
        repository,
        ["log", "--no-ext-diff", "--format=%H%x00%ae%x00%ce", *revisions],
        check=True,
        runner=subprocess.run,
    )
    identities = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        fields = line.split("\x00")
        if len(fields) != 3 or not re.fullmatch(r"[0-9a-fA-F]{40,64}", fields[0]):
            raise ValueError("git log returned malformed identity metadata")
        sha, author_email, committer_email = fields
        identities.append(
            {
                "label": sha[:12],
                "author_email": author_email,
                "committer_email": committer_email,
                "unset_name": False,
                "unset_email": False,
            }
        )
    return identities


def unpushed_identities(repo=None) -> list:
    """Return identity records for commits on HEAD absent from every remote."""
    repository = repo or os.getcwd()
    result = run_git(repository, ["remote"], runner=subprocess.run)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, "git remote")
    if not result.stdout.strip():
        return []
    revisions = ["--not", "--remotes", "--not", "--end-of-options", "HEAD"]
    return log_identities(revisions, repository)


def _allowed(email: str, pattern: re.Pattern) -> bool:
    """Return True when `email` matches the allowlist pattern."""
    return bool(pattern.match(email.strip()))


def find_violations(identities: list, pattern: re.Pattern = NOREPLY) -> list:
    """Return one message per unset field or disallowed address."""
    violations = []
    for identity in identities:
        label = identity["label"]
        if identity["unset_email"]:
            violations.append(
                f"{label}: user.email is unset, so git builds one from this "
                "machine's account name and hostname and commits on a warning"
            )
        if identity["unset_name"]:
            violations.append(
                f"{label}: user.name is unset, so git builds one from this "
                "machine's account and commits on a warning"
            )
        if identity["unset_email"] or identity["unset_name"]:
            continue
        author = identity["author_email"]
        if not _allowed(author, pattern):
            violations.append(f"{label}: author email '{author}' is not an allowed address")
        committer = identity["committer_email"]
        if committer.strip().lower() == GITHUB_COMMITTER:
            continue
        if not _allowed(committer, pattern):
            violations.append(
                f"{label}: committer email '{committer}' is not an allowed address"
            )
    return violations


def gh_advisory(email: str) -> str:
    """Return a note about the gh-authenticated account. Never blocks."""
    try:
        result = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True,
            text=True,
            check=False,
            timeout=GH_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "note: gh is unavailable, so the account behind this identity is unverified"
    login = result.stdout.strip()
    if result.returncode != 0 or not login:
        return "note: gh is not authenticated, so the account behind this identity is unverified"
    match = NOREPLY_LOGIN.match(email.strip())
    if not match:
        return (
            f"note: gh is authenticated as '{login}', but the configured address is "
            "not a noreply address for that account"
        )
    if match.group("login").lower() != login.lower():
        return f"note: gh is authenticated as '{login}' but commits would be authored as '{email}'"
    return ""


def config_only_advisory(repo=None) -> str:
    """Return a note when git may still auto-detect an identity on this machine."""
    if _config("user.useConfigOnly", repo).lower() == "true":
        return ""
    return (
        "note: user.useConfigOnly is not true, so git auto-detects an identity "
        "when user.email is unset. Set it once per machine: "
        "git config --global user.useConfigOnly true"
    )


def select_identities(args: argparse.Namespace) -> list:
    """Return the identity records the requested mode covers."""
    if args.base:
        return log_identities(["--end-of-options", f"{args.base}..{args.head}"], args.repo)
    if args.unpushed:
        return unpushed_identities(args.repo)
    return [worktree_identity(args.repo)]


def build_parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="", help="base ref (exclusive); pairs with --head")
    parser.add_argument("--head", default="", help="head ref (inclusive); pairs with --base")
    parser.add_argument("--repo", default=os.getcwd(), help="repository to inspect (default: cwd)")
    parser.add_argument(
        "--unpushed", action="store_true", help="check commits absent from every remote"
    )
    parser.add_argument("--allow", default="", help="regex of allowed emails; overrides the default")
    parser.add_argument(
        "--advise",
        action="store_true",
        help="report the gh account and user.useConfigOnly; never changes the exit code",
    )
    return parser


def _print_advisories(identities: list, repo=None) -> None:
    """Print the non-blocking machine and account notes."""
    email = identities[0]["author_email"] if identities else ""
    for note in (config_only_advisory(repo), gh_advisory(email)):
        if note:
            print(note)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if bool(args.base) != bool(args.head):
        parser.error("--base and --head must be given together")
    pattern = re.compile(args.allow) if args.allow else NOREPLY

    try:
        identities = select_identities(args)
        if args.advise:
            _print_advisories(identities, args.repo)
    except (subprocess.CalledProcessError, UnicodeError, ValueError) as error:
        print(f"error: git log failed: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"error: git is unavailable: {error}", file=sys.stderr)
        return 1

    violations = find_violations(identities, pattern)
    if violations:
        for message in violations:
            print(message, file=sys.stderr)
        print(FIX_MESSAGE, file=sys.stderr)
        return 1
    if args.base or args.unpushed:
        print(f"no identity violations found in {len(identities)} commit(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
