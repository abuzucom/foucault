# Adopter: agents

See `docs/pr-security-review.md` for the architecture and trust boundary this
record assumes.

## Adopted at

`abuzucom/agents` pins `AUDIT.md` and the reusable
`.github/workflows/security-review.yml` to the same commit,
`551a8000a33ba1955d5e9ed79c9f08daacc4ae99` (release 3.3.8).

## Wiring

- `.github/workflows/security-review-pr.yml` mirrors this repository's own
  caller workflow. It triggers on completion of `abuzucom/agents`'s existing
  `Immutable Compliance` workflow, resolves the pull request from the
  workflow run head, and calls `security-review.yml` at the pinned commit.
- `ci/build_pr_case.py`, `ci/run_model_command.py`, `ci/call_model.py`, and
  `ci/model_providers.json` are copied verbatim from the pinned commit.
- The active provider profile is Ollama with `kimi-k2.7-code`, mapped from
  the `OLLAMA_API_KEY` repository secret.
- `fail_on_block: true`. Fork pull requests receive an explicit skip result
  and no provider secret.

## Customization

None. `AUDIT.md` is loaded unmodified from the pinned commit.

## Local wiring record

`abuzucom/agents` records this adoption in its own
`docs/pr-security-review.md`.
