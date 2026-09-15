# PR security review architecture

## Purpose

The PR reviewer applies `AUDIT.md` to one pull request. The reviewer returns a
report with a machine-readable verdict. The workflow fails on `BLOCK` or
`NEEDS-HUMAN` by default.

## Event flow

1. GitHub starts `security-review-pr.yml` for a pull request event.
2. The trusted base workflow checks whether the head repository matches the
   base repository.
3. A same-repository pull request calls `security-review.yml`.
4. A fork pull request runs the fork skip job. The skip job receives no secret.
5. The reusable workflow checks out the base commit.
6. The workflow fetches the head object without checking it out.
7. One diff and one review envelope are created.
8. `ci/run_model_command.py` validates the adapter command without a shell.
9. `ci/call_model.py` sends one request to the active provider.
10. The workflow validates the report and posts a fenced comment.
11. The final verdict controls the check result.

## Trust boundary

Fork pull requests receive a skip result and no provider secret.

The caller workflow runs with base-branch code. Pull request files remain
review data. The workflow never executes a pull request file. The workflow
does not place title, body, filename, or diff content in shell syntax.

The review envelope keeps `TRUSTED_HOOK_CONTEXT` separate from
`REVIEW_TARGET`. Trusted context cannot support a finding. Findings require a
location in the review target. Missing or ambiguous provenance requires
`NEEDS-HUMAN`.

The provider receives the system policy and the review envelope. The provider
does not receive the GitHub token, the provider configuration file, or other
repository secrets.

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
