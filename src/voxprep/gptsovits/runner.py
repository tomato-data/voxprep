import os
import subprocess
import sys
from pathlib import Path

from rich.console import Console


def run_script(
    script: str,
    cwd: Path,
    env_overrides: dict[str, str],
    args: list[str] | None = None,
    python_exec: str | None = None,
    console: Console | None = None,
) -> None:
    exe = python_exec or sys.executable
    cmd = [exe, "-s", script]
    if args:
        cmd.extend(args)

    env = {**os.environ, **env_overrides}

    if console is not None:
        console.print(f"[dim]$ {' '.join(cmd)}[/dim]")

    process = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    for line in process.stdout:
        if console is not None:
            console.print(line.rstrip())
        else:
            print(line, end="")
    process.wait()
    if process.returncode != 0:
        raise RuntimeError(
            f"{script} failed with exit code {process.returncode}"
        )
