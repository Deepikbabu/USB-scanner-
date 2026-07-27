#!/usr/bin/env python3
"""Run automated checks for USB scanner features."""

import os
import sys
import tempfile
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

PASS = 0
FAIL = 0
SKIP = 0


def ok(name, detail=""):
    global PASS
    PASS += 1
    print(f"  PASS  {name}" + (f" — {detail}" if detail else ""))


def bad(name, detail=""):
    global FAIL
    FAIL += 1
    print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))


def skip(name, detail=""):
    global SKIP
    SKIP += 1
    print(f"  SKIP  {name}" + (f" — {detail}" if detail else ""))


def section(title):
    print(f"\n{'=' * 60}")
    print(title)
    print("=" * 60)


def main():
    section("1. Dependencies")
    try:
        import pyudev  # noqa: F401
        ok("pyudev")
    except ImportError:
        bad("pyudev", "run: .venv/bin/pip install -r requirements.txt")

    try:
        from fpdf import FPDF  # noqa: F401
        ok("fpdf2")
    except ImportError:
        bad("fpdf2", "PDF reports disabled until installed")

    if shutil.which("clamdscan"):
        ok("ClamAV", "clamdscan available")
    elif shutil.which("clamscan"):
        ok("ClamAV", "clamscan available")
    else:
        skip("ClamAV", "install clamav for antivirus engine scanning")

    section("2. Malware database")
    try:
        from db_init import ensure_database, DB_NAME
        ensure_database()
        ok("database created", DB_NAME)

        import sqlite3
        conn = sqlite3.connect(DB_NAME)
        count = conn.execute("SELECT COUNT(*) FROM malware_hashes").fetchone()[0]
        conn.close()
        if count >= 1:
            ok("hash entries loaded", f"{count} signature(s)")
        else:
            bad("hash entries", "table is empty")
    except Exception as e:
        bad("database", str(e))

    section("3. Hash detection (EICAR test file)")
    try:
        from changed import calculate_sha256, check_hash

        eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
        path = os.path.join(tempfile.gettempdir(), "eicar_test.com")
        with open(path, "wb") as f:
            f.write(eicar)

        digest = calculate_sha256(path)
        match = check_hash(digest)
        if match and match.get("signature") == "EICAR-Test-File":
            ok("EICAR hash match", match["signature"])
        else:
            bad("EICAR hash match", f"got {match}")
    except Exception as e:
        bad("hash detection", str(e))

    section("4. YARA smoke test")
    try:
        from backend.scanner import yara_engine

        eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
        if yara_engine.yara is None or not yara_engine.RULES_PATH.exists():
            skip("direct YARA scan", "yara-python or bundled rules unavailable")
        else:
            rules = yara_engine.load_rules()
            if rules is None:
                skip("direct YARA scan", "YARA rules could not be compiled")
            else:
                tmp = tempfile.mkdtemp()
                try:
                    sample_path = os.path.join(tmp, "yara_test.txt")
                    with open(sample_path, "wb") as f:
                        f.write(eicar)

                    direct_findings = yara_engine.scan_bytes(eicar, "yara_test.txt")
                    direct_rules = {finding.rule for finding in direct_findings}
                    if "USB_EICAR_Test" in direct_rules:
                        ok("direct YARA scan", ", ".join(sorted(direct_rules)))
                    else:
                        bad("direct YARA scan", f"rules={sorted(direct_rules)}")

                    try:
                        from changed import static_analyze
                    except ImportError as e:
                        skip("scanner YARA integration", f"scanner module unavailable: {e}")
                    else:
                        static_findings = static_analyze(sample_path)
                        static_rules = {finding.get("rule") for finding in static_findings if isinstance(finding, dict)}
                        if "USB_EICAR_Test" in static_rules:
                            ok("scanner YARA integration", ", ".join(sorted(rule for rule in static_rules if rule)))
                        else:
                            bad("scanner YARA integration", f"rules={sorted(rule for rule in static_rules if rule)}")
                finally:
                    shutil.rmtree(tmp)
    except Exception as e:
        bad("YARA smoke test", str(e))

    section("5. Static analysis engine")
    try:
        from changed import static_analyze, calculate_risk

        tmp = tempfile.mkdtemp()
        try:
            ps1 = os.path.join(tmp, "test.ps1")
            with open(ps1, "w") as f:
                f.write("powershell -w hidden -enc SGVsbG8=")
            findings = static_analyze(ps1)
            risk = calculate_risk(findings)
            if findings and risk in ("HIGH", "MEDIUM", "LOW"):
                ok("suspicious script detection", f"risk={risk}, {len(findings)} finding(s)")
            else:
                bad("suspicious script detection", f"findings={findings}")

            clean = os.path.join(tmp, "notes.txt")
            with open(clean, "w") as f:
                f.write("hello")
            if not static_analyze(clean):
                ok("clean file ignored")
            else:
                bad("clean file", "unexpected findings")
        finally:
            shutil.rmtree(tmp)
    except Exception as e:
        bad("static analysis", str(e))

    section("6. PDF report generation")
    try:
        from changed import generate_pdf_report, FPDF

        if FPDF is None:
            skip("PDF report", "fpdf2 not installed")
        else:
            reports_dir = os.path.join(ROOT, "reports")
            os.makedirs(reports_dir, mode=0o755, exist_ok=True)
            test_path = os.path.join(reports_dir, "_self_test.pdf")
            if os.path.exists(test_path):
                os.remove(test_path)

            before = set(os.listdir(reports_dir))
            generate_pdf_report(
                {"vendor": "SelfTest", "model": "USB", "vid": "0000", "pid": "0000", "serial": "TEST", "usb_class": "Test", "usb_driver": "Test"},
                0, 0, 0, 0, 0, False, ["automated self-test"],
            )
            after = set(os.listdir(reports_dir))
            new_pdfs = [f for f in after - before if f.endswith(".pdf")]
            if new_pdfs:
                ok("PDF report", new_pdfs[0])
            else:
                bad("PDF report", "no new file in reports/")
    except Exception as e:
        bad("PDF report", str(e))

    section("7. HID device parser")
    try:
        from changed import _parse_proc_input, calculate_hid_risk, HID_WHITELIST

        devices = _parse_proc_input()
        ok("HID parser", f"{len(devices)} USB HID device(s) on this Pi")
        for event, info in list(devices.items())[:3]:
            vid_pid = info.get("device_id", "?")
            risk, flags = calculate_hid_risk(info, event)
            whitelisted = vid_pid in HID_WHITELIST
            print(f"        {event} {vid_pid} risk={risk} whitelist={'yes' if whitelisted else 'no'}")
    except Exception as e:
        bad("HID parser", str(e))

    section("8. USB event monitor (pyudev)")
    try:
        import pyudev

        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by(subsystem="usb")
        monitor.start()
        ok("USB udev monitor", "can subscribe to kernel events")
    except Exception as e:
        bad("USB udev monitor", str(e))

    section("9. Mount helper (udisks)")
    if shutil.which("udisksctl"):
        ok("udisksctl found", "will try to mount USB if desktop does not")
    else:
        skip("udisksctl", "install udisks2 for auto-mount fallback")

    section("10. Phone/MTP mount helpers")
    helpers = []
    for helper in ("gio", "simple-mtpfs", "jmtpfs"):
        if shutil.which(helper):
            helpers.append(helper)
    if helpers:
        ok("MTP helper found", ", ".join(helpers))
    else:
        skip("MTP helper", "install gio/gvfs or simple-mtpfs to scan Android phone storage")

    section("11. Root privileges (storage gate + HID blocking)")
    if not hasattr(os, "geteuid"):
        skip("root check", "not available on this OS; enforcement is Linux-only")
    elif os.geteuid() == 0:
        ok("running as root", "storage accept/block and HID blocking should work")
    else:
        skip("root check", "enforcement needs: sudo ./run.sh")

    section("SUMMARY")
    total = PASS + FAIL + SKIP
    print(f"  Passed : {PASS}/{total}")
    print(f"  Failed : {FAIL}/{total}")
    print(f"  Skipped: {SKIP}/{total} (manual or optional)")

    if FAIL == 0:
        print("\n  Automated checks OK. Do the manual USB/HID tests below.")
    else:
        print("\n  Fix failed checks before testing with real USB devices.")

    print("""
MANUAL TESTS (do these yourself)
--------------------------------

A) USB STORAGE SCAN
   1. Run:  ./run.sh
   2. Plug in a USB flash drive (FAT32/exFAT is easiest)
   3. Expect:
        [ EVENT ] USB Device Detected - Analyzing...
        [+] Mounted at /media/...
        [ SCANNING ] High-Speed Threaded FS Analysis...
        COMPLETE USB DEVICE SECURITY REPORT
        [+] PDF Report Generated: reports/scan_report_....pdf
   4. Optional: put the EICAR test file on the stick — should flag as EICAR-Test-File

B) HID WHITELIST (your keyboard should NOT be blocked)
   1. Run:  ./run.sh
   2. Unplug and replug your keyboard (or plug a known keyboard)
   3. Expect: device listed as WHITELISTED, no blocking message

C) HID BLOCKING / STORAGE BLOCKING (needs root)
   1. Run:  sudo ./run.sh
   2. Plug in an unknown USB keyboard or unsafe USB storage
   3. Expect unknown keyboards to be blocked
   4. Expect unsafe storage to stay unmounted/rejected

D) SCAN LOG
   After a USB scan, check:  cat scan_log.json
   (one JSON line per suspicious file)

E) ANDROID PHONE / MTP SCAN
   1. Install one MTP helper: gio/gvfs or simple-mtpfs
   2. Run:  ./run.sh
   3. Unlock the phone and select File Transfer / MTP, not Charging Only
   4. Expect:
        [*] Mobile phone storage mode detected (MTP/PTP)
        [+] Phone storage accessible at /run/user/.../gvfs/mtp:...
        [ SCANNING ] High-Speed Threaded FS Analysis...
        COMPLETE USB DEVICE SECURITY REPORT

Press Ctrl+C to stop the scanner when done.
""")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
