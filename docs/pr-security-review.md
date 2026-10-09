# PR security review architecture

## Purpose

The PR reviewer applies `AUDIT.md` to one pull request. The reviewer returns a
report with a machine-readable verdict. The workflow fails on `BLOCK` or
`NEEDS-HUMAN` by default.

## Event flow

1. GitHub starts `immutable-conflict-check.yml` for the pull request event.
2. GitHub starts `security-review-pr.yml` after that workflow completes.
3. Applying `safe-to-review` to a fork pull request also starts
   `security-review-pr.yml` from the base repository's default branch.
4. The caller resolves the pull request from the workflow-run head or the
   labeled pull request event.
   The caller skips the review only when two records exist for that revision.
   The first is a completed `security-review` check run with a verdict. The
   second is a `security-review-verdict-<head_sha>` artifact. A workflow run
   of the caller file on the default branch must have uploaded that artifact.
5. For label events, the caller requires a successful
   `Immutable Compliance` run for the same head revision.
6. The caller checks whether the head repository matches the base repository
   and reads its current labels from the GitHub API.
7. A same-repository pull request calls `security-review.yml` on the existing
   path.
8. A fork pull request calls `security-review.yml` only after
   `safe-to-review` appears on the pull request.
9. The fork model job waits for approval in the `fork-review` environment.
   The environment supplies `MODEL_API_KEY` after approval.
10. Each reusable workflow path allows one active model review per pull request.
   A newer head cancels an obsolete in-progress review.
11. An unlabeled fork pull request runs the skip job. The skip job receives no
    provider secret.
12. The reusable workflow checks out the base commit. It verifies that the
   caller checkout holds every review script.
13. The workflow fetches the head commits without checking them out.
14. The case builder creates one merge-base diff and one review envelope. The
    envelope carries the SHA-256 digest of the loaded policy.
15. `ci/run_model_command.py` validates the adapter command without a shell.
16. `ci/call_model.py` sends one request to the active provider.
17. The workflow validates the report and posts a fenced comment. The comment
    identifies its base commit, head commit, and workflow run. The workflow
    then uploads the verdict record artifact.
18. The final verdict controls the check result.
19. The workflow publishes a `security-review` check run on the pull request
    head.

## Trust boundary

Fork pull requests receive no review until a maintainer applies
`safe-to-review`. The fork job uses the protected `fork-review` environment.
Configure that environment with required reviewers from maintainers and a
`MODEL_API_KEY` environment secret. Store the fork-review key only in that
environment. The fork caller passes no provider secret to the reusable
workflow. The fork job receives the environment secret after approval.

The workflow-run caller runs with default-branch code. Pull request files
remain review data. The workflow never executes a pull request file. The
workflow does not place title, body, filename, or diff content in shell syntax.

The workflow-run event supplies the head revision. The trusted GitHub API
resolves one matching pull request and supplies its number and revisions. The
API request uses the base repository and validated head revision. The
workflow passes the resolved metadata into the reusable workflow.

Any workflow token with `checks: write` can write a check run name and
summary. A workflow on a pull request branch holds such a token. The skip
decision therefore requires the verdict artifact as proof. GitHub runs
`workflow_run` workflows only from the default branch. A pull request branch
cannot produce a qualifying artifact.

The model verdict is advisory to human review. Prompt injection in the title,
body, or diff can steer the model toward `APPROVE`. Never configure
`security-review` as the only required status. Require a human approval in
branch protection as well.

The validator and the merge gate read the same line. That line is the last
line starting with `VERDICT:` at column zero. A malformed final line fails
validation instead of falling back to an earlier verdict.

The review envelope keeps `TRUSTED_HOOK_CONTEXT` separate from
`REVIEW_TARGET`. Trusted context cannot support a finding. Findings require a
location in the review target. Missing or ambiguous provenance requires
`NEEDS-HUMAN`.

The provider receives the system policy and the review envelope. The provider
does not receive the GitHub token, the provider configuration file, or other
repository secrets.

## Adoption in another repository

An adopter repository calls `security-review.yml` as a reusable workflow. The
workflow never executes pull request content. Pin every reference to a full
commit SHA.

### What the adopter supplies

- A caller workflow in the adopter repository.
- The `ci/` adapter directory and `scripts/check_pr_review_response.py` at
  the adopter's base revision. The reusable workflow runs
  `ci/build_pr_case.py`, `ci/run_model_command.py`, `ci/call_model.py`, and
  `scripts/check_pr_review_response.py` from the caller's checkout. Copy them
  from the pinned foucault commit. Keep `ci/model_providers.json` with them.
  A preflight step names any missing script.
- A provider API key as a repository secret, such as `OLLAMA_API_KEY`, for
  same-repository reviews.
- A `fork-review` environment with required reviewers and a `MODEL_API_KEY`
  environment secret for fork reviews.
- An `adopters/<repo>.md` record per `adopters/README.md`.

Only `AUDIT.md` comes from foucault at runtime. The workflow checks it out
into `.foucault` at `audit_ref`.

### Caller workflow

Mirror `security-review-pr.yml`. It resolves the pull request after a trusted
workflow completes, then calls the reusable workflow. The caller grants
`actions: read` beside its review permissions. The skip check reads artifacts
and workflow runs with that permission:

