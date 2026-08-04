# USB Scanner Architecture

## 1. System boundary

```text
                         USER SPACE
┌─────────────────────────────────────────────────────────┐
│ Sentinel Dashboard (PyQt6, non-privileged)              │
│ Overview · Live Scan · History · Quarantine · Settings  │
└──────────────────────────┬──────────────────────────────┘
                           │ Unix socket: newline JSON
                           │ authenticated requests/events
                         TRUST BOUNDARY
                           │
                         ROOT SPACE
┌──────────────────────────▼──────────────────────────────┐
│ Scanner Controller                                      │
│ udev/USBGuard · lifecycle · policy · decisions          │
└───────────────┬──────────────────┬──────────────────────┘
                │                  │
       ┌────────▼────────┐ ┌───────▼────────────────────┐
       │ HID Controller   │ │ Restricted Scan Worker     │
       │ block/allow      │ │ parse files, run engines  │
       │ sysfs/USBGuard   │ │ low privileges/sandbox    │
       └──────────────────┘ └──────────┬─────────────────┘
                                      │
                 ┌────────────────────┼───────────────────┐
                 │                    │                   │
          ┌──────▼──────┐     ┌───────▼──────┐    ┌───────▼──────┐
          │ Hash/Static │     │ YARA/ClamAV  │    │ MIME/PE/ELF  │
          │ analysis    │     │ engines      │    │ PDF/Office    │
          └─────────────┘     └──────────────┘    └──────────────┘
                                      │
                         ┌────────────▼─────────────┐
                         │ Verdict & Remediation    │
                         │ risk · quarantine · block│
                         └────────────┬─────────────┘
                                      │
              ┌───────────────────────▼──────────────────────┐
              │ SQLite · Evidence · Audit · Notifications   │
              └──────────────────────────────────────────────┘
```

## 2. Runtime phases

### Phase 1 — Installation and startup

`run.sh` installs dependencies, initializes ClamAV/YARA/USBGuard, prepares state, checks the host and starts the service.

### Phase 2 — Baseline and recovery

The service captures existing working HID devices and restores only verified devices after restart. Trust keys and exact device identities are stored in protected state.

### Phase 3 — Device discovery

udev reports a USB event. The controller collects VID/PID, descriptors, serial, interfaces, endpoints, topology, capacity, filesystem UUID and firmware information.

### Phase 4 — Exact identity calculation

Descriptors are canonicalized. Configuration, interface, endpoint, serial, storage and firmware evidence are combined into an exact fingerprint. Identity history is checked for changes or cloning.

### Phase 5 — Initial isolation

USBGuard keeps new or changed devices blocked before normal driver access. A physical-port session and incident ID are created.

### Phase 6 — Device classification

The controller classifies the device as HID, storage, composite, MTP/PTP or unsupported.

### Phase 7A — HID workflow

Signed exact trust is checked. Unknown, changed, composite-dangerous or suspicious HID devices remain blocked. Approved HID devices can be authorized only after policy validation.

### Phase 7B — Storage workflow

The device is mounted in an isolated read-only environment with `nosuid`, `nodev` and `noexec`. A restricted scanner worker receives only the isolated mount.

### Phase 8 — File analysis

Each file is bounded and analyzed using:

1. Content-based MIME detection.
2. SHA-256 malware lookup.
3. PE/ELF identification and signature checks.
4. Office macro and document analysis.
5. PDF JavaScript and embedded-object checks.
6. Archive traversal and expansion checks.
7. Heuristic/static analysis.
8. YARA scanning.
9. ClamAV scanning.
10. Optional fuzzy hashing, IOC feeds and sandbox enrichment.

Entropy is supporting evidence only; it cannot independently produce a malware verdict.

### Phase 9 — Risk and verdict

Evidence is combined into hardware, trust, interface, behavior, storage, policy and vulnerability risk. The normalized verdict is `CLEAN`, `TRUSTED`, `SUSPICIOUS`, `DANGEROUS` or `INCOMPLETE`.

### Phase 10 — Operator decision

The backend creates a short-lived action with allowed choices and a one-time confirmation token. The dashboard can answer that action but cannot invent a new authorization request. Expired or replayed decisions are rejected.

### Phase 11 — Remediation

The device is released, kept blocked, or quarantined according to policy and operator action. Quarantine restoration requires integrity verification and a fresh scan.

### Phase 12 — Evidence and persistence

Authoritative incident, identity, finding, engine-version, metric and audit records are stored transactionally in SQLite. JSON and PDF reports are exports of those records.

### Phase 13 — Notification and observability

Structured events record incident ID, port session, identity, state transition, engine result, failure reason, duration and enforcement latency. Suspicious, dangerous and incomplete incidents enter the persistent email queue.

### Phase 14 — Removal and shutdown

Device removal cancels workers, unmounts isolation paths and records an incomplete incident. Shutdown restores only eligible pre-existing or signed-trusted HID devices; dangerous sessions remain blocked.

## 3. Component map

| Component | Responsibility |
|---|---|
| `run.sh` | Installation, preflight, service and administration |
| `changed.py` | Current production controller and legacy orchestration |
| `backend/ipc/server.py` | Dashboard protocol, actions, events and audit |
| `ui/sentinel/` | Non-privileged dashboard |
| `backend/scanner/` | USB lifecycle, HID, storage and detection |
| `backend/scanner/advanced_detection.py` | MIME, PE/ELF, document and archive evidence |
| `backend/security/` | Fingerprints, trust, NVD and risk intelligence |
| `backend/database/` | SQLite connections, schema and migrations |
| `backend/reports/` | JSON/PDF evidence generation |
| `backend/notifications/` | Email queue, delivery and retry |
| `tools/` | Validation, recovery, trust and operational commands |
| `config/usb-scanner.service` | Root service and OS-level sandboxing |

## 4. Persistent data flow

```text
USB event
  → device identity
  → port session / incident
  → scan findings
  → risk and verdict
  → remediation action
  → audit record
  → JSON/PDF export
  → notification queue
```

## 5. Security principles

- Default deny for unknown hardware.
- Exact identity trust instead of VID/PID-only trust.
- Fail closed when required engines fail.
- Root hardware control separated from hostile file parsing.
- Operator actions are scoped, expiring and replay-resistant.
- Reports are evidence exports, not the source of truth.
- Every important transition is auditable and observable.

## 6. Current implementation status

Implemented foundations include content evidence, stronger identity construction, SQLite migrations, IPC size/schema controls, peer-credential capture, confirmation tokens, structured observability and systemd hardening. Remaining production work is listed in the project delivery plan: full parser/signature integrations, signed IOC feeds, sandbox adapters, complete process separation, MAC/seccomp profiles, state-machine refactoring and Linux hardware acceptance testing.

The backend workflow state machine is implemented in
`backend/scanner/workflow.py`. It is deliberately adapter-based so isolation,
scanning, remediation, release and re-verification can be tested without the
dashboard or physical USB hardware.
