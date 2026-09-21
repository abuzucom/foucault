# Foucault

Foucault is a security review policy and validation system for LLM-assisted
software development. It applies explicit rules to pull requests, files, code
fragments, and generated codebases. It produces actionable findings, evidence
requirements, and machine-readable verdicts.

## Design Position

Foucault uses operational controls. Each control identifies a condition, an
action, required evidence, and a result. Local checkers, evaluator cases, CI
workflows, and model adapters provide the enforcement surface.

Foucault does not rely on personal appeals to an LLM. It does not use dramatic
authority claims to override the policy. It does not use contradictory escape
valves that grant unrestricted authority and then attempt to restore safety
with a later prohibition. A security boundary must remain valid across the
execution path.

[`AUDIT.md`](AUDIT.md) defines the review contract. It separates review
evidence from trusted lifecycle context. It specifies controls, escalation
rules, and output contracts. It defines:

- **Four review modes**: PR (diff, merge-gated), File (one file on demand), Piece (a fragment with unseen context), and Wholesale (an entire codebase). The failure-mode classes apply in every mode. The workflow and verdict adapt to the context available.
- **Review principles**: attacker-path analysis, exploitability-first prioritization, explicit context boundaries, and evidence-based findings
- **15 failure-mode classes**: hallucinated dependencies, missing authorization, injection, insecure defaults, weak crypto, and other patterns where convenience beat security
- **A 9-step workflow**: applicability, context, dependencies, entry points, data flow, failure paths, config, consistency, and report, with a per-mode substitution on each step
- **Hard blockers**: findings that auto-BLOCK with no discretion
- **Mode-appropriate verdicts**: `APPROVE | BLOCK | NEEDS-HUMAN` for PRs, a prioritized `RISK` summary for File/Wholesale, findings plus an assumptions block for Piece, and a `VERDICT_JSON` companion on every mode so CI can gate on structure instead of prose
- **False-positive rules and calibration**: what not to flag, and the ban on inflating severity

## Operational Use

1. Load `AUDIT.md` as the system policy before the review target.
2. Select the review mode from the supplied material: diff, file, fragment, or tree.
3. Apply the section 3 workflow as labeled checks.
4. Require the mode-specific `VERDICT:` or `RISK:` output.
5. Validate the policy against known cases before enabling merge gates.

The model supplies analysis. The policy supplies the rules. Repository tools
validate structure, size, synchronization, evaluator cases, workflow wiring,
and report format. CI determines whether those checks pass.

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

Run `make audit-check` for the local AUDIT.md checker, policy-size check, and
structure-only evaluator. The checker enforces required sections, verdict
tokens, injection controls, provenance controls, ASCII text, LF endings, and
the 32 KiB policy limit. It also rejects prose lines over 120 characters while
allowing tables and exact-format output lines.

## CI Integration

[`security-review-pr.yml`](.github/workflows/security-review-pr.yml) invokes
the reusable workflow after the trusted immutable compliance workflow
completes. The workflow reads the base revision, fetches the pull request head
without checking it out, and builds one provenance-labeled review envelope.
Fork pull requests receive an explicit skip result because provider secrets
are unavailable to them.

[`security-review.yml`](.github/workflows/security-review.yml) loads the
immutable `AUDIT.md` revision, calls the configured provider adapter, posts a
fenced report, and gates on the final `VERDICT` line. The adapter reads the
provider profile from [`ci/model_providers.json`](ci/model_providers.json).
The active profile uses Ollama with `kimi-k2.7-code`.

The caller maps one provider-specific repository secret, such as
`OLLAMA_API_KEY`, to the reusable workflow's `MODEL_API_KEY` secret. Provider
endpoints remain allowlisted in the adapter. Review content reaches only the
configured provider endpoint. See [`docs/pr-security-review.md`](docs/pr-security-review.md)
for setup, data flow, provider changes, failure behavior, and local testing.

Pull request CI runs the AUDIT.md checker, evaluator corpus, policy-diff
summary, synchronization checks, workflow safety checks, and repository tests.
The scheduled validation workflow repeats policy, evaluator, and test checks
weekly and through manual dispatch.

## Customization

The policy is stack-agnostic. Add deployment-specific details when they improve finding accuracy:

- Languages, frameworks, ORM, authentication middleware, and secret manager
- Scope boundaries: monorepo paths, vendored and generated files to skip
- Finding suppression or waiver rules and permitted approvers

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
| 8 | False-positive exclusions |
| 9 | Zero-findings protocol |

## Different Control Point From Agent Governance

Foucault and [`abuzucom/agents`](https://github.com/abuzucom/agents) address
different operational control points:

- **agents** governs implementation-time operations. It defines repository
  rules, command gates, file gates, lifecycle controls, and authorization
  boundaries for coding-agent tools.
- **foucault** evaluates proposed or existing artifacts. It applies security
  checks to a diff, file, fragment, or whole tree. It produces findings,
  evidence requirements, severity, and verdicts.

The two systems can cover the same vulnerability class at different points in
the workflow. `AGENTS.md` can prevent unsafe command construction during
implementation. `AUDIT.md` can identify unsafe command construction in a
review target. The implementation control and the review control remain
separate. Neither replaces the other.

Foucault treats policy text as an operational contract. A rule without a
check receives a stated tooling limitation. A claimed check must exist in
scripts, tests, CI, or an adapter. A verdict must identify its evidence and
provenance. A missing or ambiguous control escalates to `NEEDS-HUMAN` rather
than relying on a rhetorical exception.

This repository's [`AGENTS.md`](AGENTS.md) preserves Foucault-specific
repository safeguards alongside the adopted upstream contract.
`docs/template-drift.md` records adaptations and drift against the pinned
upstream commit.

The adoption uses `scripts/sync.py` for policy copies and
`shared-files.json` for cross-repository gate integrity. CI checks policy
size, synchronization, gate completeness, launcher startup, hook coverage,
workflow safety, attribution, and immutable compliance.

The trusted GitHub wrapper supplies validated repository context from the
local checkout or worktree. The wrapper fails closed when context is missing
or unsafe. Pull request creation receives a validated head context when no
head option exists. Windows, macOS, and Linux worktree layouts are supported.

The wrapper decodes GitHub CLI output as UTF-8 and replaces malformed bytes.
If a Windows log request reports a codec error, enable Python UTF-8 mode for
diagnosis and rerun the command:

```powershell
$env:PYTHONUTF8 = "1"
python scripts/trusted_gh.py run <gh arguments>
```

The environment setting diagnoses codec selection. It does not replace the
wrapper's explicit decoding behavior.

The implementation policy requires runtime approval evidence for elevated or
external execution. Repository hooks enforce observable command gates. An
external harness must enforce client output claims when the client API hides
them.

## Contributing

Every repository action requires an active-user request. Do not run Git commands before consent.
Use `scripts/read_git_state.py` for state checks.

See [`AGENTS.md`](AGENTS.md) for the rules governing changes to this repository, including the requirement that any change to `AUDIT.md` affecting a verdict, blocker, or severity mapping ships with an `eval/` case demonstrating it.
