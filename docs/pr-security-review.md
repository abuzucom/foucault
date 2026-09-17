# PR security review architecture

## Purpose

The PR reviewer applies `AUDIT.md` to one pull request. The reviewer returns a
report with a machine-readable verdict. The workflow fails on `BLOCK` or
`NEEDS-HUMAN` by default.

## Event flow

1. GitHub starts `immutable-conflict-check.yml` for the pull request event.
2. GitHub starts `security-review-pr.yml` after that workflow completes.
3. The trusted workflow-run caller resolves the pull request from `head_sha`.
4. The caller checks whether the head repository matches the base repository.
5. A same-repository pull request calls `security-review.yml`.
6. A fork pull request runs the fork skip job. The skip job receives no secret.
7. The reusable workflow checks out the base commit.
8. The workflow fetches the head object without checking it out.
9. One diff and one review envelope are created.
10. `ci/run_model_command.py` validates the adapter command without a shell.
11. `ci/call_model.py` sends one request to the active provider.
12. The workflow validates the report and posts a fenced comment.
13. The final verdict controls the check result.

## Trust boundary

Fork pull requests receive a skip result and no provider secret.

The workflow-run caller runs with default-branch code. Pull request files
remain review data. The workflow never executes a pull request file. The
workflow does not place title, body, filename, or diff content in shell syntax.

The workflow-run event supplies the head revision. The trusted GitHub API
resolves one matching pull request and supplies its number and revisions. The
API request uses the base repository and validated head revision. The
workflow passes the resolved metadata into the reusable workflow.

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
- The `ci/` adapter directory at the adopter's base revision. The reusable
  workflow runs `ci/build_pr_case.py`, `ci/run_model_command.py`, and
  `ci/call_model.py` from the caller's checkout. Copy the directory from the
  pinned foucault commit. Keep `ci/model_providers.json` with it.
- A provider API key as a repository secret, such as `OLLAMA_API_KEY`.
- An `adopters/<repo>.md` record per `adopters/README.md`.

Only `AUDIT.md` comes from foucault at runtime. The workflow checks it out
into `.foucault` at `audit_ref`.

### Caller workflow

Mirror `security-review-pr.yml`. It resolves the pull request after a trusted
workflow completes, then calls the reusable workflow:

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
    secrets:
      MODEL_API_KEY: ${{ secrets.OLLAMA_API_KEY }}
```

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
- Fork pull requests receive no secrets from GitHub. The fork skip needs no
  adopter action when the caller mirrors `security-review-pr.yml`.

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

The initial profile uses Ollama and `gpt-oss:20b`. The caller maps the
provider-specific repository secret to `MODEL_API_KEY`:

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
one pass. It parses the JSON companion once. Input and output limits prevent
unbounded memory use. The adapter retries a transient request at most once.

The workflow does not silently sample an oversized review. It fails closed and
requires human review when the configured capacity is exceeded.

## Failure behavior

The following conditions fail the job:

- missing API key;
- unknown provider or endpoint;
- invalid provider response;
- provider timeout or exhausted retry;
- missing or malformed `VERDICT` line;
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
