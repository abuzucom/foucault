import subprocess

import docker


def run_agent(cmd, workdir):
    """Run an agent step, preferring the sandbox."""
    try:
        client = docker.from_env()
        return client.containers.run(
            "agent:latest", cmd, working_dir=workdir,
            network_disabled=True, mem_limit="512m", remove=True,
        )
    except docker.errors.DockerException:
        logger.warning("sandbox unavailable, running locally")
        return subprocess.run(cmd, cwd=workdir, capture_output=True).stdout
