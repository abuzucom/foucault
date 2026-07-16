# Foucault

Operating instructions for an AI agent that security-audits code, targeting vulnerabilities common in AI-assisted ("vibe") coding. It works whether you point it at a pull request, a single file, a code fragment, or a whole generated codebase.

## What This Is

[`SECURITY.md`](SECURITY.md) is a system prompt / instruction document. Load it into your audit agent (CI bot, PR reviewer, IDE assistant, or a batch scan of a whole repo) as its operating instructions. It defines:

- **Four review modes** - PR (diff, merge-gated), File (one file on demand), Piece (a fragment with unseen context), and Wholesale (an entire codebase). The failure-mode classes apply in every mode; the workflow and verdict adapt to the context you have.
- **Operating principles** - assume AI-generated code, attacker mindset, exploitability-first prioritization, and know your mode and what you can't see
- **15 failure-mode classes** - hallucinated dependencies, missing authorization, injection, insecure defaults, weak crypto, and other patterns where convenience beat security
- **An 8-step workflow** - context, dependencies, surface, data flow, failure paths, config, consistency, report, with a per-mode substitution on each step
- **Hard blockers** - findings that auto-BLOCK with no discretion
- **Mode-appropriate verdicts** - `APPROVE | BLOCK | NEEDS-HUMAN` for PRs; a prioritized `RISK` summary for File/Wholesale; findings plus an assumptions block for Piece
- **False-positive rules and calibration** - what not to flag, and the ban on inflating severity

## Usage

1. Place `SECURITY.md` at the top of the agent's context (system prompt), before any code.
2. Establish the review mode (section 0) from what you feed the agent: a diff (PR), a file (File), a fragment (Piece), or a tree (Wholesale). When in doubt, the agent defaults to the narrower mode.
3. Have the agent execute the section 3 workflow as explicit, labeled steps. If your platform supports multi-step prompting, run each pass separately with only its relevant sections.
4. Require the final line for that mode as output: the `VERDICT:` line in PR mode (gate merges on it), or the `RISK:` summary in File/Wholesale mode.
5. Validate against historical PRs or files with known issues before enforcing.

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

## Contributing

Keep edits terse and imperative. Do not add rules without an exploit scenario. Keep the document under ~5K tokens; past that, split core prompt from reference material.
