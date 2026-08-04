# Backend-First Delivery Plan

The dashboard is intentionally out of scope until all backend phases pass.
UI files remain in the repository, but backend tests must not import or depend
on `ui/`.

## Phase 0 — Backend boundary and inventory

Goal: define what is backend and make it independently importable.

Scope:

- `changed.py` production controller;
- `backend/` packages;
- `config/` runtime configuration;
- `tools/` backend administration and validation;
- SQLite databases, trust records, quarantine and reports;
- USBGuard, udev, mount and scanner adapters.

Pass criteria:

- backend imports without PyQt6;
- no backend module imports `ui`;
- one documented production entry point;
- no UI process is required to block or scan a device.

## Phase 1 — Configuration and persistence

Goal: make backend state reliable and transactional.

Implement and verify:

- SQLite migrations;
- foreign keys and indexes;
- device identities and history;
- incidents and findings;
- engine versions;
- quarantine records;
- pending actions;
- notification delivery state;
- audit records and hash-chain verification;
- backup and recovery.

Pass criteria:

- database can be created from an empty directory;
- migrations are repeatable;
- interrupted writes do not corrupt state;
- restore tests pass;
- reports can be regenerated from database records.

## Phase 2 — Device discovery and identity

Goal: produce a stable exact identity for every USB device.

Implement and verify:

- udev event collection;
- descriptor canonicalization;
- configuration/interface/endpoint fingerprints;
- serial-quality scoring;
- USB topology;
- capacity and partition fingerprint;
- filesystem UUID;
- firmware data;
- manufacturer/model consistency;
- identity history and change detection.

Pass criteria:

- identical VID/PID devices do not collide when identity evidence differs;
- descriptor changes create a new identity;
- missing serials reduce trust quality;
- port changes do not incorrectly change portable identity;
- cloned or re-enumerated devices are detected.

## Phase 3 — Isolation and lifecycle

Goal: guarantee default-deny behavior and safe device lifecycle handling.

Implement and verify:

- USBGuard default deny;
- pre-driver HID blocking;
- read-only storage mounting;
- `nosuid,nodev,noexec` validation;
- mount namespace isolation;
- stale mount cleanup;
- device removal cancellation;
- port-session locking;
- shutdown and reboot recovery.

Pass criteria:

- unknown HID remains blocked;
- composite HID/storage remains blocked;
- storage is never scanned from a writable normal mount;
- removal cancels active work;
- dangerous ports remain blocked after restart.

## Phase 4 — Restricted scan worker

Goal: ensure hostile file parsing does not run with hardware-control privileges.

Implement and verify:

- dedicated worker UID;
- bubblewrap subprocess sandbox;
- no network;
- minimal read-only filesystem view;
- isolated input mount;
- temporary scratch directory;
- dropped capabilities;
- seccomp and Landlock defense-in-depth;
- CPU, memory, file-count and wall-clock limits;
- newline-delimited JSON result protocol;
- fail-closed behavior when the sandbox is unavailable.

Pass criteria:

- worker cannot read host home or state directories;
- worker cannot access USB device nodes;
- worker cannot create network connections;
- worker cannot mount, ptrace or load BPF;
- worker termination leaves the controller safe;
- unsandboxed fallback is impossible in production mode.

## Phase 5 — File and content analysis

Goal: analyze hostile content with bounded, evidence-based engines.

Implement and verify:

- streaming SHA-256;
- content-based MIME detection;
- PE and ELF parsing;
- executable signature verification;
- Office macro analysis;
- PDF JavaScript and embedded-object analysis;
- archive inspection;
- ZIP/TAR/GZIP/7z limits;
- path traversal and link rejection;
- fuzzy hashing;
- YARA and ClamAV integration;
- engine version and freshness tracking;
- optional IOC and sandbox adapters.

Pass criteria:

- entropy never independently creates a malware verdict;
- malformed files cannot crash the controller;
- archive limits are checked before full expansion;
- stale engines prevent a `CLEAN` verdict;
- engine failures produce `INCOMPLETE`.

## Phase 6 — HID behavioral security

Goal: detect trusted-looking but malicious HID behavior.

Implement and verify:

- enumeration cooldown;
- input suppression during cooldown;
- inter-key timing analysis;
- impossible typing-rate detection;
- modifier abuse detection;
- layout mismatch as supporting evidence;
- composite HID policy;
- typed confirmation for composite authorization.

Pass criteria:

- a trusted VID/PID cannot bypass behavioral checks;
- composite HID/storage has a `SUSPICIOUS` floor;
- authorization requires an exact challenge response;
- suspicious behavior keeps the device blocked.

## Phase 7 — Verdict, remediation and TOCTOU

Goal: ensure release decisions are based on current content and current identity.

Implement and verify:

- risk aggregation;
- `CLEAN`, `TRUSTED`, `SUSPICIOUS`, `DANGEROUS`, `INCOMPLETE` verdicts;
- release-time file manifest comparison;
- selective re-hashing;
- mount/device identity re-verification;
- quarantine integrity checks;
- safe restoration and deletion;
- typed, expiring operator actions;
- replay protection.

Pass criteria:

- changed files cannot be released using an old verdict;
- changed device identity fails closed;
- expired actions are rejected;
- replayed actions are rejected;
- incomplete analysis never releases a device.

## Phase 8 — IPC, audit and observability

Goal: expose backend state safely without giving the client hardware authority.

Implement and verify:

- Unix socket permissions;
- `SO_PEERCRED` verification;
- per-command authorization;
- strict request schemas;
- message-size limits;
- rate limiting;
- action tokens and expiry;
- structured JSON events;
- hash-chained audit records;
- JSON syslog/CEF/webhook exporters;
- enforcement and scan metrics.

Pass criteria:

- the UI cannot invent authorization requests;
- unauthorized peers cannot issue sensitive commands;
- malformed or oversized requests are rejected;
- audit-chain tampering is detected;
- observability never blocks enforcement.

## Phase 9 — Backend integration testing

Goal: validate the complete backend without the UI.

Test layers:

1. Pure unit tests.
2. SQLite migration and recovery tests.
3. Fake USBGuard and mount-adapter tests.
4. Fake udev lifecycle tests.
5. Scan-worker subprocess tests.
6. Malformed-file and archive-bomb tests.
7. IPC protocol and replay tests.
8. Crash, timeout and device-removal tests.
9. Linux integration tests with loopback disk images.
10. Physical USB acceptance tests on Raspberry Pi.

Pass criteria:

- all portable tests pass in CI;
- all Linux integration tests pass on target hardware;
- physical HID and storage acceptance tests pass;
- no backend test imports PyQt6 or starts the dashboard.

## Phase 10 — UI integration (later)

Only after Phases 0–9 pass:

- enable dashboard imports;
- connect UI to the stable IPC schema;
- test rendering and event handling;
- test operator workflows;
- test dashboard failure/reconnect behavior.

The UI must remain a viewer and decision client. It must never become the
component responsible for device blocking, scanning or release authorization.
