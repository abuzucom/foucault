def run_scan(repo):
    findings = model.complete(SCAN_PROMPT + read_repo(repo))
    summary = model.complete("Summarize these findings:\n" + findings)
    memory.put(repo.id, summary)
    return summary


def next_run(repo):
    """Later runs trust the previous summary as established context."""
    prior = memory.get(repo.id)
    prompt = TRIAGE_PROMPT + "\nKnown-good baseline: " + prior
    return model.complete(prompt)
