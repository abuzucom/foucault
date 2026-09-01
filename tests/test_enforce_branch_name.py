#!/usr/bin/env python3
"""Tests for hooks/enforce_branch_name.py and its wiring.

Runs the hook as a subprocess against synthetic Claude Code payloads, the
same path the harness uses, rather than asserting on mocks. Branch names
come from `GITHUB_HEAD_REF`, which scripts/check_branch_name.py reads before
falling back to `git rev-parse`, so results do not depend on which branch
the test run happens to be on.

The settings tests guard the wiring: a hook nobody registered enforces
nothing, and an edit to `.claude/settings.json` that drops an event would
otherwise pass every behavioral test in this file.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_PATH = REPO_ROOT / "hooks" / "enforce_branch_name.py"
LIVE_SETTINGS = REPO_ROOT / ".claude" / "settings.json"
EXAMPLE_SETTINGS = REPO_ROOT / "hooks" / "claude-code-settings.example.json"
CHECKER_PATH = REPO_ROOT / "scripts" / "check_branch_name.py"

VIOLATING_BRANCH = "claude/session-start-hook-branch-check-5b33fv"
CONFORMING_BRANCH = "feat/session-start-branch-check"
BLOCKING_EXIT_CODE = 2


def _load_hook_module():
    """Import the hook by path, since hooks/ is not an importable package."""
    spec = importlib.util.spec_from_file_location("enforce_branch_name", HOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hook = _load_hook_module()


def run_hook(payload, branch: str, client: str = "claude") -> subprocess.CompletedProcess:
    """Run the hook as the harness does: JSON on stdin, branch from the env."""
    environment = dict(os.environ)
    environment["GITHUB_HEAD_REF"] = branch
    environment["CLAUDE_PROJECT_DIR"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, str(HOOK_PATH), "--client", client],
        input=json.dumps(payload) if payload is not None else "",
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )


def bash_payload(command: str) -> dict:
    """Return a PreToolUse payload for a Bash tool call."""
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }


def session_start_payload() -> dict:
    """Return a SessionStart payload."""
    return {
        "hook_event_name": "SessionStart",
        "source": "startup",
        "cwd": str(REPO_ROOT),
    }


class CheckerContractTest(unittest.TestCase):
    """The rule the hook enforces, verified against the checker itself."""

    def test_claude_prefix_is_rejected(self):
        result = subprocess.run(
            [sys.executable, str(CHECKER_PATH), VIOLATING_BRANCH],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn(VIOLATING_BRANCH, result.stderr)

    def test_conforming_prefixes_are_accepted(self):
        for branch in ("feat/a-b", "fix/a-b", "chore/a-b", "docs/a-b", "test/a-b"):
            with self.subTest(branch=branch):
                result = subprocess.run(
                    [sys.executable, str(CHECKER_PATH), branch],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_default_checker_keeps_operational_exemptions(self):
        for branch in ("main", "master", "HEAD"):
            with self.subTest(branch=branch):
                self.assertEqual(hook.check_branch(branch, strict=False), "")

    def test_agent_preflight_rejects_operational_exemptions(self):
        for branch in ("main", "master", "HEAD", ""):
            with self.subTest(branch=branch):
                self.assertTrue(hook.check_branch(branch, strict=True))


class SessionStartTest(unittest.TestCase):
    """SessionStart informs; it never blocks, since Claude Code ignores its exit."""

    def test_violation_injects_context_and_exits_zero(self):
        result = run_hook(session_start_payload(), VIOLATING_BRANCH)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        specific = output["hookSpecificOutput"]
        self.assertEqual(specific["hookEventName"], "SessionStart")
        self.assertIn(VIOLATING_BRANCH, specific["additionalContext"])
        self.assertIn("STOP", specific["additionalContext"])
        self.assertIn("git branch -m", specific["additionalContext"])
        self.assertNotIn("sign-off", specific["additionalContext"])
        self.assertEqual(output["systemMessage"], specific["additionalContext"])

    def test_conforming_branch_stays_silent(self):
        result = run_hook(session_start_payload(), CONFORMING_BRANCH)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_missing_event_name_defaults_to_session_start(self):
        result = run_hook({"cwd": str(REPO_ROOT)}, VIOLATING_BRANCH)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["hookSpecificOutput"]["hookEventName"], "SessionStart")

    def test_empty_stdin_exits_zero(self):
        result = run_hook(None, CONFORMING_BRANCH)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_malformed_stdin_exits_zero(self):
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input="not json",
            capture_output=True,
            text=True,
            env={**os.environ, "GITHUB_HEAD_REF": CONFORMING_BRANCH},
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class PreToolUseTest(unittest.TestCase):
    """PreToolUse blocks every ordinary tool until branch preflight passes."""

    def test_commit_on_violating_branch_is_blocked(self):
        result = run_hook(bash_payload('git commit -m "feat: x"'), VIOLATING_BRANCH)
        self.assertEqual(result.returncode, BLOCKING_EXIT_CODE)
        self.assertIn("git commit", result.stderr)
        self.assertIn(VIOLATING_BRANCH, result.stderr)
        self.assertIn("git branch -m", result.stderr)

    def test_push_on_violating_branch_is_blocked(self):
        result = run_hook(bash_payload("git push -u origin HEAD"), VIOLATING_BRANCH)
        self.assertEqual(result.returncode, BLOCKING_EXIT_CODE)
        self.assertIn("git push", result.stderr)

    def test_commit_on_conforming_branch_is_allowed(self):
        result = run_hook(bash_payload('git commit -m "feat: x"'), CONFORMING_BRANCH)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_push_on_conforming_branch_is_allowed(self):
        result = run_hook(bash_payload("git push -u origin HEAD"), CONFORMING_BRANCH)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rename_command_is_never_blocked(self):
        result = run_hook(bash_payload("git branch -m feat/x"), VIOLATING_BRANCH)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_read_only_git_command_is_blocked(self):
        for command in ("git status", "git log --oneline -5", "git branch --show-current"):
            with self.subTest(command=command):
                result = run_hook(bash_payload(command), VIOLATING_BRANCH)
                self.assertEqual(result.returncode, BLOCKING_EXIT_CODE)

    def test_non_git_command_is_blocked(self):
        result = run_hook(bash_payload("ls -la"), VIOLATING_BRANCH)
        self.assertEqual(result.returncode, BLOCKING_EXIT_CODE)

    def test_non_bash_tool_is_blocked(self):
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/x"},
        }
        result = run_hook(payload, VIOLATING_BRANCH)
        self.assertEqual(result.returncode, BLOCKING_EXIT_CODE)

    def test_question_tool_is_allowed(self):
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "AskUserQuestion",
            "tool_input": {"questions": []},
        }
        result = run_hook(payload, VIOLATING_BRANCH)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_primary_branch_allows_only_new_topic_branch(self):
        blocked = run_hook(bash_payload("git branch -m feat/x"), "main")
        allowed = run_hook(bash_payload("git switch -c feat/x"), "main")
        self.assertEqual(blocked.returncode, BLOCKING_EXIT_CODE)
        self.assertEqual(allowed.returncode, 0, allowed.stderr)

    def test_correction_command_rejects_chaining(self):
        result = run_hook(
            bash_payload("git branch -m feat/x && python build.py"),
            VIOLATING_BRANCH,
        )
        self.assertEqual(result.returncode, BLOCKING_EXIT_CODE)

    def test_codex_uses_blocking_exit(self):
        result = run_hook(bash_payload("git status"), VIOLATING_BRANCH, "codex")
        self.assertEqual(result.returncode, BLOCKING_EXIT_CODE)

    def test_gemini_returns_native_deny(self):
        payload = {
            "hook_event_name": "BeforeTool",
            "tool_name": "read_file",
            "tool_input": {"file_path": "README.md"},
            "cwd": str(REPO_ROOT),
        }
        result = run_hook(payload, VIOLATING_BRANCH, "gemini")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["decision"], "deny")

    def test_antigravity_returns_native_deny(self):
        payload = {
            "toolCall": {"name": "view_file", "args": {"AbsolutePath": "README.md"}},
            "workspacePaths": [str(REPO_ROOT)],
        }
        result = run_hook(payload, VIOLATING_BRANCH, "antigravity")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["decision"], "deny")

    def test_powershell_command_line_allows_exact_recovery(self):
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "PowerShell",
            "tool_input": {"CommandLine": "git branch -m feat/recovered"},
        }
        result = run_hook(payload, VIOLATING_BRANCH)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_shell_tool_without_command_passes_on_valid_branch(self):
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {},
        }
        result = run_hook(payload, CONFORMING_BRANCH)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_malformed_antigravity_tool_call_denies(self):
        payload = {
            "toolCall": "invalid",
            "workspacePaths": [str(REPO_ROOT)],
        }
        result = run_hook(payload, VIOLATING_BRANCH, "antigravity")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["decision"], "deny")

    def test_chained_command_containing_push_is_blocked(self):
        result = run_hook(bash_payload("make lint && git push"), VIOLATING_BRANCH)
        self.assertEqual(result.returncode, BLOCKING_EXIT_CODE)

    def test_repo_location_checks_the_branch_that_receives_the_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "other"
            repo.mkdir()
            subprocess.run(
                ["git", "init", "-q", "-b", VIOLATING_BRANCH],
                cwd=repo,
                check=True,
            )
            subprocess.run(
                ["git", "-c", "user.name=octocat", "-c",
                 "user.email=1234567+octocat@users.noreply.github.com",
                 "commit", "--allow-empty", "-q", "-m", "init"],
                cwd=repo,
                check=True,
            )
            command = f"git -C {repo.as_posix()} commit -m x"
            result = run_hook(bash_payload(command), CONFORMING_BRANCH)
        self.assertEqual(result.returncode, BLOCKING_EXIT_CODE, result.stderr)
        self.assertIn(VIOLATING_BRANCH, result.stderr)

    def test_alias_from_effective_repo_config_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "other"
            repo.mkdir()
            subprocess.run(
                ["git", "init", "-q", "-b", VIOLATING_BRANCH],
                cwd=repo,
                check=True,
            )
            subprocess.run(
                ["git", "-c", "user.name=octocat", "-c",
                 "user.email=1234567+octocat@users.noreply.github.com",
                 "commit", "--allow-empty", "-q", "-m", "init"],
                cwd=repo,
                check=True,
            )
            subprocess.run(
                ["git", "config", "alias.ship", "commit"],
                cwd=repo,
                check=True,
            )
            command = f"git -C {repo.as_posix()} ship -m x"
            result = run_hook(bash_payload(command), CONFORMING_BRANCH)
        self.assertEqual(result.returncode, BLOCKING_EXIT_CODE, result.stderr)

    def test_every_git_write_context_is_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first"
            second = Path(directory) / "second"
            for repo, branch in (
                    (first, CONFORMING_BRANCH), (second, VIOLATING_BRANCH)):
                repo.mkdir()
                subprocess.run(
                    ["git", "init", "-q", "-b", branch], cwd=repo, check=True)
                subprocess.run(
                    ["git", "-c", "user.name=octocat", "-c",
                     "user.email=1234567+octocat@users.noreply.github.com",
                     "commit", "--allow-empty", "-q", "-m", "init"],
                    cwd=repo,
                    check=True,
                )
            command = (
                f"git -C {first.as_posix()} commit -m first && "
                f"git -C {second.as_posix()} commit -m second"
            )
            result = run_hook(bash_payload(command), CONFORMING_BRANCH)
        self.assertEqual(result.returncode, BLOCKING_EXIT_CODE, result.stderr)
        self.assertIn(VIOLATING_BRANCH, result.stderr)


class BlockedCommandTest(unittest.TestCase):
    """Command matching, exercised directly for the cases subprocess runs skip."""

    def test_git_write_commands_match(self):
        commands = (
            ("git commit --amend", "git commit"),
            ("git   push --set-upstream", "git push"),
            ("git -C . commit -m x", "git commit"),
            ("git -c user.name=x push", "git push"),
            ("git -cuser.name=x commit", "git commit"),
            ("git --git-dir .git --work-tree . push", "git push"),
            ("env X=1 command git -C . commit -m x", "git commit"),
            ("make lint && git --no-pager push", "git push"),
            ("git -C . commit 'unterminated", "git commit"),
        )
        for command, expected in commands:
            with self.subTest(command=command):
                match = hook.blocked_command(command)[0]
                self.assertEqual(match.get("label", ""), expected)

    def test_unrelated_commands_do_not_match(self):
        for command in (
                "git status", "git -C . log", "pytest", "commit",
                "push origin", "echo 'git commit'", ""):
            with self.subTest(command=command):
                self.assertEqual(hook.blocked_command(command), [])

    def test_match_carries_effective_git_context(self):
        with tempfile.TemporaryDirectory() as directory:
            child = Path(directory) / "child"
            child.mkdir()
            command = f"git -C {child.as_posix()} -c user.name=x commit"
            match = hook.blocked_command(command)[0]
        self.assertIsInstance(match, dict)
        self.assertEqual(match["label"], "git commit")
        self.assertTrue(match["cwd"].endswith("child"))
        self.assertEqual(match["settings"], [("user.name", "x")])

    def test_unparseable_command_returns_ambiguous_context(self):
        matches = hook.blocked_command("git \\\npush --force")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["label"], "unparseable command")
        self.assertTrue(matches[0]["error"])


class FindViolationTest(unittest.TestCase):
    """A repo without the checker cannot clear strict preflight."""

    def test_absent_checker_yields_violation(self):
        with patch.dict(os.environ, {"GITHUB_HEAD_REF": ""}):
            self.assertTrue(hook.find_violation(str(Path(__file__).parent)))

    def test_explicit_project_without_checker_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            violation = hook.check_branch(
                CONFORMING_BRANCH, project_dir=directory)
        self.assertEqual(violation, "branch checker is missing")


class GitMetadataTest(unittest.TestCase):
    """Bounded Git metadata resolves branches without launching Git."""

    def make_repository(self, create_git_dir: bool = True) -> tuple[Path, Path]:
        """Create a temporary repository root and Git directory."""
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        git_dir = root / ".git"
        if create_git_dir:
            git_dir.mkdir()
        return root, git_dir

    def test_symbolic_detached_and_empty_heads(self):
        root, git_dir = self.make_repository()
        head = git_dir / "HEAD"
        head.write_text("ref: refs/heads/feat/metadata\n", encoding="utf-8")
        self.assertEqual(
            hook.current_branch(str(root), allow_environment=False),
            "feat/metadata")
        head.write_text("0123456789abcdef\n", encoding="utf-8")
        self.assertEqual(
            hook.current_branch(str(root), allow_environment=False), "HEAD")
        head.write_text("", encoding="utf-8")
        with self.assertRaises(OSError):
            hook.current_branch(str(root), allow_environment=False)

    def test_gitfile_resolves_and_rejects_invalid_targets(self):
        root, pointer = self.make_repository(create_git_dir=False)
        admin = root / "admin"
        admin.mkdir()
        (admin / "HEAD").write_text(
            "ref: refs/heads/fix/gitfile\n", encoding="utf-8")
        pointer.write_text("gitdir: admin\n", encoding="utf-8")
        self.assertEqual(
            hook.current_branch(str(root), allow_environment=False),
            "fix/gitfile")
        pointer.write_text("invalid\n", encoding="utf-8")
        with self.assertRaises(OSError):
            hook.current_branch(str(root), allow_environment=False)
        pointer.write_text("gitdir: absent\n", encoding="utf-8")
        with self.assertRaises(OSError):
            hook.current_branch(str(root), allow_environment=False)

    def test_regular_metadata_reader_rejects_invalid_files(self):
        root, git_dir = self.make_repository()
        with self.assertRaises(OSError):
            hook._read_regular(str(git_dir), hook.MAX_HEAD_BYTES)
        oversized = root / "oversized"
        oversized.write_text(
            "x" * (hook.MAX_HEAD_BYTES + 1), encoding="utf-8")
        with self.assertRaises(OSError):
            hook._read_regular(str(oversized), hook.MAX_HEAD_BYTES)

    def test_invalid_branch_handles_unreadable_repository_metadata(self):
        root, git_dir = self.make_repository()
        (git_dir / "HEAD").write_text("", encoding="utf-8")
        payload = bash_payload("git branch -m feat/recovered")
        with patch.dict(os.environ, {"GITHUB_HEAD_REF": ""}):
            result = hook._handle_invalid_branch(
                payload, str(root), "claude", "invalid branch")
        self.assertEqual(result, BLOCKING_EXIT_CODE)


class SettingsWiringTest(unittest.TestCase):
    """The hook enforces nothing unless the settings files register it."""

    @staticmethod
    def _commands(settings: dict, event: str) -> list:
        """Return every hook invocation registered for `event`, command and args."""
        return [
            " ".join([entry.get("command", "")] + list(entry.get("args", [])))
            for matcher in settings.get("hooks", {}).get(event, [])
            for entry in matcher.get("hooks", [])
        ]

    def _assert_registers_both_events(self, path: Path):
        settings = json.loads(path.read_text(encoding="utf-8"))
        session_start = self._commands(settings, "SessionStart")
        pre_tool_use = self._commands(settings, "PreToolUse")
        self.assertTrue(
            any("enforce_branch_name.py" in command for command in session_start),
            f"{path.name} does not register the hook for SessionStart",
        )
        self.assertTrue(
            any("enforce_branch_name.py" in command for command in pre_tool_use),
            f"{path.name} does not register the hook for PreToolUse",
        )

    def test_live_settings_register_both_events(self):
        self._assert_registers_both_events(LIVE_SETTINGS)

    def test_example_settings_register_both_events(self):
        self._assert_registers_both_events(EXAMPLE_SETTINGS)

    # foucault adopts only the branch and identity gates from abuzucom/agents
    # (docs/template-drift.md records the declined hooks and why). Per
    # agents/README.md adoption step 14, a subset adopter trims this matrix
    # to what was actually copied rather than asserting hooks that were
    # deliberately left out.
    HOOK_MATCHERS = {
        "enforce_branch_name.py": {"*"},
        "enforce_git_identity.py": {"Bash"},
    }

    @staticmethod
    def _matchers_for(settings: dict, hook_name: str) -> set:
        """Return every PreToolUse matcher that registers `hook_name`."""
        return {
            matcher.get("matcher", "")
            for matcher in settings.get("hooks", {}).get("PreToolUse", [])
            for entry in matcher.get("hooks", [])
            if any(hook_name in part for part in [entry.get("command", "")] + list(entry.get("args", [])))
        }

    def test_pre_tool_use_entries_match_their_hook(self):
        """Each hook is registered under exactly the matchers it needs.

        A hook wired to the wrong matcher never sees the tool call it exists
        to gate, and every behavioral test still passes.
        """
        for path in (LIVE_SETTINGS, EXAMPLE_SETTINGS):
            settings = json.loads(path.read_text(encoding="utf-8"))
            for hook_name, expected in self.HOOK_MATCHERS.items():
                with self.subTest(path=path.name, hook=hook_name):
                    self.assertEqual(self._matchers_for(settings, hook_name), expected)

    @staticmethod
    def _launchers(settings: dict) -> set:
        """Return every program a registered hook would be spawned as."""
        return {
            entry.get("command", "")
            for event in settings.get("hooks", {}).values()
            for matcher in event
            for entry in matcher.get("hooks", [])
        }

    def test_configured_launcher_resolves_on_this_platform(self):
        """A launcher that does not resolve makes every gate fail open.

        Claude Code spawns the exec form directly, with no shell, so
        `command` must name a real executable on PATH. A startup failure
        exits non-zero but not 2, which Claude Code treats as a
        non-blocking error, and the gate waves the call through.

        Asserting on the configured string is the point. Running the
        hooks through `sys.executable`, as the behavioral tests do, keeps
        passing against a configuration that never starts.
        """
        for path in (LIVE_SETTINGS, EXAMPLE_SETTINGS):
            settings = json.loads(path.read_text(encoding="utf-8"))
            for launcher in self._launchers(settings):
                with self.subTest(path=path.name, launcher=launcher):
                    self.assertIsNotNone(
                        shutil.which(launcher),
                        f"{path.name} launches hooks as {launcher!r}, which "
                        f"does not resolve on this platform. Windows has no "
                        f"python3.exe; use 'python' or 'py'. Debian without "
                        f"python-is-python3 has no 'python'; use 'python3'.",
                    )

    def test_every_registered_hook_declares_its_matchers(self):
        """A PreToolUse hook absent from the table above is unreviewed wiring."""
        for path in (LIVE_SETTINGS, EXAMPLE_SETTINGS):
            settings = json.loads(path.read_text(encoding="utf-8"))
            for matcher in settings["hooks"]["PreToolUse"]:
                for entry in matcher.get("hooks", []):
                    parts = [entry.get("command", "")] + list(entry.get("args", []))
                    invocation = " ".join(parts)
                    with self.subTest(path=path.name, command=invocation):
                        self.assertTrue(
                            any(name in invocation for name in self.HOOK_MATCHERS),
                            f"{invocation} is registered but not declared in HOOK_MATCHERS",
                        )


if __name__ == "__main__":
    unittest.main()
