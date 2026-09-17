# Changelog

This file documents every notable project change.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project follows Semantic Versioning. Pin a tag or commit SHA when
loading `AUDIT.md` into a deployment.

## [3.3.4] (2026-09-17)

### Fixed

- Retried the model call once when the first response fails structure
  validation. Logged only the validator's structural error on final failure.

## [3.3.2] (2026-09-17)

### Fixed

- Retried the model call once when the first response fails structure
  validation. Logged a bounded response tail on a final validation failure.

## [3.3.1] (2026-09-17)

### Fixed

- Skipped duplicate model calls for an already-reviewed head revision. The
  caller cancels parallel runs for one head and skips the review when a
  completed check run with a verdict exists for it.

## [3.3.0] (2026-09-17)

### Added

- Published the review result as a `security-review` check run on the pull
  request head. The review now appears in the pull request checks box. The
  summary sanitizes the model-influenced verdict line. The publication
  carries a timeout and one retry. A publication failure after a successful
  review logs a warning and keeps the job green.

## [3.2.4] (2026-09-17)

### Fixed

- Switched the active review model to `kimi-k2.7-code` and raised the output
  budget to 16384 tokens. `gpt-oss:20b` returned empty or malformed responses
  on two of three review runs.

## [3.2.3] (2026-09-17)

### Fixed

- Listed the `ambiguous-hook-provenance-pr` and `policy-reinjection-hook-pr`
  cases in the `eval/README.md` case table.

## [3.2.2] (2026-09-17)

### Fixed

- Posted the review comment to the resolved pull request number. The comment
  step read `context.issue.number`, which is empty under `workflow_run`.
- Added a regression test for the review-comment pull request target.

## [3.2.1] (2026-09-17)

### Fixed

- Forwarded sanitized adapter diagnostics on model-command failure. CI logs
  now show the provider error class without credentials or control
  characters.

## [3.2.0] (2026-09-16)

### Added

- `AUDIT.md` rules: dependency confusion and install-time download-and-execute
  (2.1), webhook signature verification, WebSocket upgrade, Origin, and
  per-message authorization, and host-header link trust (2.4), spreadsheet
  formula injection and prototype pollution (2.5), CI run-step interpolation
  of untrusted context (step 3.6), contradictory or impossible logic with
  precondition ordering (2.13), and GraphQL depth and decompression limits
  (2.11).
- Eleven eval cases covering the new rules: `dependency-confusion-file`,
  `install-script-pr`, `webhook-no-signature-file`,
  `websocket-no-origin-file`, `csv-formula-injection-file`,
  `ci-workflow-injection-pr`, `contradictory-logic-file`,
  `host-header-reset-file`, `prototype-pollution-file`,
  `graphql-limits-file`, `decompression-bomb-file`.

### Changed

- Compressed `AUDIT.md` prose without altering any rule. The freed budget funds
  the new content under the 32768-character ceiling.
- Rewrote `AUDIT.md` prose into single-clause sentences. No rule, verdict
  token, or cross-reference changed.
- Pinned `AUDIT.md` to LF line endings in `.gitattributes`. The upstream
  convention stores LF only.
- Refreshed the upstream drift manifest hash for `CHANGELOG.md`.

## [3.1.5] (2026-09-15)

### Fixed

- Sanitized control characters and credential-like values in trusted GitHub
  command diagnostics.
- Reconciled secure Git delivery guidance with `abuzucom/agents` main at
  `d486437`.
- Documented the end-to-end wrapper audit, retained local protections, and
  final-argument gate evaluation.
- Refreshed the upstream drift manifest after the reconciliation so CI checks
  all locally adapted files at their current normalized hashes.
- Restored synchronized policy copies after the detailed documentation update.
- Adopted upstream UTF-8 subprocess decoding with replacement handling for
  GitHub, Git, identity, hook, and test-first diagnostics.
- Enforced LF policy line endings in the working tree and policy-size checker.

## [3.1.4] (2026-09-15)

### Fixed

