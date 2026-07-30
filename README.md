# USB Scanner (Raspberry Pi/Linux)

This project monitors USB and HID events, isolates unknown devices before
driver binding, mounts storage read-only, and combines hash, heuristic, YARA,
and ClamAV results before allowing or blocking a device.

## Start

Disconnect every untrusted USB device before the first setup. Devices already
connected during first USBGuard policy generation form the trusted baseline.

```bash
chmod +x run.sh
./run.sh --check
./run.sh
```

If an untrusted HID was connected during the first baseline generation,
disconnect it and rebuild the baseline:

```bash
./run.sh --reset-usbguard
```

Useful backend diagnostics:

```bash
./run.sh --status
./run.sh --test-yara
./run.sh --test-clamav
./run.sh --list-hid
./run.sh --trust-hid
./run.sh --untrust-hid
./run.sh --repair-input
./run.sh --approve-hid
./run.sh --revoke-hid
./run.sh --rescan-hid
./run.sh --configure-nvd
./run.sh --test-nvd
./run.sh --list-trusted-storage
./run.sh --forget-storage
./run.sh --approve-storage
./run.sh --revoke-storage
./run.sh --rescan-storage
./run.sh --list-quarantine
./run.sh --restore-quarantine
./run.sh --delete-quarantine
./run.sh --simulate
./run.sh --validate
./run.sh --install-service
./run.sh --configure-email
./run.sh --test-email
./run.sh --email-status
```

## Live dashboard

The dashboard is a non-privileged viewer for the existing scanner service; it
does not replace udev/USBGuard isolation or run a second scanner. Install the
service once, then launch the interface without `sudo`. The launcher activates
its protected backend access automatically; no user/group command, logout or
reboot is required:

```bash
sudo ./run.sh --install-service
./run.sh --validate-dashboard
./run.sh --dashboard
```

During installation, disconnect untrusted USB input devices and type
`BASELINE` when prompted. The installer signs the mouse, keyboard, and receiver
devices already working at the physical console. Unknown HID devices remain
blocked. The baseline can be refreshed explicitly with:

```bash
sudo ./run.sh --enroll-input-baseline
```

Settings → Scanner Health displays the backend build ID and absolute project
path. A version/path mismatch means the systemd service must be reinstalled
from the same checkout before scanning.

The Overview, Scan, History, and Settings pages consume live and persisted
events through `/run/usb-scanner/backend.sock`. Device detection, lifecycle
state, YARA/ClamAV progress, findings, risk, reports, quarantine and email
delivery status come from the backend. When the backend requests a decision,
the dashboard displays a blocking dialog and safely defaults to keeping the
device blocked. The interface contains no automatic sample-device or sample-
malware timers.

`--trust-hid` lists connected HID devices with USBGuard state, VID:PID,
physical port, serial, interfaces, and descriptor hash. Trust requires typing
`TRUST`, updates both USBGuard's persistent rules and `whitelist.json`, and
survives scanner shutdown/reboot. `--untrust-hid` removes both forms of trust
and blocks connected instances. `--repair-input` reauthorizes currently
connected devices already present in the project whitelist.

The launcher installs missing Debian and Python dependencies, including
USBGuard, YARA, and ClamAV. It initializes the malware database, downloads
ClamAV definitions, starts the required services, and runs preflight.

If Debian's ClamAV package cannot be installed on ARM64, setup discovers the
current official ARM64 `.deb` from <https://www.clamav.net/downloads>.

## Security flow

Device type is inferred automatically; there is no device-type menu. USBGuard
provides default-deny isolation before Linux binds an input driver. Unknown HID
and composite HID devices remain blocked, preventing keystroke injection.
Trusted HID VID:PID entries retain the existing whitelist behavior.

Storage is temporarily authorized and scanned from a
`ro,nosuid,nodev,noexec` mount. ClamAV or YARA failures are reported as failed
or degraded engine states instead of being presented as clean scans.

