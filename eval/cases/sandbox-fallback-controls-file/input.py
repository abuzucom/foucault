def run_task(task, sandbox):
    if sandbox.start():
        return sandbox.run(task)
    return run_without_sandbox(task)
