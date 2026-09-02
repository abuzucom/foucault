import subprocess


def analyze(clone_url, workdir):
    """Clone a user-submitted repository and collect its history."""
    subprocess.run(["git", "clone", clone_url, workdir], check=True)
    log = subprocess.run(
        ["git", "-C", workdir, "log", "--stat"],
        capture_output=True, check=True,
    )
    subprocess.run(["git", "-C", workdir, "gc"], check=True)
    return log.stdout