```yaml
jobs:
  security-review:
    uses: abuzucom/foucault/.github/workflows/security-review.yml@<full-commit-sha>
    with:
      audit_ref: "<the same full-commit-sha>"
      model_call_command: "python3 ci/call_model.py"
      pr_comment: true
      fail_on_block: true
      pr_number: ${{ needs.resolve-pr.outputs.pr_number }}
      base_sha: ${{ needs.resolve-pr.outputs.base_sha }}
      head_sha: ${{ needs.resolve-pr.outputs.head_sha }}
      head_repo_url: ${{ needs.resolve-pr.outputs.head_repo_url }}
      head_repo_full_name: ${{ needs.resolve-pr.outputs.head_repo_full_name }}
      fork_review: false
    secrets:
      MODEL_API_KEY: ${{ secrets.OLLAMA_API_KEY }}
```

Add a second reusable workflow call for approved forks. Set `fork_review: true`
on that call. The reusable workflow assigns its fork job to `fork-review`.
Omit the `secrets:` mapping on that call. GitHub waits for a required reviewer
before starting that job. Applying the label does not bypass the successful
`Immutable Compliance` requirement.

The `workflow_run` trigger keeps the caller on default-branch code. A pull
request cannot edit the reviewer. Copy `security-review-pr.yml` and change
nothing else.

A direct `pull_request` trigger also works. The reusable workflow resolves
`context.payload.pull_request` itself. One trade-off applies. A pull request
can edit the caller file in the same repository. Prefer the `workflow_run`
pattern, or require review for workflow changes in branch protection.

### Pins and secrets

- Pin `uses:` and `audit_ref` to the same full commit SHA. Never a tag or
  branch. Record the release version in a comment beside the pin.
- Map only the provider secret. Never use inherited secrets. The job sends an
  untrusted diff to a provider. Inherited secrets hand every repository secret
  to that path.
- The caller maps `MODEL_API_KEY` from a repository secret for same-repository
  reviews. The fork environment stores its own `MODEL_API_KEY` value.
- The fork skip job runs until the maintainer applies `safe-to-review`.

### Verify the wiring

Open a documentation-only pull request in the adopter repository. The review
posts an `APPROVE` comment on the pull request. A missing comment after a few
minutes means the run failed. Find the `security-review-pr` run under the
default branch in the Actions tab. `workflow_run` runs do not appear on the
pull request branch.

## Provider configuration

`ci/model_providers.json` contains the active provider and its reviewed
endpoint, protocol, model, and output limit. The adapter accepts only the four
exact endpoints in the endpoint allowlist. Endpoint aliases and arbitrary URLs do
not pass validation.

The active profile uses Ollama and `kimi-k2.7-code`. The other profiles in
`ci/model_providers.json` serve as adopter-configured templates. Adopters must
supply valid model identifiers and secrets when activating those profiles. The
caller maps the provider-specific repository secret to `MODEL_API_KEY`:

```yaml
secrets:
  MODEL_API_KEY: ${{ secrets.OLLAMA_API_KEY }}
```

Switching providers requires a reviewed configuration change and a trusted
secret mapping change. One provider runs per review. Provider matrices remain
disabled by default.

## Request formats

The adapter uses standard-library HTTP requests. The system policy and review
envelope become JSON values. The adapter never constructs JSON through string
concatenation.

Supported protocols:

- Ollama uses `/api/chat` with Bearer authentication.
- OpenAI-compatible providers use `/v1/chat/completions` with Bearer
  authentication.
- Anthropic uses `/v1/messages` with its native API-key header.
- Google uses `generateContent` with the `x-goog-api-key` header.

Each request disables streaming. Each request uses a bounded output size and
temperature zero. The adapter prints only the response text. It excludes
provider reasoning fields from the workflow report when the API separates
those fields.

## Injection controls

- Review content enters JSON fields only.
- Provider endpoints come from exact reviewed values.
- Provider model names remain JSON values. Gemini model names receive URL
  encoding after profile validation.
- Subprocess calls use argument arrays and `shell=False`.
- Shell metacharacters and interpreter payloads fail validation.
- Git revision values require full hexadecimal commit identifiers.
- Repository URLs require HTTPS and the GitHub host.
- Provider response text remains data. The workflow never executes it.

## Performance controls

The workflow creates one diff and one provider request per event. It does not
call a provider once per file or once per finding. The adapter reads each file
once. It uses dictionary dispatch and set-based endpoint checks.

Response validation compiles patterns once. It scans for the final verdict in
one pass. It parses one complete JSON companion line. Diff capture rejects
output above 3 MB before envelope construction. The adapter retries a transient
request at most once.

The workflow does not silently sample an oversized review. It fails closed and
requires human review when the configured capacity is exceeded.

## Failure behavior

The following conditions fail the job:

- missing API key;
- unknown provider or endpoint;
- invalid provider response;
- provider timeout or exhausted retry;
- missing or malformed `VERDICT` line after one retry;
- missing or mismatched `VERDICT_JSON` block;
- `BLOCK` verdict;
- `NEEDS-HUMAN` verdict when `fail_on_block` is true.

The workflow never converts a provider failure into `APPROVE`.

## Local testing

Set `AUDIT_PROMPT_FILE`, `CASE_TEXT_FILE`, and `MODEL_API_KEY` from a secret
manager or process environment. Do not write the key to a file in the
repository.

Run one adapter request:

```console
python3 ci/call_model.py
```

Run the live corpus:

```console
python3 eval/run_eval.py --model-call ci.call_model:call_model
```

Run the structure-only corpus when no key is available:

```console
python3 eval/run_eval.py
```

Run the local policy and evaluator checks together:

```console
make audit-check PYTHON=python3
```

Pull request CI adds an AUDIT.md policy-diff summary with base size, head size,
and approximate changed-line positions. The metric compares aligned line
positions and length delta. It is not a unified diff line count. Weekly
scheduled validation repeats policy, evaluator, and repository test checks.
