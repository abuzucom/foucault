# Adopters

Records of repositories that load `AUDIT.md` as an audit agent's system
prompt, or wire the reference `.github/workflows/security-review.yml`.
Mirrors the `adopters/<repo>.md` convention from `abuzucom/agents`.
See `docs/pr-security-review.md` for the wiring steps.

## Recording an adoption

Add `adopters/<repo>.md` with:

- The pinned tag or commit SHA of `AUDIT.md` in use.
- Any customization made per the README's Customization section
  (stack-specific additions, scope boundaries, a waiver mechanism).
- Whether the repository wires `.github/workflows/security-review.yml`,
  and at what pinned commit SHA.

## Current adopters

- [`agents`](agents.md)
- [`1a2n-web-visualizer`](1a2n-web-visualizer.md)
- [`xdj-rx3-emu`](xdj-rx3-emu.md)
