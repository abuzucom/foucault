# Adopter: infiniteprep

See `docs/pr-security-review.md` for the architecture and trust boundary this
record assumes.

## Adopted at

`abuzucom/infiniteprep` pins `AUDIT.md` and the reusable
`.github/workflows/security-review.yml` to the same commit,
`fbb09487cdbbe85ca64b2e8c46605c3120b62c54` (release 3.5.0). The wiring
landed in pull request abuzucom/infiniteprep#1 at release 3.4.7. Pull request
abuzucom/infiniteprep#14 advances the pin to release 3.5.0.

## Wiring

- `.github/workflows/security-review-pr.yml` mirrors this repository's
  caller workflow. It triggers on completion of the adopter's `ci` workflow,
  the adopter's `pull_request` workflow. It resolves the pull request from
  the workflow run head and calls `security-review.yml` at the pinned commit.
- `ci/build_pr_case.py`, `ci/run_model_command.py`, `ci/call_model.py`,
  `ci/model_providers.json`, and `scripts/check_pr_review_response.py` are
  verbatim copies from the pinned commit.
- `tests/test_review_wiring.py` checks the pins, the trigger, the secret
  mapping, the fork handling, and the SHA-256 digest of each copied file.
- The active provider profile is Ollama with `kimi-k2.7-code`, mapped from
  the `OLLAMA_API_KEY` repository secret.
- Review input above the `kimi-k2.7-code` budget routes to the
  `ollama-large` profile with `minimax-m3.1-flash`. Both profiles use the
  same `OLLAMA_API_KEY` mapping.
- `fail_on_block: true`. Fork pull requests run only after the
  `safe-to-review` label and `fork-review` environment approval. Unlabeled
  fork pull requests receive an explicit skip result and no provider secret.

## Customization

None. `AUDIT.md` loads unmodified from the pinned commit.

## Local wiring record

The adopter records this adoption in its own `docs/pr-review.md`.
