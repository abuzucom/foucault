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

Scope includes the repository's automation: `eval/`, `scripts/`,
`hooks/`, `.github/workflows/security-review.yml`, and the tests for each.

Scope excludes a vulnerability in code that `AUDIT.md` reviews. Report that
to the reviewed project instead.

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