- Kept intentional weak-hash evaluator fixtures available for model review.
- Preserved weak-hash enforcement for production code.

## [3.1.3] (2026-09-15)

### Fixed

- Preserved the intentional weak-hash evaluator fixture.
- Resolved workflow-run pull requests through the GitHub API by head SHA.
- Removed bearer headers from pull request head fetches.

## [3.1.2] (2026-09-15)

### Fixed

- Made the adapter path test portable across Windows and Linux runners.

## [3.1.1] (2026-09-15)

### Fixed

- Started PR model review from the trusted workflow-run path.
- Kept immutable compliance compatible with the review workflow trigger.
- Made the model command test portable across Python executable names.
- Marked the intentional weak-hash evaluator fixture for checker review.

## [3.1.0] (2026-09-15)

### Added

- Automatic same-repository pull request security review triggers.
- Ollama, OpenAI-compatible, Anthropic, and Google provider adapters.
- Reviewed provider configuration and exact endpoint allowlisting.
- Shell-free model command execution and report validation.
- Fork pull request skip handling without provider secret exposure.
- Bounded provider retries, input sizes, output sizes, and response parsing.
- PR security review architecture and provider setup documentation.

### Security

- Prevented pull request content from reaching shell syntax or dynamic URLs.
- Preserved base-only workflow execution and fail-closed verdict handling.

### Documentation

- Documented model request formats, provider secrets, data transfer, local
  testing, failure behavior, and performance safeguards.

## [3.0.2] (2026-09-14)

### Fixed

- Accepted historical changelog headings during version range checks.

## [3.0.1] (2026-09-14)

### Fixed

- Hardened trusted GitHub wrapper context across checkout and worktree layouts.
- Added test-first enforcement for executable changes.
- Denied additional GitHub authentication scope options.

## [3.0.0] (2026-09-14)

### Changed

- Re-adopted the `abuzucom/agents` 2.0 contract at immutable commit
  `7de83d04224784774dcfd1a21462bf23315bdeae`.
- Added complete cross-platform command, infrastructure, consent, lifecycle,
  GitHub, branch, and identity enforcement.
- Added synchronized policy copies for supported agent clients.
- Added immutable compliance, attribution, coverage, drift, and checker
  validation to CI.

### Breaking

- Agent workflows now require the complete policy and gate registration set.
- Missing client hooks, shared modules, or policy copies fail adoption checks.

## [2.0.1] (2026-09-14)

### Fixed

- Calibrated `AUDIT.md` section 8 to avoid treating stricter agent permissions
  and matching test expectation changes as security findings without concrete
  harmful impact.

### Added

- `eval/cases/agent-hardening-calibration-pr` regression coverage for command
  policy tightening and matching test expectation updates.

## [2.0.0] (2026-09-13)

### Fixed

- Closed short-flag, attached-flag, and branch-context bypasses in delivery
  verification.
- Added trusted GitHub CLI routing with bounded account checks, repository-safe
  executable lookup, managed-proxy handling, token-output denial, and
  delivery-safe diagnostics.
- Added delivery evidence rules that distinguish unverified state from failed
  operations and require remote read-back before completion claims.

### Added

- Provenance-separated evaluator input with pinned policy hashing. Hook context
  is read-only and cannot support review findings.
- Local evaluation no longer trusts a self-referential in-repository policy
  hash. Production policy integrity remains anchored by the immutable workflow
  revision.

- Twenty rules and a workflow step across `AUDIT.md`, closing gaps found by
  assessing fifteen review checklists against it. Injection gains XXE, template
  injection, open redirect, second-order injection, upload content validation
  and content-type discipline. Authentication gains session, token, delegated
  authorization and credential-path lifecycle rules. Crypto gains construction,
  primitive strength, integrity and comparison. Insecure defaults gains the
  served-file and diagnostic surface, plus a gated group for systems that run
  agents or untrusted code in a sandbox. LLM risks gain instruction-channel
  integrity, trust propagation and the tool boundary. Concurrency gains lost
  update and single-executor coordination.
