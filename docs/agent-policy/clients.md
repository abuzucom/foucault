# Client lifecycle

Re-adopt the complete canonical policy at session startup, resume, clear,
compaction, fork, and subagent startup.

Inject complete policy context before every Gemini and Antigravity model
request. Keep client output within the client limit.

Claude loads `CLAUDE.md` natively. Built-in Explore and Plan agents skip that
file. Preserve both agents. Inject numbered chunks through `SubagentStart`.

Codex loads `AGENTS.md` natively. Set `project_doc_max_bytes` above the
canonical limit. Set `additionalContextLimit` to zero when supported.

Gemini uses `SessionStart` and `BeforeModel`. Gemini project hooks require
fingerprint trust and permit disablement.

Antigravity uses an ephemeral `PreInvocation` message. Its `PreToolUse`
payload must remain schema-safe. Do not emit unsupported `injectSteps` fields
from `PreToolUse`.

Client APIs differ. Do not claim coverage that the client cannot observe.
Repository hooks remain defense in depth only.

`AGENTS.md` controls when linked documents conflict with it.
