# Foucault

Operating instructions for an AI agent that security-audits code, targeting vulnerabilities common in AI-assisted ("vibe") coding. It works whether you point it at a pull request, a single file, a code fragment, or a whole generated codebase.

## What This Is

[`AUDIT.md`](AUDIT.md) is a system prompt / instruction document. Load it into your audit agent (CI bot, PR reviewer, IDE assistant, or a batch scan of a whole repo) as its operating instructions. It defines:

- **Four review modes**: PR (diff, merge-gated), File (one file on demand), Piece (a fragment with unseen context), and Wholesale (an entire codebase). The failure-mode classes apply in every mode. The workflow and verdict adapt to the context available.
- **Operating principles**: assume AI-generated code, an attacker mindset, exploitability-first prioritization, and awareness of mode and what is out of view
- **15 failure-mode classes**: hallucinated dependencies, missing authorization, injection, insecure defaults, weak crypto, and other patterns where convenience beat security
- **An 8-step workflow**: context, dependencies, surface, data flow, failure paths, config, consistency, report, with a per-mode substitution on each step
- **Hard blockers**: findings that auto-BLOCK with no discretion
- **Mode-appropriate verdicts**: `APPROVE | BLOCK | NEEDS-HUMAN` for PRs, a prioritized `RISK` summary for File/Wholesale, findings plus an assumptions block for Piece, and a `VERDICT_JSON` companion on every mode so CI can gate on structure instead of prose
- **False-positive rules and calibration**: what not to flag, and the ban on inflating severity

## Usage

1. Place `AUDIT.md` at the top of the agent's context (system prompt), before any code.
2. Establish the review mode (section 0) from what you feed the agent: a diff (PR), a file (File), a fragment (Piece), or a tree (Wholesale). When in doubt, the agent defaults to the narrower mode.
3. Have the agent execute the section 3 workflow as explicit, labeled steps. If your platform supports multi-step prompting, run each pass separately with only its relevant sections.
4. Require the final line for that mode as output: the `VERDICT:` line in PR mode (gate merges on it), or the `RISK:` summary in File/Wholesale mode.
5. Validate against historical PRs or files with known issues before enforcing.

## Versioning

Pin a tag or commit SHA when loading `AUDIT.md` into a deployment, rather
than tracking `main`. `CHANGELOG.md` records what changed release to
release, including any change to a verdict, a hard blocker, or the
`VERDICT_JSON` schema. Record the pin in `adopters/<repo>.md`.

## Verifying Changes

`eval/` holds a golden corpus: small fixtures paired with the verdict
`AUDIT.md` should produce for each. `python eval/run_eval.py` validates the
case set's structure; add `--model-call module:function` to run it against
a real model. See [`eval/README.md`](eval/README.md). Any change to
`AUDIT.md` affecting a verdict, a hard blocker, or a severity mapping ships
with a new or updated case.

## CI Integration

[`.github/workflows/security-review.yml`](.github/workflows/security-review.yml)
is a reusable `workflow_call` reference implementation: check out a pull
request diff, load `AUDIT.md`, run an adopter-supplied model-call command,
post the report as a PR comment, and optionally fail the check on `BLOCK`.
foucault ships no model credential or provider lock-in; the model call is
one shell command supplied by the adopting repository. Pin the `uses:` line
and the `audit_ref` input to the same full commit SHA. See the workflow
file's header comment for the exact adoption snippet.

## Customization

The document is stack-agnostic by design. Recommended additions for your deployment:

- Your languages, frameworks, ORM, auth middleware, and secret manager, so fixes are concrete
- Scope boundaries: monorepo paths, vendored and generated files to skip
- A finding suppression/waiver mechanism and who may use it

## Structure

| Section | Purpose |
|---|---|
| 0 | Review modes (PR, File, Piece, Wholesale) |
| 1 | Operating principles |
| 2 | Failure-mode classes (2.1-2.15) |
| 3 | Review workflow (mode-aware) |
| 4 | Test quality rules |
| 5 | Hard blockers |
| 6 | Reporting format |
| 7 | Prohibitions, incl. prompt-injection defense |
| 8 | False positives |
| 9 | Zero-findings protocol |

## Organization Policy Suite

foucault and [`abuzucom/agents`](https://github.com/abuzucom/agents) share a
philosophy (defend against AI-assisted, "vibe" coding failure modes) and
split the work by when it runs:

- **agents** guards work in progress and future progress. It is proactive
  and hook-enforced: a canonical `AGENTS.md`, synced copies for eight
  coding-agent tools, and Claude Code hooks that block a violation live, as
  it happens, before a commit or a tool call completes.
- **foucault** reviews a pull request or a piece of work on demand. It is
  reactive and manually or CI invoked: a system prompt for an audit agent,
  run against a diff, a file, a fragment, or a whole tree, after the code
  already exists.

The two documents cover overlapping subject matter by design. `AGENTS.md`
Rule 1 (no untrusted input in queries or commands), Rule 7 (no MD5/SHA-1 in
security contexts), and Rule 8 (no committed secrets) try to stop an agent
from writing the defect. `AUDIT.md` sections 2.5, 2.7, and 2.3 try to catch
it if that defect ships anyway. Each repository maintains its own document
independently. Exact wording can drift as a result. The different trigger
model makes drift an expected outcome, not a bug. This repository's
own [`AGENTS.md`](AGENTS.md) is a bespoke subset of the `abuzucom/agents`
template, not a copy of it. `docs/template-drift.md` records the kept and
dropped rules, the reason for each, and drift against the pinned upstream
commit.

## Contributing

See [`AGENTS.md`](AGENTS.md) for the rules governing changes to this repository, including the requirement that any change to `AUDIT.md` affecting a verdict, blocker, or severity mapping ships with an `eval/` case demonstrating it.
