# PR quality review architecture

## Purpose

The quality reviewer applies the `QUALITY.md` policy from `abuzucom/euler` to
one pull request. The reviewer returns a report with a machine-readable
verdict. The workflow fails on `BLOCK` or `NEEDS-HUMAN`.

This review runs beside the security review. The security review applies
`AUDIT.md` and publishes a `security-review` check run. The quality review
applies `QUALITY.md` and publishes a `quality-review` check run. The two
reviews read different policies and publish different check runs.

## Event flow

1. GitHub runs `ci.yml` for the pull request event.
2. GitHub runs `immutable-conflict-check.yml` for the pull request target
   event.
3. Either workflow completion starts `quality-review-pr.yml`. The caller
   subscribes to both workflows so the review starts whichever one finishes
   last.
4. The caller resolves the pull request from the workflow run head revision.
   The caller reads the current pull request from the API for a fork pull
   request so the `safe-to-review` label state is current.
5. The caller reads the most recent `ci` run and the most recent
   `Immutable Compliance` run for the head revision.
6. The review starts only when both runs concluded `success`.
7. A same-repository pull request calls `quality-review.yml` on the euler
   reusable workflow.
8. A fork pull request calls `quality-review.yml` with `fork_review: true`
   after a maintainer applies the `safe-to-review` label.
9. The fork model job waits for approval in the `fork-review` environment.
   The environment supplies `MODEL_API_KEY` after approval.
10. The euler reusable workflow checks out the pinned euler revision into
    `.euler`. The workflow builds the review envelopes and the prescan
    candidates. The workflow uploads the result as an artifact.
11. The model job downloads the artifact, calls the model, and validates the
    report.
12. The workflow posts a fenced pull request comment and publishes a
    `quality-review` check run on the head revision.
13. The final verdict controls the check result.

## Duplicate reviews

More than one trigger event can name the same head revision. GitHub
serializes the caller runs for one head. A later run therefore observes the
completed review check run.

The caller reads the completed `quality-review` check runs for the head
revision. The reviewed rule accepts a check run that the GitHub Actions app
published. Every workflow-authored check run carries that app. A completed
check run that names a review verdict or a fork skip marks the head as
reviewed. The caller then skips the review jobs.

The check run title names the verdict at the pinned euler release. The
title `Euler quality review: no verdict` stands for a provider failure or a
timeout. Such an ending leaves the head unmarked. The next same-head event
starts a fresh review. Each re-run starts one attempt.

## Trust boundary

Fork pull requests receive no review until a maintainer applies
`safe-to-review`. The fork job uses the protected `fork-review` environment.
Configure that environment with required reviewers from maintainers and a
`MODEL_API_KEY` environment secret. Store the fork-review key only in that
environment. The fork caller passes no provider secret to the reusable
workflow. The fork job receives the environment secret after approval.

The workflow-run caller runs with default-branch code. Pull request files
remain review data. The workflow never executes a pull request file. The
workflow does not place title, body, filename, or diff content in shell
syntax.

This caller supplies `pr_number`, `base_sha`, `head_sha`, `pr_title` and
`pr_body` from the resolved pull request. The euler reusable workflow
validates the revisions and the policy reference. It loads its own response
validator from the pinned euler revision. This repository supplies no
response contract for the quality review.

The model verdict is advisory to human review. Prompt injection in the title,
body, or diff can steer the model toward `APPROVE`. Never configure
`quality-review` as a required status. Require a human approval in branch
protection as well.

## Pins and secrets

- The `uses:` reference and the `quality_ref` input carry the same full
  commit SHA. Never a tag or a branch. Record the euler release version in a
  comment beside the pin.
- The caller maps `MODEL_API_KEY` from the `OLLAMA_API_KEY` repository
  secret. The euler adapter loads its provider profile from the pinned euler
  revision. The active profile there is Ollama with `kimi-k2.7-code`.
- The fork environment stores its own `MODEL_API_KEY` value.
- Never use inherited secrets. The job sends an untrusted diff to a
  provider. Inherited secrets hand every repository secret to that path.

## Prescan exclusions

The euler prescan runs the deterministic checkers over the files a pull
request changes, then keeps the findings on added lines. The `exclude_paths`
input carries whitespace-separated globs that the prescan skips.

This caller excludes `eval/cases/**` and `tests/**`. Both hold intentional
defects. The evaluation corpus holds a code sample that a security review
must flag. The test suite holds the same kind of sample.

## Known prescan findings

The euler checkers report seven blocking findings against the current tree.
Each is a deliberate fall-through rather than a swallowed error. The
prescan reports a finding only on an added line in a changed file. The
findings stay quiet until a pull request edits one of these handlers.

- `hooks/_gate_core.py` reports an empty catch block at the repository
  search. The handler continues with the parent directory on a missing
  `.git` entry.
- `hooks/require_consent.py` reports an empty catch block and a check
  suppression. The handler denies the call when the lookup fails. The
  suppression comment names the reason.
- `scripts/check_conflict_markers.py` reports two empty catch blocks. The
  handlers try the next decoding strategy.
- `scripts/check_git_identity.py` reports two empty catch blocks. The
  handlers continue with the next candidate.
- `scripts/prose_policy.py` reports an empty catch block. The handler falls
  back to the given path.

The `hooks/require_consent.py` suppression also contradicts the rule that
disallows a check suppression in this repository. The file is a shared gate
file that must stay byte-identical across the repositories that adopt these
gates. A change needs the shared-file manifest refreshed in every adopting
repository. That work sits outside this change.

## Verdict and check run

The euler reusable workflow publishes a check run named `quality-review`. The
name does not collide with the `security-review` check run. The workflow
posts one pull request comment per review. The comment places the blocking
prescan list, the unreviewed file list, the validation problems, and each
model report inside code fences.

The check run is not a required status. The review posts a comment and a
check run that a reviewer reads. A human decides.

## Manual settings

These steps change repository and provider settings. A repository admin
performs each one:

1. Confirm that the `OLLAMA_API_KEY` repository secret holds the provider
   key the euler provider profile expects.
2. Confirm that the `fork-review` environment holds a `MODEL_API_KEY`
   environment secret and required reviewers from maintainers.
3. Require human review for changes under `.github/workflows/`.
4. Set a spending cap with the provider.

## Failure behavior

The following conditions skip the review and leave no check run:

- a workflow run head revision that resolves to no open pull request;
- a `ci` run that did not conclude `success` for the head revision;
- an `Immutable Compliance` run that did not conclude `success` for the head
  revision;
- a completed `quality-review` check run with a published verdict for the
  head revision;
- a fork pull request without the `safe-to-review` label.

A fork pull request without the label receives a `quality-review` check run
with a `skipped` conclusion and a summary that names the missing label.

A review that ended without a verdict is an exception. The head stays
unmarked. The next same-head event starts a fresh review. To recover from a
provider outage, a maintainer re-runs the `ci` workflow or the
`Immutable Compliance` workflow for the same head revision.

The review never converts a provider failure into an approval. The euler
reusable workflow publishes a blocking check run when the review ends
without a verdict.

## Upgrade procedure

1. Pick a new euler release commit.
2. Diff euler's `quality-review.yml` between the old and new pins.
3. Set the `uses:` pin and the `quality_ref` input to the new commit.
4. Update the version comment beside the pin.
5. Update this document and the `CHANGELOG.md` entry.

## Local testing

- Run `python3 -m unittest tests.test_workflows -v` to check the caller
  wiring.
- Open a documentation-only pull request. The review posts an `APPROVE`
  comment. A missing comment after a few minutes means the run failed. Find
  the `quality-review-pr` run under the default branch in the Actions tab.
