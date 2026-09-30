# Adopter: 1a2n-web-visualizer

See `docs/pr-security-review.md` for the architecture and trust boundary this
record assumes.

## Adopted at

`abuzucom/1a2n-web-visualizer` pins `AUDIT.md` and the reusable
`.github/workflows/security-review.yml` to the same commit,
`06d74fba4d9013654cdaf9896bb7535724385186` (release 3.3.14). The wiring
lands in draft pull request abuzucom/1a2n-web-visualizer#149.

## Wiring

- `.github/workflows/security-review-pr.yml` mirrors this repository's
  caller workflow. It triggers on completion of the adopter's `Checks`
  workflow, the adopter's `pull_request` workflow. It resolves the pull
  request from the workflow run head and calls `security-review.yml` at the
  pinned commit.
- `ci/build_pr_case.py`, `ci/run_model_command.py`, `ci/call_model.py`, and
  `ci/model_providers.json` are verbatim copies from the pinned commit.
- `scripts/check_pr_review_response.py` arrives with the adopter's
  `abuzucom/agents` template `scripts/` set. It matches the pinned commit
  byte for byte.
- `tests/test_foucault_review_wiring.py` checks the pins, the trigger, the
  secret mapping, the fork skip, and the SHA-256 digest of each copied file.
- The active provider profile is Ollama with `kimi-k2.7-code`, mapped from
  the `OLLAMA_API_KEY` repository secret.
- `fail_on_block: true`. Fork pull requests receive an explicit skip result
  and no provider secret.

## Customization

None. `AUDIT.md` loads unmodified from the pinned commit.

## Local wiring record

The adopter records this adoption in its own `docs/pr-security-review.md`.
