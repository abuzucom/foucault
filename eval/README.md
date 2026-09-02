# Eval harness

Golden-corpus regression tests for `AUDIT.md`. Each case under `cases/` is a
small code sample (or diff) paired with the verdict a careful reviewer
applying `AUDIT.md` should produce. `AGENTS.md` requires a new or updated
case for any change to `AUDIT.md` that affects a verdict, a hard blocker, or
a severity mapping.

## Why this exists

`AUDIT.md` is a system prompt. Nothing about a well-written instruction
document guarantees a model actually follows it. This harness is the
difference between trusting the prompt and checking it: run every case
against a real model call and confirm the verdicts still match after any
edit.

## Model-agnostic by design

`run_eval.py` never calls a model API and ships no credentials. Point it at
a locally supplied callable:

```console
python eval/run_eval.py --model-call mymodule:call_model
```

`call_model(system_prompt, mode, case_text) -> str` loads `AUDIT.md` as the
system prompt, sends `case_text` (the fixture plus any `context.md`) as a
user-turn message, and returns the model's raw text response. Wire it to
whichever provider and model an `AUDIT.md` deployment actually uses. This
repository does not prescribe one.

`--model-call` resolves to an importable module and executes its code. Treat
it as a trusted input. Supply it only from a local invocation or a CI
configuration under this repository's control, never from pull request content
or any other value an outside contributor can influence. `ci.yml` never passes
it.

Without `--model-call`, the script runs structure-only. It confirms every
`expected.json` and fixture file parses and is internally consistent, then
exits 0. This is what runs in this repository's own CI, since foucault
ships no model credential. Any consumer with a model credential can run the
live check the same way.

## Case format

```
eval/cases/<slug>/
  diff.patch | input.<ext>   one or more input files (the review unit)
  context.md                 optional: PR description or ticket text
  expected.json              required
```

`expected.json` fields:

| Field | Meaning |
|---|---|
| `mode` | `PR`, `File`, `Piece`, or `Wholesale` (AUDIT.md section 0) |
| `expected_verdict` | Substring the response's `VERDICT:`/`RISK:` line must contain, e.g. `BLOCK`, `RISK: CRITICAL`, `RISK (partial)` |
| `expected_classes` | AUDIT.md section 2.x references the case exercises |
| `expect_json` | If `true`, the harness also requires a parseable `VERDICT_JSON:` block (AUDIT.md section 6) |
| `notes` | Why this verdict is correct, for a human reviewing the case |
| `fixture_notes` | Optional: provenance of any secret-shaped value in the fixture (see below) |

## Secret-shaped fixtures

A case testing secret detection (`AUDIT.md` 2.3) needs a value with real
entropy, because entropy is the signal the review workflow keys on. `hardcoded-secret-pr` uses a string generated fresh with Python's `secrets`
module for that fixture alone. It has never been a working credential for
any account or service. `AGENTS.md` non-negotiable rule 1 requires this for
every case: synthetic and high-entropy where the case needs entropy,
low-entropy and placeholder-shaped where the case tests the false-positive
rule instead (`clean-*` cases), never copied from a real system.

## Current cases

| Case | Mode | Tests |
|---|---|---|
| `sql-injection-pr` | PR | 2.5, string-concatenated SQL, hard blocker |
| `hardcoded-secret-pr` | PR | 2.3/2.6, committed high-entropy secret, hard blocker |
| `weak-hash-password-file` | File | 2.7, MD5 password hash, hard blocker |
| `missing-authz-idor-pr` | PR | 2.4, IDOR on a data-mutating endpoint, hard blocker |
| `ssrf-file` | File | 2.5, unvalidated server-side fetch |
| `piece-fragment-unseen-caller` | Piece | section 6, never a clean verdict when safety depends on unseen code |
| `clean-parameterized-query-pr` | PR | section 8, a parameterized query is not a finding |
| `clean-file-wholesale` | File | section 9, zero-findings protocol on genuinely clean code |
