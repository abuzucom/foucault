# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows SemVer. Pin a tag or commit SHA when loading `AUDIT.md`
into a deployment.

## [Unreleased]

### Added

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

### Changed

- `AUDIT.md` states the MD5 exception once, points step 3.4 at principle 1.5,
  and drops two clauses duplicated across classes. Repetition of the mode rule,
  the Piece-mode clean-verdict bar and the severity threshold is deliberate
  agent steering and is preserved.
- `AGENTS.md` and `CONTRIBUTING.md` state the 32768-character ceiling in place
  of a stale token budget, and `CONTRIBUTING.md` gains the standing rule for
  incoming checklists: assess against what `AUDIT.md` already says, extend by
  default, and add a rule only for a distinct sink, scenario or fix.

## [1.0.0]: first tagged release

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

## [Unreleased before 1.0.0]

- `SECURITY.md` (now `AUDIT.md`). Four review modes, 15 failure-mode
  classes, an 8-step workflow, hard blockers, and false-positive rules.
