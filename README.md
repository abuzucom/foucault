# Foucault

Operating instructions for an AI agent that reviews employee code before merge, targeting vulnerabilities common in AI-assisted ("vibe") coding.

## What This Is

[`SECURITY.md`](SECURITY.md) is a system prompt / instruction document. Load it into your code review agent (CI bot, PR reviewer, IDE assistant) as its operating instructions. It defines:

- **Operating principles** - assume AI-generated code, attacker mindset, exploitability-first prioritization
- **15 failure-mode classes** - hallucinated dependencies, missing authorization, injection, insecure defaults, weak crypto, and other patterns where convenience beat security
- **An 8-step per-PR workflow** - context, dependencies, surface, data flow, failure paths, config, consistency, report
- **Hard blockers** - findings that auto-BLOCK with no discretion
- **Reporting format and verdict** - `APPROVE | BLOCK | NEEDS-HUMAN`
- **False-positive rules and calibration** - what not to flag, and the ban on inflating severity

## Usage

1. Place `SECURITY.md` at the top of the agent's context (system prompt), before any code.
2. Have the agent execute the section 3 workflow as explicit, labeled steps. If your platform supports multi-step prompting, run each pass separately with only its relevant sections.
3. Require the `VERDICT:` line as the final output; gate merges on it.
4. Validate against historical PRs with known issues before enforcing.

## Customization

The document is stack-agnostic by design. Recommended additions for your deployment:

- Your languages, frameworks, ORM, auth middleware, and secret manager, so fixes are concrete
- Scope boundaries: monorepo paths, vendored and generated files to skip
- A finding suppression/waiver mechanism and who may use it

## Structure

| Section | Purpose |
|---|---|
| 1 | Operating principles |
| 2 | Failure-mode classes (2.1-2.15) |
| 3 | Per-PR review workflow |
| 4 | Test quality rules |
| 5 | Hard blockers |
| 6 | Reporting format |
| 7 | Prohibitions, incl. prompt-injection defense |
| 8 | False positives |
| 9 | Zero-findings protocol |

## Contributing

Keep edits terse and imperative. Do not add rules without an exploit scenario. Keep the document under ~5K tokens; past that, split core prompt from reference material.
