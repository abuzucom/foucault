# Adopter: xdj-rx3-emu

See `docs/pr-security-review.md` for the architecture and trust boundary this
record assumes.

## Adopted at

`abuzucom/xdj-rx3-emu` pins `AUDIT.md` and the reusable
`.github/workflows/security-review.yml` to the same commit,
`62851df1ef177593adbb9e06b223f5a6dce66fc0` (release 3.3.10). The pin
arrives with the adopter's `abuzucom/agents` template at commit `fd9da22`.

## Wiring

- `.github/workflows/security-review-pr.yml` is the `abuzucom/agents` copy of
  this repository's caller. It triggers on completion of the adopter's
  `Immutable Compliance` workflow and calls `security-review.yml` at the
  pinned commit.
- `ci/build_pr_case.py`, `ci/run_model_command.py`, `ci/call_model.py`, and
  `ci/model_providers.json` match the pinned commit byte for byte.
- `scripts/check_pr_review_response.py` arrives with the adopter's
  `abuzucom/agents` template `scripts/` set.
- `tests/test_security_review_wiring.py`, from `abuzucom/agents`, checks the
  pin, the trigger, the secret mapping, the fork skip, and the adapter files.
- The active provider profile is Ollama with `kimi-k2.7-code`, mapped from
  the `OLLAMA_API_KEY` repository secret.
- `fail_on_block: true`. Fork pull requests receive an explicit skip result
  and no provider secret.

## Customization

None. `AUDIT.md` loads unmodified from the pinned commit.

## Local wiring record

The adopter records this adoption in its own `docs/pr-security-review.md`.
