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

## No build step

This repository has no application code and no build. Everything runs with
the standard library:

```console
python eval/run_eval.py
python scripts/check_hedging.py AGENTS.md README.md
python -m unittest discover -s tests -v
```

## Pull requests

Open every pull request as a draft. Never push to `main`. State what
changed. For an `AUDIT.md` change, name the `eval/cases/` entries that
cover it.
