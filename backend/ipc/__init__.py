"""Local dashboard IPC for the root security service."""

from .server import get_ipc_server, publish_event

__all__ = ["get_ipc_server", "publish_event"]
