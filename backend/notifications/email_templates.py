from __future__ import annotations

import json
from pathlib import Path


def incident_message(incident_id: str, verdict: str, json_report: str | None) -> tuple[str, str]:
    payload = {}
    if json_report:
        try:
            payload = json.loads(Path(json_report).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    device = payload.get("device", {})
    report_incident = payload.get("device", {}).get("incident_id") or payload.get("incident_id")
    if report_incident and str(report_incident) != str(incident_id):
        raise ValueError("incident ID does not match finalized JSON report")
    report_verdict = str(payload.get("verdict", verdict)).upper()
    if report_verdict not in {"CLEAN", "TRUSTED", "SUSPICIOUS", "DANGEROUS", "INCOMPLETE"}:
        report_verdict = "INCOMPLETE"
    verdict = report_verdict
    risk = payload.get("risk_breakdown", {})
    findings = payload.get("flags") or payload.get("findings") or []
    subject_prefix = "CRITICAL" if verdict == "DANGEROUS" else "INFO" if verdict in {"CLEAN", "TRUSTED"} else "WARNING"
    subject = f"{subject_prefix}: USB incident {incident_id} - {verdict}"
    lines = [
        "USB Security Engine incident notification", "",
        f"Incident ID : {incident_id}", f"Verdict     : {verdict}",
        f"Device      : {device.get('vendor', 'Unknown')} {device.get('model', 'USB Device')}",
        f"VID:PID     : {device.get('vid', '?')}:{device.get('pid', '?')}",
        f"Serial      : {device.get('serial', 'Unknown')}",
        f"Port        : {device.get('physical_port', 'unknown')}",
        f"Risk        : {risk.get('total', payload.get('total_risk', 'unknown'))}", "",
        "Findings:",
    ]
    lines.extend(f"- {item}" for item in findings[:50])
    lines.extend(("", "The PDF and JSON evidence are attached when available.",
                  "Suspicious files are never attached."))
    return subject, "\n".join(lines)
