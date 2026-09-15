# Contributing

## Ground rules

Follow `AGENTS.md`. It governs branch naming, git identity, style, and
scope for every change to this repository, human or agent-authored.

## Changing AUDIT.md

Any change to `AUDIT.md` that affects a verdict, a hard blocker (section
5), or a severity mapping (section 1.7) needs a new or updated
`eval/cases/` entry demonstrating the change is still caught correctly
(`AGENTS.md` non-negotiable rule 3). Run `python eval/run_eval.py` to
confirm the case set stays structurally sound; run it with `--model-call`
against a real model when a credential is available.

Assess every incoming checklist against what `AUDIT.md` already says. Add
nothing an existing rule already covers. Each item has one of three
outcomes. An item already covered needs no change. An item covered in
principle by a rule too vague to fire needs that rule extended in place. An
item introducing a genuinely new sink, scenario, or fix needs a new rule.
Extend by default. A parallel rule naming a sink an existing rule already
names is a defect.

Keep `AUDIT.md` terse and imperative. Do not add a rule without a stated
exploit scenario. Keep the document under its 32768-character ceiling.
Split reference material out before exceeding it.

## Validation

This repository has no application build. Install the pinned checker
dependency before running validation:

```console
python -m pip install --requirement requirements-checkers.txt
python eval/run_eval.py
python scripts/sync.py --check
python scripts/sync.py --check-shared
python scripts/check_gate_adoption.py
python scripts/run_tests.py
```

Run the complete policy, workflow, security, and hook checks before opening a
pull request. Do not claim live-model coverage without a configured adapter.

## Pull requests

Open every pull request as a draft. Never push to `main`. State what
changed. For an `AUDIT.md` change, name the `eval/cases/` entries that
cover it.

Run hosted GitHub commands through `scripts/trusted_gh.py`:
`python scripts/trusted_gh.py run <gh arguments>`. Verify branch and remote
state before reporting a push. Read the pull request back before reporting
its number or draft status.

## PR security review

Same-repository pull requests run `security-review-pr.yml`. The workflow uses
the base branch workflow and never executes pull request files. Fork pull
requests receive a skip result because no provider secret crosses that trust
boundary.

Provider changes require an update to `ci/model_providers.json`, the endpoint
allowlist, adapter tests, and the provider documentation. Keep API keys in
repository or organization secrets. Map the active provider key to
`MODEL_API_KEY` in the trusted caller workflow.

Run the adapter locally with `AUDIT_PROMPT_FILE`, `CASE_TEXT_FILE`, and
`MODEL_API_KEY` set outside the repository. Run `python3 ci/call_model.py` for
one request. Run `python3 eval/run_eval.py --model-call ci.call_model:call_model`
for the live corpus. Never place review content in a command string.
