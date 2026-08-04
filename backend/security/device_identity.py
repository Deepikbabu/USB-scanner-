"""Canonical, exact USB identity construction."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable

UNKNOWN_SERIALS = {"", "unknown", "unavailable", "none", "0", "00000000"}


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def canonical_descriptors(info: dict[str, Any]) -> dict[str, Any]:
    endpoints = info.get("endpoints") or []
    configurations = info.get("configurations") or []
    interfaces = info.get("interfaces") or info.get("guard_interfaces") or []
    return {
        "vid": _text(info.get("vid")).lower().zfill(4),
        "pid": _text(info.get("pid")).lower().zfill(4),
        "bcd_device": _text(info.get("bcd_device") or info.get("firmware_version")),
        "usb_version": _text(info.get("usb_version")),
        "manufacturer": _text(info.get("manufacturer") or info.get("vendor")).casefold(),
        "model": _text(info.get("model") or info.get("product")).casefold(),
        "serial": _text(info.get("serial")),
        "configurations": sorted(map(str, configurations)),
        "interfaces": sorted(map(str, interfaces)),
        "endpoints": sorted(map(str, endpoints)),
        "capacity_bytes": int(info.get("capacity_bytes") or 0),
        "partition_table_fingerprint": _text(info.get("partition_table_fingerprint")),
        "filesystem_uuid": _text(info.get("filesystem_uuid")),
        "usbguard_hash": _text(info.get("usbguard_hash")),
    }


def serial_quality(serial: Any) -> dict[str, Any]:
    value = _text(serial)
    normalized = value.casefold()
    reasons = []
    score = 100
    if normalized in UNKNOWN_SERIALS: score, reasons = 0, ["missing"]
    else:
        if len(value) < 6: score -= 40; reasons.append("short")
        if len(set(value)) <= 2: score -= 35; reasons.append("low_variation")
        if re.fullmatch(r"0+|f+", normalized): score = 0; reasons.append("placeholder")
    return {"value": value, "score": max(0, score),
            "quality": "strong" if score >= 80 else "medium" if score >= 40 else "weak",
            "reasons": reasons}


def exact_identity(info: dict[str, Any]) -> dict[str, Any]:
    descriptors = canonical_descriptors(info)
    topology = {"physical_port": _text(info.get("physical_port") or info.get("port")),
                "bus": _text(info.get("busnum") or info.get("bus")),
                "device_path": _text(info.get("device_path"))}
    stable = dict(descriptors)
    # Location is recorded and evaluated but excluded from portable identity.
    payload = json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()
    return {"identity": hashlib.sha256(payload).hexdigest(), "descriptors": descriptors,
            "descriptor_fingerprint": hashlib.sha256(payload).hexdigest(),
            "interface_fingerprint": _hash(descriptors["interfaces"]),
            "endpoint_fingerprint": _hash(descriptors["endpoints"]),
            "configuration_fingerprint": _hash(descriptors["configurations"]),
            "serial_quality": serial_quality(descriptors["serial"]), "topology": topology}


def _hash(value: Iterable[Any]) -> str:
    return hashlib.sha256(json.dumps(list(value), sort_keys=True).encode()).hexdigest()


def manufacturer_model_consistency(current: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
    current_pair = (_text(current.get("manufacturer") or current.get("vendor")).casefold(),
                    _text(current.get("model") or current.get("product")).casefold())
    previous = {(str(item.get("manufacturer", "")).casefold(), str(item.get("model", "")).casefold())
                for item in history}
    return {"consistent": not previous or current_pair in previous,
            "current": current_pair, "previous": sorted(previous)}
