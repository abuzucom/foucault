# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest tagged release | Yes |
| `main` (pre-release) | Yes |
| Older tags | No |

## Scope

Scope includes `AUDIT.md` itself. A defect that causes the documented
review workflow to miss a class of vulnerability it claims to cover, or
that lets reviewed content override the reviewer's instructions (prompt
injection), counts as a security issue in this project, not a quality bug.

Scope includes the repository's automation: `eval/`, `scripts/`, `hooks/`,
client hook configurations, `.github/workflows/`, and the tests for each.

Scope includes policy distribution and enforcement. A defect that bypasses a
registered gate, accepts an unsafe client payload, or validates mutable policy
instead of the trusted revision counts as a security issue.

Scope excludes a vulnerability in code that `AUDIT.md` reviews. Report that
to the reviewed project instead.

## PR model review

The PR reviewer sends the pull request title, body, diff, and configured
review context to one allowlisted provider. The provider key stays in a
GitHub secret. The workflow maps that key to `MODEL_API_KEY` and passes it
only to the adapter process.

The trusted caller runs on `pull_request_target`. It uses workflow code from
the base revision. It fetches the pull request head for diff inspection. It
never checks out or executes pull request files. Fork pull requests receive a
skip result and no provider key.

The adapter serializes all provider requests as JSON. It uses argument arrays
for subprocess calls. It rejects shell syntax, unknown providers, unapproved
models, and endpoints outside the exact allowlist. Provider failures and
malformed reports fail closed.

External providers receive review content. Provider selection and endpoint
changes require maintainer review. Use a provider with data handling terms
that permit this repository's review data.

## Reporting a Vulnerability

Report vulnerabilities through GitHub private vulnerability reporting.
Open the Security tab on this repository. Select Report a vulnerability.
Never open a public issue for a vulnerability report.

For a prompt-injection or instruction-override finding against `AUDIT.md`,
include the exact input that triggered it and the mode (PR, File, Piece,
Wholesale) that reproduced it.

## Disclosure Policy

Coordinate disclosure with the maintainers. Keep the report private before
a shipped fix or 90 days from the initial report, whichever comes first.
