"""Bubblewrap launcher for hostile-file parsing workers."""
from __future__ import annotations

import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
from typing import Sequence

class SandboxUnavailable(RuntimeError):
    pass

def command(worker: Sequence[str], scan_root: str, app_root: str) -> list[str]:
    bwrap = shutil.which("bwrap")
    if not bwrap:
        raise SandboxUnavailable("bubblewrap is required; refusing unsandboxed scanning")
    root = Path(scan_root).resolve()
    app = Path(app_root).resolve()
    return [bwrap, "--die-with-parent", "--unshare-all", "--unshare-net",
            "--new-session", "--clearenv", "--ro-bind", "/usr", "/usr",
            "--ro-bind", "/bin", "/bin", "--ro-bind", "/lib", "/lib",
            "--ro-bind", str(app), "/app", "--ro-bind", str(root), "/input",
            "--tmpfs", "/tmp", "--proc", "/proc", "--dev", "/dev",
            "--chdir", "/input", "--setenv", "SCAN_ROOT", "/input", "--"] + list(worker)

def run(worker: Sequence[str], scan_root: str, app_root: str, timeout: float = 300,
        memory_bytes: int = 1024 * 1024 * 1024) -> subprocess.CompletedProcess[str]:
    args = command(worker, scan_root, app_root)
    def limits() -> None:
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
        resource.setrlimit(resource.RLIMIT_CPU, (max(1, int(timeout)), max(1, int(timeout))))
        resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
    try:
        return subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, timeout=timeout, preexec_fn=limits)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SandboxUnavailable(f"sandboxed worker failed: {exc}") from exc

def run_python_worker(scan_root: str, app_root: str, database_path: str,
                      timeout: float = 300) -> subprocess.CompletedProcess[str]:
    env_worker = [sys.executable, "-m", "backend.scanner.worker"]
    args = command(env_worker, scan_root, app_root)
    # The worker receives only a logical /input path; the host mount path is
    # never exposed in its protocol.
    marker = args.index("--setenv")
    args[marker:marker] = ["--setenv", "USB_SCANNER_WORKER_SANDBOXED", "1"]
    env = {"PYTHONPATH": "/app"}
    try:
        return subprocess.run(args, input=(__import__('json').dumps({
            "mount_path": "/input", "database_path": database_path}) + "\n"),
            capture_output=True, text=True, timeout=timeout, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SandboxUnavailable(f"sandboxed worker failed: {exc}") from exc