- A ninth hard blocker in section 5: XML from externally influenced input
  parsed with external entities or DTDs enabled.
- Step 0 of the review workflow, applicability. A class whose sink is absent
  from the review unit is neither a finding nor a clean result. Section 6 now
  distinguishes not applicable from reviewed and clean.
- Four investigation sweeps in section 3, covering the authorization surface,
  crypto call sites, model invocations and prompt composition, and the response
  and logging configuration.
- Thirty-nine `eval/cases/` fixtures, one per new idea, using instances the
  source checklists did not name so a pass shows the rule generalized.
- `eval/cases/policy-reinjection-hook-pr`: a hook that re-delivers a
  repository's own `AGENTS.md` to its own agent session. The pass condition
  is a clean verdict. The delivery mechanism for the trusted channel is not
  untrusted content entering it.

### Fixed

- `AUDIT.md` section 7 requires a real location in the review target for
  every finding. A lifecycle hook's injected context, this system prompt, a
  synchronized `CLAUDE.md`, and tool output all place text in the review
  session that the target does not contain. Section 6 demands `file:line`.
  An agent flagging session-context text under section 7 invented a file and
  a commit hash to satisfy the format. The resulting HIGH finding directed a
  maintainer to rewrite history against a commit that did not exist. Section
  8 gains the matching false-positive entry. Two checks bound it. A hook
  resolving its policy root by upward search remains a finding. Identical
  directive text committed into a reviewed file remains a finding.

### Changed

- `AUDIT.md` states the MD5 exception once, points step 3.4 at principle 1.5,
  and drops two clauses duplicated across classes. Repetition of the mode rule,
  the Piece-mode clean-verdict bar and the severity threshold is deliberate
  agent steering and is preserved.
- `AGENTS.md` and `CONTRIBUTING.md` state the 32768-character ceiling in place
  of a stale token budget, and `CONTRIBUTING.md` gains the standing rule for
  incoming checklists: assess against what `AUDIT.md` already says, extend by
  default, and add a rule only for a distinct sink, scenario or fix.

## [1.0.0] (2026-09-01)

### Changed (breaking)

- Renamed the distributed audit-agent system prompt from `SECURITY.md` to
  `AUDIT.md`. `SECURITY.md` is now this repository's own vulnerability-
  disclosure policy, resolving a filename collision with GitHub's native
  convention and with `abuzucom/agents`' own `SECURITY.md.example`
  adoption step. A deployment loading the old `SECURITY.md` path as its
  audit prompt needs its load path updated to `AUDIT.md`.

### Added

- `VERDICT_JSON` machine-readable companion to `AUDIT.md` section 6. Lets
  CI gate on structure instead of parsing the prose verdict line.
- `eval/`: a golden-corpus harness (`run_eval.py`) and eight fixtures
  validating verdicts across hard blockers, mode-specific behavior, and
  false-positive discipline.
- `.github/workflows/security-review.yml`: a reusable, adoptable reference
  CI workflow that runs `AUDIT.md` against a pull request and posts the
  report.
- `AGENTS.md`: a bespoke, security-work-specific instruction file for this
  repository (not a copy of `abuzucom/agents`' generic template). Adopts
  the branch-name and git-identity Claude Code hooks in full, plus the
  style/prose checker scripts, from `abuzucom/agents`.
- `docs/template-drift.md`, `upstream-files.json`,
  `scripts/check_upstream_drift.py`: drift tracking against the pinned
  `abuzucom/agents` commit, and a mechanism for reviewing upstream changes
  for adoption.
- `adopters/`: adoption-tracking scaffold.
- `LICENSE` (BSD 3-Clause, matching `abuzucom/agents`), `CONTRIBUTING.md`,
  and a proper project `SECURITY.md`.
- An "Organization Policy Suite" section in `README.md` documenting the
  relationship between foucault and `abuzucom/agents`.

## Historical pre-1.0.0

- `SECURITY.md` (now `AUDIT.md`). Four review modes, 15 failure-mode
  classes, an 8-step workflow, hard blockers, and false-positive rules.
