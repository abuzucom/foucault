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
| `xxe-pr` | PR | 2.5, external entities enabled, hard blocker |
| `ssti-file` | File | 2.5, user input compiled as a template |
| `xss-and-redirect-file` | File | 2.5, DOM sink and a prefix-matched redirect |
| `key-custody-pr` | PR | 2.3, provider key inlined into a browser bundle |
| `second-order-injection-file` | File | 2.5, safe write, unsafe later read |
| `ldap-filter-injection-file` | File | 2.5, query construction outside SQL |
| `upload-validation-pr` | PR | 2.5, extension-only typing into a served path |
| `content-type-switch-file` | File | 2.5, parser chosen by sniffing the body |
| `zip-slip-file` | File | 2.5, archive entry names as an unrecognized source |
| `session-lifecycle-file` | File | 2.4, no rotation, no server-side invalidation |
| `token-validation-file` | File | 2.4/2.7, algorithm confusion and absent claims |
| `delegated-authz-pr` | PR | 2.4, no state, no PKCE, caller-supplied redirect |
| `credential-path-file` | File | 2.4, second factor bypassed by a parallel route |
| `type-coercion-bypass-file` | File | 2.4/2.5, the checked value is not the used value |
| `password-storage-file` | File | 2.7, work factor below floor plus a reversible copy |
| `primitive-strength-file` | File | 2.7, unnamed weak cipher and an undersized key |
| `crypto-construction-file` | File | 2.7, MAC-then-encrypt padding oracle |
| `hmac-timing-compare-file` | File | 2.7, early-return digest comparison |
| `deployment-surface-file` | File | 2.6, directory listing, reachable dotfiles, version banner |
| `error-and-output-leak-file` | File | 2.8/2.12, correct rejection leaking internals |
| `data-lifecycle-file` | File | 2.12, unencrypted at rest, no deletion path, whole-object logging |
| `instruction-channel-pr` | PR | 2.15, system prompt composed from tenant data |
| `agent-trust-propagation-file` | File | 2.15, model output reloaded as fact |
| `rag-provenance-file` | File | 2.15, retrieved chunks with an inverted hierarchy |
| `sandbox-privilege-pr` | PR | 2.6, privileged container with a mounted socket |
| `git-hooks-untrusted-repo-file` | File | 2.6, hooks in a user-supplied repository |
| `sandbox-network-file` | File | 2.6, unrestricted egress and reachable metadata |
| `sandbox-fallback-file` | File | 2.8/2.6, sandbox degrading to host execution |
| `agent-env-inheritance-pr` | PR | 2.6, worker inheriting the full parent environment |
| `tool-output-secret-leak-file` | File | 2.15, credentials through the tool boundary |
| `llm-output-to-markdown-file` | File | 2.5/2.15, model output rendered into markdown |
| `no-lockfile-file` | File | 2.1, no lockfile at all |
| `dependency-health-file` | File | 2.1, overlapping, unmaintained and unpinned packages |
| `copyleft-dependency-file` | File | 2.14, copyleft dependency in a proprietary product |
| `deprecated-unsafe-api-file` | File | 2.2, unsafe superseded API with the warning suppressed |
| `lost-update-file` | File | 2.9, read-modify-write with no concurrency check |
| `distributed-lock-pr` | PR | 2.9, scheduled job without a single executor |
| `authz-sweep-wholesale` | Wholesale | section 3, one route of four missing its guard |
| `inapplicable-classes-file` | File | section 3 step 0, classes that do not apply are not findings |
