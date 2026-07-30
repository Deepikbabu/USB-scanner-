"""Shared build and IPC compatibility metadata."""

from __future__ import annotations

from pathlib import Path

APP_VERSION = "2.0.0"
BUILD_ID = "sentinel-production-2026.07"
IPC_PROTOCOL_VERSION = 1
API_SCHEMA_VERSION = 2


def runtime_identity() -> dict[str, object]:
    """Return identity data used to detect stale/mismatched deployments."""
    project_root = Path(__file__).resolve().parents[1]
    return {
        "app_version": APP_VERSION,
        "build_id": BUILD_ID,
        "protocol_version": IPC_PROTOCOL_VERSION,
        "api_schema_version": API_SCHEMA_VERSION,
        "project_root": str(project_root),
    }
