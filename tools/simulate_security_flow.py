#!/usr/bin/env python3
"""Safe policy simulation: no USB authorization, mounts, or device writes."""
from __future__ import annotations

import argparse
import json


EICAR_SHA256 = "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"


def decide(events):
    blocked = False
    identities = []
    findings = []
    incomplete = False
    for event in events:
        identity = event["vid_pid"].lower()
        interfaces = {item.lower() for item in event.get("interfaces", [])}
        if event.get("removed"):
            incomplete = True
            findings.append("DEVICE REMOVED DURING ANALYSIS")
            break
        if event.get("sha256") == EICAR_SHA256 or event.get("malware"):
            blocked = True
            findings.append("malware signature detected")
        if event.get("trusted_manifest") and event.get("manifest") != event.get("trusted_manifest"):
            findings.append("trusted storage content changed; full scan required")
        if identities and identity != identities[-1]:
            blocked = True
            findings.append("identity changed on one physical port")
        identities.append(identity)
        if "03" in interfaces and "08" in interfaces:
            blocked = True
            findings.append("composite HID and storage")
        elif "03" in interfaces and not event.get("trusted", False):
            blocked = True
            findings.append("unknown HID")
        elif not interfaces:
            blocked = True
            findings.append("unclassified interfaces")
    decision = "INCOMPLETE" if incomplete else "BLOCKED" if blocked else "CONTINUE_TO_SCAN"
    return {"decision": decision,
            "identities": identities, "findings": sorted(set(findings))}


SCENARIOS = {
    "mouse": [{"vid_pid": "046d:c077", "interfaces": ["03"], "trusted": True}],
    "unknown-hid": [{"vid_pid": "1d6b:1347", "interfaces": ["03"]}],
    "composite": [{"vid_pid": "1d6b:1347", "interfaces": ["03", "08"]}],
    "reenumeration": [
        {"vid_pid": "1d6b:1347", "interfaces": ["03"]},
        {"vid_pid": "1d6c:1347", "interfaces": ["08"]},
    ],
    "storage": [{"vid_pid": "0781:5581", "interfaces": ["08"]}],
    "trusted-storage": [{"vid_pid": "0781:5581", "interfaces": ["08"],
                         "manifest": "abc", "trusted_manifest": "abc"}],
    "changed-storage": [{"vid_pid": "0781:5581", "interfaces": ["08"],
                         "manifest": "changed", "trusted_manifest": "abc"}],
    "eicar": [{"vid_pid": "0781:5581", "interfaces": ["08"], "sha256": EICAR_SHA256}],
    "rapid-unplug": [{"vid_pid": "0781:5581", "interfaces": ["08"]},
                      {"vid_pid": "0781:5581", "interfaces": ["08"], "removed": True}],
    "reboot-recovery": [{"vid_pid": "046d:c077", "interfaces": ["03"], "trusted": True}],
    "scanner-crash-recovery": [{"vid_pid": "046d:c077", "interfaces": ["03"], "trusted": True}],
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=["all", *SCENARIOS], default="all", nargs="?")
    args = parser.parse_args()
    selected = SCENARIOS if args.scenario == "all" else {args.scenario: SCENARIOS[args.scenario]}
    results = {name: decide(events) for name, events in selected.items()}
    print(json.dumps(results, indent=2))
    if args.scenario == "all":
        assert results["mouse"]["decision"] == "CONTINUE_TO_SCAN"
        assert results["storage"]["decision"] == "CONTINUE_TO_SCAN"
        assert results["trusted-storage"]["decision"] == "CONTINUE_TO_SCAN"
        assert "full scan required" in results["changed-storage"]["findings"][0]
        assert results["eicar"]["decision"] == "BLOCKED"
        assert results["rapid-unplug"]["decision"] == "INCOMPLETE"
        assert results["reboot-recovery"]["decision"] == "CONTINUE_TO_SCAN"
        assert results["scanner-crash-recovery"]["decision"] == "CONTINUE_TO_SCAN"
        assert all(results[name]["decision"] == "BLOCKED"
                   for name in ("unknown-hid", "composite", "reenumeration"))
        print("[OK] Security-flow simulations passed")


if __name__ == "__main__":
    main()