Normal device workflows are processed one at a time. Initial PDF/JSON evidence
is written before a remediation question and final PDF/JSON evidence afterward.
Reports are stored in the repository's `reports/` directory.

Interactive decisions use a full `USER ACTION REQUIRED` screen. The scanner
states that it is paused, explains each numbered choice, validates input, and
defaults to blocking when the timeout expires. Quarantine requires a second
confirmation because it temporarily writes to the storage device.

## Fingerprints and vulnerability intelligence

HID trust records are HMAC-signed under `/var/lib/usb-scanner` and include
hardware, descriptor, and interface fingerprints. Storage trust includes a
SHA-256 manifest and scan-engine signature. On repeat scans, unchanged files
reuse cached clean results only when their hashes and the YARA/ClamAV engine
signature still match; new or changed files receive a full scan.

Physical-port sessions correlate USB identity changes and re-enumeration. Once
a connection exhibits unknown HID, dangerous composite interfaces, a known
attack-platform indicator, or identity changes, every personality on that port
remains blocked until physical disconnect and session expiry. Unsupported
`other` devices are blocked rather than reported clean.

NVD enrichment is optional. Configure an individual API key without placing it
in the repository:

```bash
sudo ./run.sh --configure-nvd
sudo ./run.sh --test-nvd
```

Only administrator-reviewed CPE mappings in `config/device_cpe_map.json` with
`verified` or `high` confidence affect risk. NVD responses are cached locally;
API failure never bypasses USB isolation and missing CPE coverage never means
that a device is clean.

## Fast HID enforcement and recovery

HID blocking is kept on the enforcement path while PDF/JSON creation runs in
the background. Rapid identities from the same physical port are debounced
into one incident, alerts fire once per session, and output includes measured
enforcement latency. Work still waiting in the scan queue is cancelled when a
device is unplugged. Temporary read-only mounts are released during startup.

Quarantine restoration verifies the stored SHA-256 and rescans with the
current engines; an unsafe or modified item cannot be restored. Individual
items can be deleted without purging the complete vault.

For unattended Pi operation, `--install-service` installs a restart-on-failure
systemd unit. Use `journalctl -u usb-scanner -f` for bounded system journal
logging, and `./run.sh --uninstall-service` to remove it. `--simulate` validates
trusted HID, unknown HID, composite, re-enumeration, and storage policy without
authorizing or mounting real hardware.

Each physical-port connection receives one stable incident identifier, so
later evidence overwrites/extends the same PDF and JSON instead of producing
duplicate reports. Verdicts are normalized to `CLEAN`, `TRUSTED`,
`SUSPICIOUS`, `DANGEROUS`, or `INCOMPLETE`. An unplug during scanning signals
the active file workers, cancels queued work, unmounts isolation paths, and
records `DEVICE REMOVED DURING ANALYSIS`.

`--validate` runs all safe policy scenarios, compiles YARA rules, and verifies
ClamAV with EICAR. Physical USBGuard enforcement must still be validated on the
Pi because simulation intentionally never authorizes real hardware.

## Email notifications

SMTP credentials are stored only in `/etc/usb-scanner/email.env` with mode
`0600`. Configure and verify delivery before enabling the background service:

```bash
sudo ./run.sh --configure-email
sudo ./run.sh --test-email
sudo ./run.sh --email-status
```

`SUSPICIOUS`, `DANGEROUS`, and `INCOMPLETE` incidents are queued only after
their consolidated JSON/PDF reports exist. `CLEAN` and `TRUSTED` devices do
not generate email. Delivery is deduplicated by incident ID, persisted in
`/var/lib/usb-scanner/email_delivery.db`, retried with backoff, and spooled
under `/var/lib/usb-scanner/email-spool`. Suspicious files are never attached.
Use `--disable-email`, `--enable-email`, or `--retry-email` for administration.
