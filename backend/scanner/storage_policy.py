"""Storage isolation policy primitives for Linux removable media."""
from __future__ import annotations

import subprocess
from pathlib import Path


REQUIRED_OPTIONS = frozenset({"ro", "nosuid", "nodev", "noexec"})


def verify_mount_options(mount_path: str | Path) -> bool:
    """Return true only when the kernel reports all isolation options."""
    try:
        result = subprocess.run(
            ["findmnt", "-n", "-o", "OPTIONS", "--target", str(mount_path)],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return False
        options = {item.strip().lower() for item in result.stdout.strip().split(",")}
        return REQUIRED_OPTIONS.issubset(options)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def mount_read_only(device_node: str, mount_path: str, timeout: float = 20.0) -> bool:
    """Mount a device with the required isolation flags and verify them."""
    try:
        Path(mount_path).mkdir(parents=True, mode=0o700, exist_ok=True)
        result = subprocess.run(
            ["mount", "-o", "ro,nosuid,nodev,noexec", device_node, mount_path],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode == 0 and verify_mount_options(mount_path):
            return True
        subprocess.run(["umount", mount_path], capture_output=True, timeout=10)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False
    return False


def unmount(mount_path: str, timeout: float = 15.0) -> bool:
    try:
        result = subprocess.run(["umount", mount_path], capture_output=True,
                                text=True, timeout=timeout)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False
