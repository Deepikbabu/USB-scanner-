"""Signed device trust, fingerprints, incremental manifests, and NVD enrichment."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = Path(os.environ.get("USB_SCANNER_STATE_DIR", "/var/lib/usb-scanner"))
FALLBACK_STATE_DIR = ROOT / ".scanner_state"
CPE_MAP_PATH = ROOT / "config" / "device_cpe_map.json"


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def hardware_fingerprint(info: dict[str, Any], interfaces: set[str] | list[str]) -> str:
    evidence = {
        "vid": str(info.get("vid", "unknown")).lower(),
        "pid": str(info.get("pid", "unknown")).lower(),
        "serial": str(info.get("serial", "Unknown")),
        "interfaces": sorted(interfaces),
        "usbguard_hash": str(info.get("usbguard_hash", "")),
    }
    return canonical_hash(evidence)


def interface_fingerprint(interfaces: set[str] | list[str]) -> str:
    return canonical_hash(sorted(interfaces))


def device_identity_fingerprint(info: dict[str, Any], interfaces: set[str] | list[str]) -> str:
    """Build a composite identity independent of a transient USB port."""
    return canonical_hash({
        "vid": str(info.get("vid", "unknown")).lower(),
        "pid": str(info.get("pid", "unknown")).lower(),
        "serial": str(info.get("serial", "Unknown")),
        "usbguard_hash": str(info.get("usbguard_hash", "")),
        "interfaces": sorted(interfaces),
    })


def identity_quality(info: dict[str, Any], interfaces: set[str] | list[str]) -> str:
    """Classify how strongly a device can be distinguished from duplicates."""
    serial = str(info.get("serial", "")).strip().lower()
    has_serial = serial not in {"", "unknown", "unavailable", "none"}
    has_descriptor = bool(str(info.get("usbguard_hash", "")).strip())
    has_interfaces = bool(list(interfaces))
    if has_serial and has_descriptor and has_interfaces:
        return "STRONG"
    if has_descriptor and has_interfaces:
        return "MEDIUM"
    return "WEAK"


def manifest_fingerprint(files: list[dict[str, Any]]) -> str:
    stable = [{"relative_path": item["relative_path"], "size": item.get("size", 0),
               "sha256": item.get("sha256")} for item in files]
    return canonical_hash(sorted(stable, key=lambda item: item["relative_path"]))


class SignedTrustStore:
    SCHEMA_VERSION = 2

    def __init__(self) -> None:
        try:
            STATE_DIR.mkdir(parents=True, mode=0o700, exist_ok=True)
            self.directory = STATE_DIR
        except OSError:
            FALLBACK_STATE_DIR.mkdir(parents=True, mode=0o700, exist_ok=True)
            self.directory = FALLBACK_STATE_DIR
        self.key_path = self.directory / "trust.key"
        self.records_path = self.directory / "trust_records.json"
        if not self.key_path.exists():
            self.key_path.write_bytes(os.urandom(32))
            self.key_path.chmod(0o600)

    def _sign(self, record: dict[str, Any]) -> str:
        body = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str).encode()
        return hmac.new(self.key_path.read_bytes(), body, hashlib.sha256).hexdigest()

    def _load_all(self) -> dict[str, dict[str, Any]]:
        try:
            value = json.loads(self.records_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def get(self, identity: str) -> tuple[dict[str, Any] | None, str]:
        wrapped = self._load_all().get(identity)
        if not wrapped:
            return None, "not_enrolled"
        record, signature = wrapped.get("record"), wrapped.get("signature")
        if not isinstance(record, dict) or not hmac.compare_digest(str(signature), self._sign(record)):
            return None, "invalid_signature"
        expires_at = record.get("expires_at")
        try:
            if expires_at is not None and float(expires_at) <= time.time():
                return None, "expired"
        except (TypeError, ValueError):
            return None, "invalid_expiration"
        return record, "verified"

    def put(self, identity: str, record: dict[str, Any]) -> None:
        records = self._load_all()
        if self.records_path.exists():
            self.backup()
        record = dict(record)
        record.setdefault("schema_version", self.SCHEMA_VERSION)
        records[identity] = {"record": record, "signature": self._sign(record)}
        temporary = self.records_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(records, indent=2, default=str) + "\n", encoding="utf-8")
        temporary.replace(self.records_path)
        self.records_path.chmod(0o600)

    def backup(self) -> Path | None:
        """Create a recoverable trust-record backup before migration/write."""
        if not self.records_path.exists():
            return None

    def rollback(self) -> bool:
        """Restore the last trust-record backup atomically."""
        backup = self.records_path.with_name("trust_records.json.bak")
        if not backup.exists():
            return False
        try:
            self.records_path.replace(self.records_path.with_suffix(".pre-rollback"))
            backup.replace(self.records_path)
            self.records_path.chmod(0o600)
            return True
        except OSError:
            return False
        target = self.records_path.with_name("trust_records.json.bak")
        try:
            target.write_bytes(self.records_path.read_bytes())
            target.chmod(0o600)
            return target
        except OSError:
            return None

    def migrate_legacy(self) -> int:
        """Upgrade unsigned-schema metadata while preserving signatures."""
        records = self._load_all()
        changed = 0
        for wrapped in records.values():
            record = wrapped.get("record") if isinstance(wrapped, dict) else None
            if isinstance(record, dict) and "schema_version" not in record:
                record["schema_version"] = self.SCHEMA_VERSION
                wrapped["signature"] = self._sign(record)
                changed += 1
        if changed:
            self.backup()
            temporary = self.records_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(records, indent=2, default=str) + "\n", encoding="utf-8")
            temporary.replace(self.records_path)
            self.records_path.chmod(0o600)
        return changed

    def remove(self, identity: str) -> None:
        records = self._load_all()
        records.pop(identity, None)
        self.records_path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")


@dataclass
class NVDResult:
    status: str = "not_evaluated"
    cpe: str | None = None
    confidence: str = "none"
    checked_at: float | None = None
    cves: list[dict[str, Any]] | None = None
    highest_cvss: float = 0.0
    kev: bool = False
    risk: int = 0
    message: str = "No verified CPE mapping"

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["cves"] = self.cves or []
        return result


class NVDClient:
    CVE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"

    def __init__(self) -> None:
        self.state = SignedTrustStore().directory
        self.cache_path = self.state / "nvd_cache.db"
        self.api_key = self._load_api_key()
        with sqlite3.connect(self.cache_path) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, created REAL, payload TEXT)")

    @staticmethod
    def _load_api_key() -> str | None:
        if os.environ.get("NVD_API_KEY"):
            return os.environ["NVD_API_KEY"].strip()
        path = Path("/etc/usb-scanner/nvd.env")
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("NVD_API_KEY="):
                    return line.split("=", 1)[1].strip()
        except OSError:
            pass
        return None

    def _mapping(self, vid_pid: str) -> dict[str, Any] | None:
        try:
            mapping = json.loads(CPE_MAP_PATH.read_text(encoding="utf-8"))
            value = mapping.get(vid_pid.lower())
            return value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def lookup(self, vid_pid: str, timeout: int = 8) -> NVDResult:
        mapping = self._mapping(vid_pid)
        if not mapping or not mapping.get("cpe") or mapping.get("confidence") not in {"verified", "high"}:
            return NVDResult(message="No verified/high-confidence CPE mapping; NVD did not affect risk")
        cpe, confidence = mapping["cpe"], mapping["confidence"]
        cache_key = canonical_hash({"cpe": cpe})
        with sqlite3.connect(self.cache_path) as connection:
            row = connection.execute("SELECT created, payload FROM cache WHERE key=?", (cache_key,)).fetchone()
        if row and time.time() - row[0] < 86400:
            payload = json.loads(row[1])
            payload["status"] = "cached"
            return NVDResult(**payload)
        request = urllib.request.Request(self.CVE_URL + "?" + urllib.parse.urlencode({
            "cpeName": cpe, "isVulnerable": "", "resultsPerPage": 100,
        }), headers={"User-Agent": "usb-scanner/1.0", **({"apiKey": self.api_key} if self.api_key else {})})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = json.load(response)
            cves = [self._parse_cve(item.get("cve", {})) for item in raw.get("vulnerabilities", [])]
            highest = max((item["cvss"] for item in cves), default=0.0)
            kev = any(item["kev"] for item in cves)
            risk = min(20, self._cvss_risk(highest) + (5 if kev else 0))
            result = NVDResult("fresh", cpe, confidence, time.time(), cves, highest, kev, risk,
                               f"{len(cves)} applicable CVE(s) returned")
            cached = result.to_dict(); cached["status"] = "fresh"
            with sqlite3.connect(self.cache_path) as connection:
                connection.execute("REPLACE INTO cache VALUES (?, ?, ?)",
                                   (cache_key, time.time(), json.dumps(cached)))
            return result
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            if row:
                payload = json.loads(row[1]); payload["status"] = "stale_cache"
                payload["message"] = f"NVD unavailable; stale cache used: {exc}"
                return NVDResult(**payload)
            return NVDResult(status="unavailable", cpe=cpe, confidence=confidence,
                             message=f"NVD unavailable and no cache exists: {exc}")

    @staticmethod
    def _cvss_risk(score: float) -> int:
        if score >= 9: return 10
        if score >= 7: return 7
        if score >= 4: return 3
        if score > 0: return 1
        return 0

    @staticmethod
    def _parse_cve(cve: dict[str, Any]) -> dict[str, Any]:
        descriptions = cve.get("descriptions", [])
        description = next((item.get("value", "") for item in descriptions if item.get("lang") == "en"), "")
        metrics = cve.get("metrics", {})
        metric = next(iter(metrics.get("cvssMetricV31", []) or metrics.get("cvssMetricV30", []) or
                           metrics.get("cvssMetricV2", [])), {})
        data = metric.get("cvssData", {})
        return {"id": cve.get("id"), "cvss": float(data.get("baseScore", 0) or 0),
                "severity": data.get("baseSeverity") or metric.get("baseSeverity") or "UNKNOWN",
                "description": description[:500], "kev": bool(cve.get("cisaExploitAdd")),
                "recommendation": "Apply vendor firmware updates or isolate the device"}


def risk_breakdown(hardware=0, trust=0, interface=0, behavior=0, storage=0, nvd=0,
                   malware=0) -> dict[str, Any]:
    values = {"hardware": min(15, hardware), "trust": min(20, trust),
              "interface": min(30, interface), "behavior": min(15, behavior),
              "storage": min(30, storage), "nvd": min(20, nvd),
              "malware": min(70, malware)}
    values["total"] = min(100, sum(values.values()))
    total = values["total"]
    values["severity"] = "CRITICAL" if total >= 70 else "HIGH" if total >= 40 else "MEDIUM" if total >= 20 else "REVIEW" if total >= 5 else "LOW"
    return values


def incident_verdict(allowed=False, trusted=False, incomplete=False,
                     malware=False, total_risk=0, remediated=False) -> str:
    """Return the historical incident verdict; containment never erases malware."""
    if incomplete:
        return "INCOMPLETE"
    if malware or total_risk >= 40:
        return "DANGEROUS"
    if remediated or not allowed:
        return "SUSPICIOUS"
    if trusted:
        return "TRUSTED"
    return "CLEAN"
