import pyudev
import os
import time
import sqlite3
import hashlib
import fcntl
import struct
import threading
import re
import math
import collections
import functools
import zipfile
import io
import json
import base64
import binascii
import concurrent.futures
import warnings
import shutil
from datetime import datetime
from pathlib import Path
import subprocess
import sys
import tty
import termios
import queue
import select

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

from db_init import DB_NAME, ensure_database
from backend.scanner.yara_engine import load_rules as load_yara_rules
from backend.scanner.yara_engine import scan_bytes as yara_scan_bytes
from backend.security.intelligence import (
    NVDClient, SignedTrustStore, hardware_fingerprint, interface_fingerprint,
    device_identity_fingerprint, incident_verdict, risk_breakdown,
)
from backend.notifications import (
    queue_incident_email, queue_operational_email, start_email_worker,
)
from backend.ipc import get_ipc_server, publish_event

UI_MODE = False
CLI_AUTO = False
UI_RESPONSES = queue.Queue()
ACTIVE_DEVICE_PATHS = set()
DISCONNECTED_DEVICE_PATHS = set()
DEVICE_CANCEL_EVENTS = {}
DEVICE_EVENT_QUEUE = queue.Queue()
REPORT_QUEUE = queue.Queue()
REPORT_PENDING = {}
REPORT_LOCK = threading.Lock()
REPORT_RENDER_LOCK = threading.Lock()
DEVICE_STATES = {}
PROMPT_ACTIVE = threading.Event()
PORT_SESSIONS = {}
PORT_SESSION_GENERATION = {}
ACTIVE_ISOLATION_MOUNTS = set()


class DeviceRemovedDuringAnalysis(RuntimeError):
    pass


def port_session(port):
    return PORT_SESSIONS.setdefault(port, {
        "port": port, "started_at": datetime.now().isoformat(), "vid_pid_history": [],
        "interface_history": [], "blocked": False, "risk": 0, "findings": [],
        "detected_monotonic": time.monotonic(), "blocked_monotonic": None,
        "alert_sent": False, "report_queued": False, "connected": True,
        "enforcement_recorded": False, "re_enumeration_count": 0,
        "report_generated": False,
        "incident_id": f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{re.sub(r'[^A-Za-z0-9_.-]', '_', port)}",
    })


def lock_port_session(port, reason, risk):
    session = port_session(port)
    session["blocked"] = True
    if session.get("blocked_monotonic") is None:
        session["blocked_monotonic"] = time.monotonic()
    session["risk"] = min(100, session["risk"] + risk)
    if reason not in session["findings"]:
        session["findings"].append(reason)


def schedule_session_clear(port, delay=3.0):
    generation = PORT_SESSION_GENERATION.get(port, 0) + 1
    PORT_SESSION_GENERATION[port] = generation
    if port in PORT_SESSIONS:
        PORT_SESSIONS[port]["connected"] = False
    def clear_later():
        time.sleep(delay)
        if PORT_SESSION_GENERATION.get(port) == generation:
            session = PORT_SESSIONS.get(port)
            if session and not session.get("report_generated"):
                queue_session_report(port, final=True)
            publish_event("device_state", {
                "device_id": port, "state": "DISCONNECTED",
                "detail": "physical USB device removed; temporary isolation released",
            }, session.get("incident_id") if session else None)
            PORT_SESSIONS.pop(port, None)
            print(f"[STATE] {port}: DISCONNECTED - connection session cleared")
            if session and session.get("report_generated"):
                print("[READY] Monitoring for the next USB device...")
    threading.Thread(target=clear_later, daemon=True).start()


def set_device_state(device_id, state, detail=""):
    """Record and display one authoritative lifecycle state per USB device."""
    DEVICE_STATES[device_id] = state
    suffix = f" - {detail}" if detail else ""
    print(f"[STATE] {device_id}: {state}{suffix}")
    incident_id = None
    for session in PORT_SESSIONS.values():
        if session.get("port") and session["port"] in str(device_id):
            incident_id = session.get("incident_id"); break
    publish_event("device_state", {"device_id": str(device_id), "state": state, "detail": detail}, incident_id)


def request_user_action(title, device_name, summary, options, default, timeout=60):
    """Display an unmistakable, validated CLI decision prompt.

    ``options`` maps accepted lower-case inputs to ``(result, label)``. A lack
    of input always resolves to the caller's safe default.
    """
    ipc = get_ipc_server()
    action_id = ipc.register_action(title, device_name, summary, options, default, timeout)
    chosen = default
    expired = False
    PROMPT_ACTIVE.set()
    try:
        interactive = sys.stdin.isatty()
        if not interactive:
            print(f"[ACTION] Waiting up to {timeout}s for dashboard response. Safe default: {default.upper()}")
            response = ipc.wait_action(action_id, timeout)
            chosen = response or default
            expired = response is None
            return chosen
        print("\n" + "#" * 68)
        print("#" + " USER ACTION REQUIRED ".center(66) + "#")
        print("#" * 68)
        print(f"\n{title}")
        print(f"Device: {device_name}")
        print(summary)
        print("\nThe scanner is PAUSED and the USB remains BLOCKED.")
        print("Choose one option, type its number, then press Enter:\n")
        shown = set()
        for key, (result, label) in options.items():
            if result in shown or not key.isdigit():
                continue
            shown.add(result)
            print(f"  [{key}] {label}")
        print(f"\nWaiting up to {timeout} seconds. Safe default: {default.upper()}")

        deadline = time.time() + timeout
        prompt_drawn = False
        while True:
            remaining = max(0, int(deadline - time.time()))
            if not prompt_drawn:
                print(f"\nYOUR CHOICE ({remaining}s remaining) > ", end="", flush=True)
                prompt_drawn = True
            dashboard_value = ipc.wait_action(action_id, min(0.25, max(0, deadline - time.time())))
            if dashboard_value is not None:
                print(f"\nDashboard selected: {dashboard_value}")
                chosen = dashboard_value
                return chosen
            ready, _, _ = select.select([sys.stdin], [], [], 0)
            if not ready:
                if time.time() >= deadline:
                    print(f"\n\nNo response received. Applying safe default: {default.upper()}")
                    expired = True
                    return chosen
                continue
            value = sys.stdin.readline().strip().lower()
            if value in options:
                result, label = options[value]
                print(f"\nYou selected: {label}")
                chosen = result
                return chosen
            print(f"Invalid choice: {value!r}. Please use one of the numbered options.")
            prompt_drawn = False
    finally:
        ipc.finish_action(action_id, chosen, expired=expired)
        PROMPT_ACTIVE.clear()

def emit_ui_event(event_type, data=None):
    """Emit JSON events to stdout for the UI frontend."""
    event_data = data if isinstance(data, dict) else {"message": str(data)} if data is not None else {}
    incident_id = event_data.get("incident_id")
    publish_event(event_type, event_data, incident_id)
    if not UI_MODE:
        return
    payload = {"type": event_type}
    if isinstance(data, dict):
        payload.update(data)
    elif data is not None:
        payload["message"] = str(data)
    print(json.dumps(payload), file=sys.__stdout__, flush=True)

def prompt_ui(prompt_id, data=None):
    """Emit a prompt event and wait for a JSON response from stdin."""
    if not UI_MODE:
        return None
    payload = {"type": "prompt", "prompt_id": prompt_id}
    if data:
        payload.update(data)
    print(json.dumps(payload), file=sys.__stdout__, flush=True)
    # Block and wait for response from stdin
    try:
        response = UI_RESPONSES.get(timeout=300)
        if isinstance(response, dict):
            return response
    except queue.Empty:
        emit_ui_event("log", f"UI prompt timed out: {prompt_id}")
    except Exception:
        pass
    return None

# ==========================================
# TERMINAL COLORS
# ==========================================
class Colors:
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    END    = "\033[0m"

# ==========================================
# HID WHITELIST
# Add YOUR trusted devices here as "vid:pid": "Name"
# Run `lsusb` to find your device IDs.
# ==========================================
HID_RISK_CACHE = {}

WHITELIST_FILE = os.path.join(os.path.dirname(__file__), "whitelist.json")
STORAGE_WHITELIST_FILE = os.path.join(os.path.dirname(__file__), "storage_whitelist.json")
QUARANTINE_DIR = os.path.join(os.path.dirname(__file__), "quarantine")
QUARANTINE_LOG = os.path.join(QUARANTINE_DIR, "quarantine_log.json")

def _fix_file_ownership(filepath):
    """If running as sudo, change file ownership to the original user."""
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user:
        try:
            import pwd
            uid = pwd.getpwnam(sudo_user).pw_uid
            gid = pwd.getpwnam(sudo_user).pw_gid
            os.chown(filepath, uid, gid)
        except Exception:
            pass

def load_whitelist():
    global HID_WHITELIST
    HID_WHITELIST = {}
    
    if not os.path.exists(WHITELIST_FILE):
        # Create default whitelist.json if it doesn't exist
        default_whitelist = {
            "413c:2113": "Dell KB216 Wired Keyboard",
            "413c:3020": "Dell KB216 Wired Keyboard (alt)",
            "0461:4d15": "Primax Electronics Keyboard",
            "046d:c534": "Logitech USB Receiver",
            "093a:2510": "PixArt Optical USB Mouse",
            "1c4f:0034": "SIGMACHIP USB Mouse",
        }
        try:
            with open(WHITELIST_FILE, "w") as f:
                json.dump(default_whitelist, f, indent=4)
            _fix_file_ownership(WHITELIST_FILE)
        except Exception:
            pass

    if os.path.exists(WHITELIST_FILE):
        try:
            with open(WHITELIST_FILE, "r") as f:
                HID_WHITELIST.update(json.load(f))
        except Exception:
            pass

load_whitelist()

def load_storage_whitelist():
    global STORAGE_WHITELIST
    STORAGE_WHITELIST = {}

    if not os.path.exists(STORAGE_WHITELIST_FILE):
        try:
            with open(STORAGE_WHITELIST_FILE, "w") as f:
                json.dump({}, f, indent=4)
            _fix_file_ownership(STORAGE_WHITELIST_FILE)
        except Exception:
            pass

    if os.path.exists(STORAGE_WHITELIST_FILE):
        try:
            with open(STORAGE_WHITELIST_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    STORAGE_WHITELIST.update(data)
        except Exception:
            pass

load_storage_whitelist()

def save_whitelist():
    try:
        with open(WHITELIST_FILE, "w") as f:
            json.dump(HID_WHITELIST, f, indent=4)
        _fix_file_ownership(WHITELIST_FILE)
    except Exception:
        pass

def save_storage_whitelist():
    try:
        with open(STORAGE_WHITELIST_FILE, "w") as f:
            json.dump(STORAGE_WHITELIST, f, indent=4)
        _fix_file_ownership(STORAGE_WHITELIST_FILE)
        with open(STORAGE_WHITELIST_FILE, "r", encoding="utf-8") as stream:
            saved = json.load(stream)
        return isinstance(saved, dict)
    except Exception:
        return False

def trust_storage_device(vid_pid, usb_info, fingerprint, file_hashes):
    record = {
        "label": f"{usb_info.get('vendor', 'Unknown')} {usb_info.get('model', 'USB Device')}",
        "serial": usb_info.get("serial", "Unknown"),
        "fingerprint": fingerprint,
        "file_hashes": file_hashes,
        "trusted_at": datetime.now().isoformat(),
        "device_type": "storage",
        "hardware_fingerprint": usb_info.get("hardware_fingerprint"),
        "interface_fingerprint": usb_info.get("interface_fingerprint"),
        "engine_signature": scan_engine_signature(),
    }
    STORAGE_WHITELIST[vid_pid] = record
    if not save_storage_whitelist():
        STORAGE_WHITELIST.pop(vid_pid, None)
        return False
    try:
        SignedTrustStore().put(f"storage:{vid_pid}:{usb_info.get('serial', 'Unknown')}", record)
    except Exception:
        STORAGE_WHITELIST.pop(vid_pid, None)
        save_storage_whitelist()
        return False
    return True

def invalidate_storage_trust(vid_pid, reason):
    if vid_pid in STORAGE_WHITELIST:
        del STORAGE_WHITELIST[vid_pid]
        save_storage_whitelist()
    return reason

def storage_trust_matches(vid_pid, usb_info, fingerprint):
    entry = STORAGE_WHITELIST.get(vid_pid)
    if not isinstance(entry, dict):
        return False, None

    serial_matches = entry.get("serial") == usb_info.get("serial")
    fingerprint_matches = entry.get("fingerprint") == fingerprint and fingerprint is not None
    return serial_matches and fingerprint_matches, entry


def move_to_quarantine(file_path, device_info=None, reason="security engines detected malicious content"):
    """Move a malicious file to the quarantine vault instead of deleting it.
    Saves metadata so the file can be identified and restored later."""
    os.makedirs(QUARANTINE_DIR, mode=0o700, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_name = os.path.basename(file_path)
    # Use timestamp + original name to avoid collisions
    quarantined_name = f"{timestamp}_{original_name}.quarantined"
    quarantined_path = os.path.join(QUARANTINE_DIR, quarantined_name)
    
    try:
        original_hash = calculate_sha256(file_path)
        shutil.copy2(file_path, quarantined_path)
        copied_hash = calculate_sha256(quarantined_path)
        if not original_hash or copied_hash != original_hash:
            raise IOError("quarantine copy hash verification failed")
        os.unlink(file_path)
        # Remove execute permissions from quarantined file
        os.chmod(quarantined_path, 0o400)
        source_removed = not os.path.exists(file_path)
        execute_disabled = (os.stat(quarantined_path).st_mode & 0o111) == 0
        if not source_removed or not execute_disabled:
            raise IOError("quarantine post-move verification failed")
    except Exception as e:
        try:
            if os.path.exists(quarantined_path):
                os.remove(quarantined_path)
        except OSError:
            pass
        raise e
    
    # Save metadata
    entry = {
        "quarantined_name": quarantined_name,
        "original_path": file_path,
        "quarantine_path": quarantined_path,
        "original_name": original_name,
        "timestamp": datetime.now().isoformat(),
        "device_vid_pid": f"{device_info.get('vid', '?')}:{device_info.get('pid', '?')}" if device_info else "unknown",
        "device_model": device_info.get("model", "Unknown") if device_info else "Unknown",
        "sha256": original_hash,
        "reason": reason,
        "hash_verified": copied_hash == original_hash,
        "source_removed": source_removed,
        "execute_disabled": execute_disabled,
        "verified": True,
    }
    
    log_entries = []
    if os.path.exists(QUARANTINE_LOG):
        try:
            with open(QUARANTINE_LOG, "r") as f:
                log_entries = json.load(f)
        except Exception:
            pass
    log_entries.append(entry)
    try:
        with open(QUARANTINE_LOG, "w") as f:
            json.dump(log_entries, f, indent=4)
    except Exception:
        pass
    publish_event("quarantine_updated", entry,
                  (device_info or {}).get("incident_id") if device_info else None)
    return quarantined_path


def list_quarantine():
    """List all files in the quarantine vault."""
    if not os.path.exists(QUARANTINE_LOG):
        print(Colors.YELLOW + "\n[*] Quarantine vault is empty.\n" + Colors.END)
        return []
    try:
        with open(QUARANTINE_LOG, "r") as f:
            entries = json.load(f)
    except Exception:
        print(Colors.RED + "[!] Could not read quarantine log." + Colors.END)
        return []
    
    if not entries:
        print(Colors.YELLOW + "\n[*] Quarantine vault is empty.\n" + Colors.END)
        return []
    
    print("\n" + "=" * 70)
    print(Colors.BOLD + Colors.CYAN + "           QUARANTINE VAULT            " + Colors.END)
    print("=" * 70)
    print(f"  Location: {QUARANTINE_DIR}")
    print(f"  Files:    {len(entries)}")
    print("-" * 70)
    
    for i, entry in enumerate(entries, 1):
        quarantined_file = os.path.join(QUARANTINE_DIR, entry["quarantined_name"])
        exists = os.path.exists(quarantined_file)
        status = Colors.GREEN + "STORED" + Colors.END if exists else Colors.RED + "MISSING" + Colors.END
        print(f"  {i}. {Colors.BOLD}{entry['original_name']}{Colors.END}")
        print(f"     Original Path : {entry['original_path']}")
        print(f"     Vault Path    : {entry.get('quarantine_path', quarantined_file)}")
        print(f"     SHA-256       : {entry.get('sha256', 'missing')}")
        print(f"     Reason        : {entry.get('reason', 'not recorded')}")
        print(f"     Quarantined   : {entry['timestamp']}")
        print(f"     Source Device : {entry.get('device_model', '?')} ({entry.get('device_vid_pid', '?')})")
        print(f"     Status        : {status}")
        print()
    
    print("=" * 70 + "\n")
    return entries


def _read_quarantine_entries_for_device(vid_pid):
    try:
        with open(QUARANTINE_LOG, "r", encoding="utf-8") as stream:
            entries = json.load(stream)
        return [item for item in entries if item.get("device_vid_pid") == vid_pid]
    except (OSError, json.JSONDecodeError):
        return []


def restore_from_quarantine(index):
    """Restore only after current hash, ClamAV, YARA and static checks pass."""
    if not os.path.exists(QUARANTINE_LOG):
        print(Colors.RED + "[!] No quarantine log found." + Colors.END)
        return False
    try:
        with open(QUARANTINE_LOG, "r") as f:
            entries = json.load(f)
    except Exception:
        print(Colors.RED + "[!] Could not read quarantine log." + Colors.END)
        return False
    
    if index < 1 or index > len(entries):
        print(Colors.RED + f"[!] Invalid index. Valid range: 1-{len(entries)}" + Colors.END)
        return False
    
    entry = entries[index - 1]
    quarantined_file = os.path.join(QUARANTINE_DIR, entry["quarantined_name"])
    
    if not os.path.exists(quarantined_file):
        print(Colors.RED + f"[!] Quarantined file not found: {entry['quarantined_name']}" + Colors.END)
        return False

    stored_hash = entry.get("sha256")
    current_hash = calculate_sha256(quarantined_file)
    if not stored_hash or current_hash != stored_hash:
        print(Colors.RED + "[!] Restore blocked: quarantine integrity hash mismatch." + Colors.END)
        return False
    print("[*] Rescanning quarantined content with current security engines...")
    _, findings, _ = scan_file_task(quarantined_file)
    security_findings = [item for item in findings if item.get("risk", 0) > 0]
    if security_findings:
        print(Colors.RED + "[!] Restore blocked: the file is still unsafe." + Colors.END)
        for finding in security_findings:
            print(f"    - {finding.get('issue', 'security finding')}")
        entry["last_restore_scan"] = datetime.now().isoformat()
        entry["last_restore_findings"] = security_findings
        with open(QUARANTINE_LOG, "w") as f:
            json.dump(entries, f, indent=4)
        return False
    
    original_path = entry["original_path"]
    try:
        os.makedirs(os.path.dirname(original_path), exist_ok=True)
        os.chmod(quarantined_file, 0o600)
        shutil.move(quarantined_file, original_path)
        print(Colors.GREEN + f"[+] Restored: {entry['original_name']} -> {original_path}" + Colors.END)
        
        # Remove entry from log
        entries.pop(index - 1)
        with open(QUARANTINE_LOG, "w") as f:
            json.dump(entries, f, indent=4)
        return True
    except Exception as e:
        print(Colors.RED + f"[!] Failed to restore: {e}" + Colors.END)
        return False


def delete_quarantine_entry(index):
    """Permanently delete one selected quarantine item and its metadata."""
    try:
        with open(QUARANTINE_LOG, "r") as stream:
            entries = json.load(stream)
    except (OSError, json.JSONDecodeError):
        print(Colors.RED + "[!] Could not read quarantine log." + Colors.END)
        return False
    if index < 1 or index > len(entries):
        print(Colors.RED + f"[!] Invalid index. Valid range: 1-{len(entries)}" + Colors.END)
        return False
    entry = entries[index - 1]
    path = os.path.join(QUARANTINE_DIR, entry["quarantined_name"])
    try:
        if os.path.exists(path):
            os.chmod(path, 0o600)
            os.remove(path)
        entries.pop(index - 1)
        with open(QUARANTINE_LOG, "w") as stream:
            json.dump(entries, stream, indent=4)
        print(Colors.GREEN + f"[+] Permanently deleted: {entry['original_name']}" + Colors.END)
        return True
    except OSError as exc:
        print(Colors.RED + f"[!] Delete failed: {exc}" + Colors.END)
        return False


def purge_quarantine():
    """Permanently delete all quarantined files."""
    if not os.path.exists(QUARANTINE_DIR):
        print(Colors.YELLOW + "[*] Quarantine vault is already empty." + Colors.END)
        return
    
    count = 0
    for f in os.listdir(QUARANTINE_DIR):
        fpath = os.path.join(QUARANTINE_DIR, f)
        if os.path.isfile(fpath):
            try:
                os.remove(fpath)
                count += 1
            except Exception:
                pass
    
    print(Colors.GREEN + f"[+] Quarantine vault purged. {count} file(s) permanently deleted." + Colors.END)


def show_history():
    """Print a formatted terminal table of all past scans from scan_log.json."""
    log_file = os.path.join(os.path.dirname(__file__), "scan_log.json")
    if not os.path.exists(log_file):
        print(Colors.YELLOW + "[*] No scan history log found." + Colors.END)
        return
        
    entries = []
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        pass
    except Exception as e:
        print(Colors.RED + f"[!] Failed to read scan history log: {e}" + Colors.END)
        return

    if not entries:
        print(Colors.YELLOW + "[*] Scan history log is empty." + Colors.END)
        return

    print(Colors.CYAN + Colors.BOLD + f"\n=== USB SCAN HISTORY ({len(entries)} entries) ===" + Colors.END)
    
    col_widths = {
        "time": 16,
        "device": 20,
        "file": 24,
        "risk": 8,
        "issue": 35
    }
    
    def truncate(s, w):
        s = str(s)
        return s[:w-3] + "..." if len(s) > w else s
        
    def format_row(time_str, device_str, file_str, risk_str, issue_str, colors=False):
        t_val = truncate(time_str, col_widths["time"]).ljust(col_widths["time"])
        d_val = truncate(device_str, col_widths["device"]).ljust(col_widths["device"])
        f_val = truncate(file_str, col_widths["file"]).ljust(col_widths["file"])
        
        if colors:
            if "HIGH" in risk_str:
                r_val = (Colors.RED + Colors.BOLD + risk_str + Colors.END).ljust(col_widths["risk"] + len(Colors.RED) + len(Colors.BOLD) + len(Colors.END))
            elif "MEDIUM" in risk_str:
                r_val = (Colors.YELLOW + Colors.BOLD + risk_str + Colors.END).ljust(col_widths["risk"] + len(Colors.YELLOW) + len(Colors.BOLD) + len(Colors.END))
            elif "LOW" in risk_str:
                r_val = (Colors.GREEN + risk_str + Colors.END).ljust(col_widths["risk"] + len(Colors.GREEN) + len(Colors.END))
            else:
                r_val = (Colors.BLUE + risk_str + Colors.END).ljust(col_widths["risk"] + len(Colors.BLUE) + len(Colors.END))
        else:
            r_val = truncate(risk_str, col_widths["risk"]).ljust(col_widths["risk"])
            
        i_val = truncate(issue_str, col_widths["issue"]).ljust(col_widths["issue"])
        
        return f"| {t_val} | {d_val} | {f_val} | {r_val} | {i_val} |"

    border = "+" + "-" * (col_widths["time"] + 2) + "+" + "-" * (col_widths["device"] + 2) + "+" + "-" * (col_widths["file"] + 2) + "+" + "-" * (col_widths["risk"] + 2) + "+" + "-" * (col_widths["issue"] + 2) + "+"
    
    print(border)
    print(format_row("Timestamp", "Device", "File Name", "Risk", "Primary Finding"))
    print(border)
    
    for entry in entries:
        ts = entry.get("timestamp", "")
        try:
            dt = datetime.fromisoformat(ts)
            ts_formatted = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            ts_formatted = ts[:16].replace("T", " ")
            
        dev = entry.get("device", "")
        if isinstance(dev, dict):
            vendor = dev.get("vendor", "").strip()
            model = dev.get("model", "").strip()
            if vendor and model:
                if vendor.lower() in model.lower():
                    dev_str = model
                else:
                    dev_str = f"{vendor} {model}"
            else:
                dev_str = model or vendor or "Unknown"
        else:
            dev_str = os.path.basename(str(dev))
            if not dev_str:
                dev_str = str(dev)
                
        filepath = entry.get("file", "")
        filename = os.path.basename(str(filepath))
        if not filename:
            filename = str(filepath)
            
        risk = entry.get("risk_level", "CLEAN")
        
        findings = entry.get("findings", [])
        issue_str = ""
        if findings:
            issue_str = findings[0].get("issue", "")
            
        print(format_row(ts_formatted, dev_str, filename, risk, issue_str, colors=True))
        
    print(border)
    print()


# ==========================================
# DESKTOP / SOUND ALERT SYSTEM
# ==========================================
def _play_tone(frequency=800, duration_ms=300, repeat=1):
    """Generate and play a tone through the user's audio session.
    Uses paplay (PulseAudio) or pw-play (PipeWire) under the original user so it works when running as sudo.
    Falls back to aplay, then terminal bell if nothing works.
    Runs in a background thread so it never blocks the main scan flow."""
    def _do_play():
        try:
            import wave
            sample_rate = 44100
            samples = int(sample_rate * duration_ms / 1000)
            
            for _ in range(repeat):
                # Generate WAV in memory
                buf = io.BytesIO()
                with wave.open(buf, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    for i in range(samples):
                        val = int(32767 * math.sin(2 * math.pi * frequency * i / sample_rate))
                        wf.writeframes(struct.pack('<h', val))
                wav_data = buf.getvalue()
                
                played = False
                sudo_user = os.environ.get("SUDO_USER")
                sudo_uid = os.environ.get("SUDO_UID", "1000")
                
                tmp_wav = "/tmp/_usb_scanner_alert.wav"
                with open(tmp_wav, "wb") as f:
                    f.write(wav_data)
                os.chmod(tmp_wav, 0o644)
                
                # Determine user home directory for config/cookie access
                user_home = f"/home/{sudo_user}" if sudo_user else "/home/pi"
                if sudo_user:
                    try:
                        import pwd
                        user_home = pwd.getpwnam(sudo_user).pw_dir
                    except Exception:
                        pass
                
                attempts = []
                if sudo_user:
                    xdg = f"/run/user/{sudo_uid}"
                    dbus = f"unix:path=/run/user/{sudo_uid}/bus"
                    pipewire_sock = f"unix:/run/user/{sudo_uid}/pulse/native"
                    
                    # 1. paplay (standard auto-detection with full env)
                    if shutil.which("paplay"):
                        attempts.append({
                            "name": "paplay (auto env)",
                            "cmd": ["sudo", "-u", sudo_user, "env",
                                    f"XDG_RUNTIME_DIR={xdg}",
                                    f"DBUS_SESSION_BUS_ADDRESS={dbus}",
                                    f"HOME={user_home}",
                                    f"USER={sudo_user}",
                                    "paplay", tmp_wav]
                        })
                        # 2. paplay (explicit socket)
                        attempts.append({
                            "name": "paplay (explicit socket)",
                            "cmd": ["sudo", "-u", sudo_user, "env",
                                    f"PULSE_SERVER={pipewire_sock}",
                                    f"XDG_RUNTIME_DIR={xdg}",
                                    f"DBUS_SESSION_BUS_ADDRESS={dbus}",
                                    f"HOME={user_home}",
                                    f"USER={sudo_user}",
                                    "paplay", tmp_wav]
                        })
                    
                    # 3. pw-play (PipeWire native player)
                    if shutil.which("pw-play"):
                        attempts.append({
                            "name": "pw-play",
                            "cmd": ["sudo", "-u", sudo_user, "env",
                                    f"XDG_RUNTIME_DIR={xdg}",
                                    f"DBUS_SESSION_BUS_ADDRESS={dbus}",
                                    f"HOME={user_home}",
                                    f"USER={sudo_user}",
                                    "pw-play", tmp_wav]
                        })
                    
                    # 4. aplay as desktop user (Pulse-ALSA plugin)
                    if shutil.which("aplay"):
                        attempts.append({
                            "name": "aplay (user)",
                            "cmd": ["sudo", "-u", sudo_user, "env",
                                    f"XDG_RUNTIME_DIR={xdg}",
                                    f"DBUS_SESSION_BUS_ADDRESS={dbus}",
                                    f"HOME={user_home}",
                                    f"USER={sudo_user}",
                                    "aplay", "-q", tmp_wav]
                        })
                        
                    # 5. aplay as root (direct ALSA hardware interface)
                    if shutil.which("aplay"):
                        attempts.append({
                            "name": "aplay (root)",
                            "cmd": ["aplay", "-q", tmp_wav]
                        })
                else:
                    # Running natively as user (not under sudo)
                    if shutil.which("paplay"):
                        attempts.append({"name": "paplay (native)", "cmd": ["paplay", tmp_wav]})
                    if shutil.which("pw-play"):
                        attempts.append({"name": "pw-play (native)", "cmd": ["pw-play", tmp_wav]})
                    if shutil.which("aplay"):
                        attempts.append({"name": "aplay (native)", "cmd": ["aplay", "-q", tmp_wav]})

                for attempt in attempts:
                    try:
                        result = subprocess.run(attempt["cmd"], capture_output=True, timeout=6)
                        err = result.stderr.decode(errors='replace').strip()
                        if os.environ.get("USB_SCANNER_AUDIO_DEBUG") == "1" and not PROMPT_ACTIVE.is_set():
                            print(f"[DEBUG AUDIO] {attempt['name']} returncode={result.returncode} stderr={err}")
                        if result.returncode == 0:
                            played = True
                            break
                    except Exception as e:
                        if os.environ.get("USB_SCANNER_AUDIO_DEBUG") == "1" and not PROMPT_ACTIVE.is_set():
                            print(f"[DEBUG AUDIO] {attempt['name']} exception: {e}")
                
                # Terminal bell fallback
                if not played:
                    if os.environ.get("USB_SCANNER_AUDIO_DEBUG") == "1" and not PROMPT_ACTIVE.is_set():
                        print("[DEBUG AUDIO] All methods failed, using terminal bell")
                    print("\a", end="", flush=True)
                
                if repeat > 1:
                    time.sleep(0.15)
        except Exception as e:
            if os.environ.get("USB_SCANNER_AUDIO_DEBUG") == "1" and not PROMPT_ACTIVE.is_set():
                print(f"[DEBUG AUDIO] Play tone root exception: {e}")
            for _ in range(repeat):
                print("\a", end="", flush=True)
    threading.Thread(target=_do_play, daemon=True).start()


def _desktop_notify(title, message, urgency="normal", icon="dialog-warning"):
    """Send a desktop notification via notify-send.
    Runs as the original user (not root) so it appears on the desktop."""
    def _do_notify():
        try:
            sudo_user = os.environ.get("SUDO_USER")
            sudo_uid = os.environ.get("SUDO_UID")
            cmd = ["notify-send", f"--urgency={urgency}", f"--icon={icon}", title, message]
            env = os.environ.copy()
            if sudo_user and sudo_uid:
                cmd = ["sudo", "-u", sudo_user] + cmd
                env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{sudo_uid}/bus"
            subprocess.run(cmd, env=env, capture_output=True, timeout=5)
        except Exception:
            pass  # Notifications are best-effort
    threading.Thread(target=_do_notify, daemon=True).start()


def notify_incident(usb_info, verdict, json_path, pdf_path):
    verdict = normalize_verdict(verdict)
    """Queue post-report email without allowing notification errors to affect scanning."""
    incident_id = usb_info.get("incident_id") or f"{usb_info.get('vid','unknown')}-{usb_info.get('pid','unknown')}"
    publish_event("report_ready", {"verdict": verdict, "json_path": json_path,
                                   "pdf_path": pdf_path, "device": usb_info}, incident_id)
    try:
        queue_incident_email(incident_id, verdict, json_path, pdf_path)
    except Exception as exc:
        print(Colors.YELLOW + f"[EMAIL] Could not queue incident notification: {exc}" + Colors.END)
    finally:
        publish_event("incident_completed", {"verdict": verdict, "json_path": json_path,
                                              "pdf_path": pdf_path}, incident_id)


def alert_threat_detected(device_model, threat_count=0):
    """Fire alerts when malware or a dangerous device is detected."""
    _play_tone(frequency=1000, duration_ms=200, repeat=3)  # Urgent triple beep
    msg = f"Malware detected on {device_model}!" if threat_count else f"Dangerous device blocked: {device_model}"
    if threat_count:
        msg += f" ({threat_count} malicious file(s) found)"
    _desktop_notify("USB THREAT DETECTED", msg, urgency="critical", icon="dialog-error")


def alert_device_clean(device_model):
    """Fire a short success alert when a device passes the scan."""
    _play_tone(frequency=600, duration_ms=150, repeat=1)  # Short friendly beep
    _desktop_notify("USB Device Safe", f"{device_model} passed all security checks.", urgency="low", icon="dialog-information")


def alert_hid_blocked(device_name):
    """Fire alerts when an unknown HID keyboard is blocked."""
    _play_tone(frequency=1200, duration_ms=150, repeat=5)  # Rapid high-pitched alarm
    msg = f"Unknown keyboard blocked: {device_name}"
    _desktop_notify("HID ATTACK BLOCKED", msg, urgency="critical", icon="dialog-error")


def format_vid_pid(vid, pid):
    """Normalize vendor/product IDs to the whitelist key format."""
    return f"{str(vid).lower()}:{str(pid).lower()}"


def is_whitelisted_hid(vid, pid):
    return format_vid_pid(vid, pid) in HID_WHITELIST


def usbguard_device(vid, pid, port=None, serial=None, timeout=1.0):
    """Return USBGuard's newest matching record and advertised interfaces."""
    target = format_vid_pid(vid, pid)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            result = subprocess.run(
                ["usbguard", "list-devices"], capture_output=True, text=True, timeout=1
            )
            matches = []
            for line in result.stdout.splitlines():
                if f" id {target} " not in f" {line.lower()} ":
                    continue
                match = re.match(r"\s*(\d+):\s+(\w+)", line)
                interfaces = set(re.findall(r"\b([0-9a-fA-F]{2}):[0-9a-fA-F*]{2}:[0-9a-fA-F*]{2}\b", line))
                if match:
                    port_match = re.search(r'via-port\s+"([^"]+)"', line)
                    serial_match = re.search(r'serial\s+"([^"]*)"', line)
                    hash_match = re.search(r'hash\s+"([^"]*)"', line)
                    record = {"id": match.group(1), "state": match.group(2),
                              "interfaces": {value.lower() for value in interfaces}, "line": line,
                              "port": port_match.group(1) if port_match else None,
                              "serial": serial_match.group(1) if serial_match else None}
                    record["hash"] = hash_match.group(1) if hash_match else ""
                    if port and record["port"] and record["port"] != port:
                        continue
                    if serial and serial != "Unknown" and record["serial"] and record["serial"] != serial:
                        continue
                    matches.append(record)
            if matches:
                return matches[-1]
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return None
        time.sleep(0.1)
    return None


def usbguard_set_state(device_id, allow):
    """Change only the current USBGuard device instance; never persist trust."""
    if not device_id:
        return False
    action = "allow-device" if allow else "block-device"
    try:
        result = subprocess.run(["usbguard", action, str(device_id)], capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False

# Bus type 0003 = USB HID.
# 001e = platform/HDMI, 0011 = i8042/PS2, 0019 = GPIO.
# Non-USB buses can NEVER be USB HID attack devices — filter them out.
USB_BUS_TYPE = "0003"

# ==========================================
# STATIC ANALYSIS ENGINE (INTEGRATED)
# ==========================================
def calculate_risk(findings):
    total_risk = sum(f.get('risk', 0) for f in findings)
    if total_risk >= 8:
        return "HIGH"
    elif total_risk >= 4:
        return "MEDIUM"
    elif total_risk > 0:
        return "LOW"
    return "CLEAN"

def calc_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = collections.Counter(data)
    total = len(data)
    return -sum((c / total) * math.log2(c / total) for c in counts.values() if c)

def extract_strings(data: bytes, min_len: int = 6) -> list:
    ascii_re = re.compile(rb"[\x20-\x7e]{%d,}" % min_len)
    return [s.decode("ascii", errors="ignore") for s in ascii_re.findall(data)]

def static_analyze(file_path: str) -> list:
    '''
    Perform deep static analysis without execution.
    Returns a list of findings (dictionaries with 'issue' and 'risk' score).
    '''
    findings = []
    try:
        file_size = os.path.getsize(file_path)
        # 3. Skip very large files (>100MB) to prevent freezing
        if file_size > 100 * 1024 * 1024:
            findings.append({"issue": "File too large (>100MB)", "risk": 1})
            return findings
            
        # Extension-based Type
        ext = os.path.splitext(file_path)[1].lower()
        
        with open(file_path, 'rb') as f:
            head = f.read(4)
            f.seek(0)
            data = f.read()

        yara_findings = yara_scan_bytes(data, os.path.basename(file_path))
        for finding in yara_findings:
            findings.append({
                "issue": finding.issue,
                "risk": finding.risk,
                "rule": finding.rule,
                "tags": finding.tags,
                "meta": finding.meta,
            })
            
        # 1. File Type Validation (Magic Bytes Anti-evasion)
        is_exe = head[:2] == b"MZ"
        is_zip = head[:4] == b"PK\x03\x04"
        is_elf = head[:4] == b"\x7fELF"
        
        if is_exe and ext not in ['.exe', '.dll', '.sys', '.scr', '.ocx', '.cpl']:
            findings.append({"issue": f"Magic byte mismatch: EXE disguised as {ext}", "risk": 8})
        if is_zip and ext not in ['.zip', '.jar', '.apk', '.docx', '.xlsx']:
            if ext in ['.jpg', '.png', '.mp3', '.pdf']:
                findings.append({"issue": f"Magic byte mismatch: ZIP/Archive disguised as {ext}", "risk": 7})

        # Entropy Check (packed code)
        entropy = calc_entropy(data)
        if entropy > 7.4:
            findings.append({"issue": f"Very high entropy ({entropy:.2f}) - packed/encrypted", "risk": 7})
        elif entropy > 6.8:
            findings.append({"issue": f"Elevated entropy ({entropy:.2f}) - obfuscation", "risk": 3})

        # 7. Safe Archive Handling
        if is_zip or ext in ['.zip', '.apk', '.jar']:
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    entries = zf.infolist()
                    if len(entries) > 2000:
                        findings.append({"issue": "Archive contains abnormally high file count (>2000)", "risk": 4})
                    
                    suspicious_exts = {'.exe', '.bat', '.ps1', '.py', '.sh', '.vbs', '.js', '.cmd', '.dll'}
                    sus_files = []
                    total_uncompressed = 0
                    
                    for e in entries[:2000]:  # limit inspection depth
                        total_uncompressed += e.file_size
                        e_ext = os.path.splitext(e.filename)[1].lower()
                        if e_ext in suspicious_exts:
                            sus_files.append(e.filename)
                            
                        # Double extension check
                        parts = e.filename.split('.')
                        if len(parts) > 2 and f".{parts[-1].lower()}" in suspicious_exts:
                            findings.append({"issue": f"Double extension in archive: {e.filename}", "risk": 8})
                            
                    if total_uncompressed > 500 * 1024 * 1024:  # 500MB extraction limit bomb
                        findings.append({"issue": "Possible zip bomb (huge uncompressed ratio)", "risk": 6})
                        
                    if sus_files:
                        findings.append({"issue": f"Archive payload contains executables/scripts: {', '.join(sus_files[:3])}", "risk": 6})
            except zipfile.BadZipFile:
                findings.append({"issue": "Corrupt or password-protected archive", "risk": 4})
            except Exception:
                pass

        # Content Decoding
        is_script = ext in ['.bat', '.ps1', '.sh', '.py', '.vbs', '.js', '.cmd']
        text_content = ""
        if is_script:
            text_content = data.decode("utf-8", errors="ignore")
        elif is_exe or is_elf:
            text_content = "\n".join(extract_strings(data))
            
        if text_content:
            # Dangerous Strings Risk Weighting
            dangerous_patterns = [
                (r"powershell(\.exe)?\s+(?:-w\s+hidden|-enc|-nop|-ep\s+bypass)", 9, "PowerShell stealth execution"),
                (r"nc\s+.*-e\s+/bin/(?:sh|bash)", 10, "Netcat reverse shell"),
                (r"bash\s+-i\s+>&", 10, "Bash interactive reverse shell"),
                (r"curl\s+.*\|\s*(?:bash|sh|python)", 10, "Pipe-to-shell remote execution"),
                (r"Invoke-Expression|IEX\s*\(", 8, "PowerShell arbitrary code execution (IEX)"),
                (r"cmd(?:\.exe)?\s+/c", 6, "CMD shell execution"),
                (r"WScript\.Shell", 7, "VBScript Win32 shell execution"),
                (r"VirtualAllocEx|WriteProcessMemory", 8, "Process Injection APIs"),
                (r"SetWindowsHookEx", 8, "Keylogging APIs")
            ]
            for pat, risk, desc in dangerous_patterns:
                if re.search(pat, text_content, re.IGNORECASE):
                    findings.append({"issue": desc, "risk": risk})
            
            # 6. Base64 Payload Safe Detection & Decoding
            b64_blobs = re.findall(r"(?:[A-Za-z0-9+/]{40,}={0,2})", text_content)
            if b64_blobs:
                findings.append({"issue": f"Encoded Base64 strings detected ({len(b64_blobs)})", "risk": 4})
                for blob in b64_blobs:
                    try:
                        decoded = base64.b64decode(blob).decode('utf-8', errors='ignore')
                        if re.search(r"Invoke-|powershell|cmd\.exe|WScript", decoded, re.IGNORECASE):
                            findings.append({"issue": "Base64 decoded payload contains malicious execution commands", "risk": 8})
                    except Exception:
                        pass
                        
            # 5. URL and IP Extraction
            urls = re.findall(r"https?://[^\s\"'>]{4,200}", text_content, re.IGNORECASE)
            ips = re.findall(r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b", text_content)
            
            private_ip_re = re.compile(r"^(?:127\.|10\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.|0\.0\.0\.0|255\.)")
            external_ips = [ip for ip in set(ips) if not private_ip_re.match(ip)]
            unique_urls = list(set(urls))
            
            if external_ips:
                findings.append({"issue": f"IPv4 Addresses Extracted: {', '.join(external_ips[:3])}", "risk": 6})
            if unique_urls:
                findings.append({"issue": f"URLs (HTTP/HTTPS) Extracted: {', '.join(unique_urls[:3])}", "risk": 4})
                
    except Exception as e:
         findings.append({"issue": f"Static analysis error: {str(e)}", "risk": 0})
         
    return findings

# ==========================================
# DATABASE CONFIG
# ==========================================
def check_hash(sha256_hash):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT signature, severity FROM malware_hashes WHERE sha256_hash = ?",
            (sha256_hash.lower(),)
        )
        result = cursor.fetchone()
        conn.close()
        return {"signature": result[0], "severity": result[1]} if result else None
    except Exception as e:
        print(f"Database error: {e}")
        return None

def calculate_sha256(file_path):
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception:
        return None


def _clamav_command():
    """Prefer clamdscan when available, otherwise fall back to clamscan."""
    clamdscan = shutil.which("clamdscan")
    daemon_ready = any(os.path.exists(path) for path in (
        "/run/clamav/clamd.ctl", "/var/run/clamav/clamd.ctl", "/run/clamd.scan/clamd.sock"
    ))
    if clamdscan and daemon_ready:
        return [clamdscan, "--fdpass", "--no-summary"]
    clamscan = shutil.which("clamscan")
    if clamscan:
        return [clamscan, "--no-summary"]
    return None


def clamav_scan_file(file_path):
    """Return ClamAV findings for a single file, or an empty list when clean/unavailable."""
    command = _clamav_command()
    if not command:
        return []
    try:
        result = subprocess.run(
            command + [file_path],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
        return [{"issue": f"ClamAV scan skipped: {e}", "risk": 5}]

    output = "\n".join(part for part in [result.stdout, result.stderr] if part).strip()
    if result.returncode > 1 and os.path.basename(command[0]) == "clamdscan":
        fallback = shutil.which("clamscan")
        if fallback:
            try:
                result = subprocess.run([fallback, "--no-summary", file_path], capture_output=True,
                                        text=True, timeout=120)
                output = "\n".join(part for part in [result.stdout, result.stderr] if part).strip()
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
                return [{"issue": f"ClamAV daemon and fallback scan failed: {e}", "risk": 5}]
    if result.returncode == 1:
        signature = "infected file"
        for line in output.splitlines():
            if " FOUND" in line:
                signature = line.rsplit(":", 1)[-1].replace("FOUND", "").strip()
                break
        return [{"issue": f"ClamAV MALWARE DETECTED: {signature}", "risk": 15}]
    if result.returncode > 1:
        return [{"issue": f"ClamAV scan error: {output[:160]}", "risk": 5}]
    return []

# ==========================================
# STORAGE MONITOR
# ==========================================
def find_mount_point(device_node):
    try:
        with open("/proc/mounts") as f:
            for line in f:
                parts = line.split()
                if parts[0] == device_node:
                    return parts[1].replace("\\040", " ")
    except Exception:
        pass
    return None

def try_mount_with_udisks(device_node):
    """Ask udisks to mount the partition when desktop auto-mount is slow or missing."""
    try:
        cmd = ["udisksctl", "mount", "-b", device_node, "--no-user-interaction"]
        sudo_user = os.environ.get("SUDO_USER")
        if sudo_user:
            cmd = ["sudo", "-u", sudo_user] + cmd
            
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        for line in result.stdout.splitlines():
            if " at " in line:
                return line.split(" at ", 1)[1].strip().rstrip(".")
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def wait_for_mount(device_node, timeout=15):
    for attempt in range(timeout):
        mount = find_mount_point(device_node)
        if mount and os.path.exists(mount):
            return mount
        if attempt == 4:
            mount = try_mount_with_udisks(device_node)
            if mount and os.path.exists(mount):
                return mount
        time.sleep(1)
    return None


def is_root_user():
    return hasattr(os, "geteuid") and os.geteuid() == 0


def unmount_storage(device_node=None, mount_path=None):
    """Best-effort unmount used to keep unsafe storage unavailable."""
    success = False
    commands = []
    if device_node and shutil.which("udisksctl"):
        commands.append(["udisksctl", "unmount", "-b", device_node, "--no-user-interaction"])
    if mount_path:
        commands.append(["umount", mount_path])

    for command in commands:
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                success = True
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            continue
    return success


def quarantine_mount_path(device_node):
    safe_name = os.path.basename(device_node).replace("/", "_")
    return os.path.join("/tmp", "usb_scanner_quarantine", safe_name)


def verify_isolation_mount(mount_path):
    """Verify the kernel mount options before exposing files to the scanner."""
    try:
        result = subprocess.run(
            ["findmnt", "-n", "-o", "OPTIONS", "--target", mount_path],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return False
        options = {item.strip().lower() for item in result.stdout.strip().split(",")}
        return {"ro", "nosuid", "nodev", "noexec"}.issubset(options)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def mount_for_quarantine_scan(device_node):
    """
    Mount a USB partition read-only with execution/device bits disabled for scanning.
    Returns (mount_path, is_quarantine_mount).
    """
    existing_mount = find_mount_point(device_node)
    if existing_mount:
        print(Colors.YELLOW + f"[*] USB auto-mounted at {existing_mount}; unmounting before safety scan." + Colors.END)
        unmount_storage(device_node, existing_mount)

    if not is_root_user():
        print(Colors.RED +
              "[!] Refusing storage analysis without a privileged isolated mount." +
              Colors.END)
        return None, False

    mount_path = quarantine_mount_path(device_node)
    try:
        os.makedirs(mount_path, mode=0o700, exist_ok=True)
        result = subprocess.run(
            ["mount", "-o", "ro,nosuid,nodev,noexec", device_node, mount_path],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if result.returncode == 0 and verify_isolation_mount(mount_path):
            print(Colors.GREEN + f"[+] Quarantine-mounted read-only at {mount_path}" + Colors.END)
            ACTIVE_ISOLATION_MOUNTS.add(mount_path)
            return mount_path, True
        if result.returncode == 0:
            print(Colors.RED + "[!] Mount options could not be verified; keeping storage blocked." + Colors.END)
            unmount_storage(mount_path=mount_path)
        print(Colors.YELLOW + f"[!] Quarantine mount failed: {result.stderr.strip()}" + Colors.END)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
        print(Colors.YELLOW + f"[!] Quarantine mount error: {e}" + Colors.END)

    # Never fall back to an unverified desktop mount: an unsafe mount would
    # defeat the read-only/noexec isolation guarantee.
    return None, False


def release_storage_for_use(device_node, mount_path, is_quarantine_mount):
    """Unmount scan mount and remount normally only after a clean verdict."""
    if is_quarantine_mount:
        unmount_storage(mount_path=mount_path)
        ACTIVE_ISOLATION_MOUNTS.discard(mount_path)
    if shutil.which("udisksctl"):
        mount = try_mount_with_udisks(device_node)
        if mount:
            print(Colors.GREEN + f"[✓] Device accepted and mounted for user access at {mount}" + Colors.END)
            return True
    print(Colors.GREEN + "[✓] Device accepted. It is safe to mount/use normally." + Colors.END)
    return True


def keep_storage_blocked(device_node, mount_path, is_quarantine_mount):
    """Remove unsafe storage from the filesystem view."""
    if mount_path:
        unmount_storage(device_node, mount_path)
    if is_quarantine_mount:
        ACTIVE_ISOLATION_MOUNTS.discard(mount_path)
        try:
            os.rmdir(mount_path)
        except OSError:
            pass
    print(Colors.RED + f"[!] Device rejected. {device_node} is not mounted for user access." + Colors.END)


# ==========================================
# MTP / PHONE STORAGE SUPPORT
# ==========================================
def is_mtp_or_ptp_device(device):
    """Best-effort udev detection for phones that expose files through MTP/PTP."""
    checks = [
        device.get("ID_MTP_DEVICE"),
        device.get("ID_MEDIA_PLAYER"),
        device.get("ID_PTP_DEVICE"),
        device.get("MTP_NO_PROBE"),
    ]
    if any(str(value).lower() in {"1", "true", "yes"} for value in checks if value):
        return True

    searchable = " ".join(
        str(value).lower()
        for value in [
            device.get("ID_USB_CLASS_FROM_DATABASE"),
            device.get("ID_USB_INTERFACES"),
            device.get("ID_MODEL"),
            device.get("ID_VENDOR"),
            device.get("ID_USB_DRIVER"),
        ]
        if value
    )
    return any(token in searchable for token in ("mtp", "ptp", "still imaging", "media player"))


def _gvfs_mtp_roots():
    uid = os.getuid() if hasattr(os, "getuid") else None
    candidates = []
    if uid is not None:
        candidates.append(f"/run/user/{uid}/gvfs")
    xdg_runtime = os.environ.get("XDG_RUNTIME_DIR")
    if xdg_runtime:
        candidates.append(os.path.join(xdg_runtime, "gvfs"))
    return [path for path in candidates if os.path.isdir(path)]


def find_existing_mtp_mounts():
    mounts = []
    for gvfs_root in _gvfs_mtp_roots():
        try:
            for name in os.listdir(gvfs_root):
                path = os.path.join(gvfs_root, name)
                if name.startswith(("mtp:", "gphoto2:")) and os.path.isdir(path):
                    mounts.append(path)
        except OSError:
            continue
    return mounts


def try_mount_with_gio(device):
    """Ask GVFS/GIO to mount the MTP/PTP device if the desktop stack is available."""
    if not shutil.which("gio"):
        return []

    before = set(find_existing_mtp_mounts())
    device_file = device.device_node or device.get("DEVNAME")
    mount_targets = []
    if device_file:
        mount_targets.append(device_file)

    # Some desktops need a generic MTP volume activation instead of a dev node.
    mount_targets.extend(["mtp://", "gphoto2://"])

    for target in mount_targets:
        try:
            subprocess.run(
                ["gio", "mount", target],
                capture_output=True,
                text=True,
                timeout=20,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            continue

        after = set(find_existing_mtp_mounts())
        new_mounts = list(after - before)
        if new_mounts:
            return new_mounts
    return list(set(find_existing_mtp_mounts()) - before)


def try_mount_with_fuse_mtp(device):
    """Mount the first available MTP device with simple-mtpfs or jmtpfs when installed."""
    helper = shutil.which("simple-mtpfs") or shutil.which("jmtpfs")
    if not helper:
        return None

    vid = str(device.get("ID_VENDOR_ID", "unknown")).lower()
    pid = str(device.get("ID_MODEL_ID", "unknown")).lower()
    mount_root = os.path.join("/tmp", "usb_scanner_mtp")
    mount_path = os.path.join(mount_root, f"{vid}_{pid}")
    try:
        os.makedirs(mount_path, mode=0o700, exist_ok=True)
        result = subprocess.run(
            [helper, mount_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and os.path.isdir(mount_path):
            return mount_path
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def wait_for_mtp_mount(device, timeout=20):
    """Return accessible MTP/PTP mount paths for a connected phone."""
    for attempt in range(timeout):
        mounts = find_existing_mtp_mounts()
        if mounts:
            return mounts

        if attempt == 3:
            mounts = try_mount_with_gio(device)
            if mounts:
                return mounts

        if attempt == 7:
            mount = try_mount_with_fuse_mtp(device)
            if mount:
                return [mount]

        time.sleep(1)
    return []

def scan_file_task(path, cancel_event=None):
    findings = []
    if cancel_event and cancel_event.is_set():
        raise DeviceRemovedDuringAnalysis("DEVICE REMOVED DURING ANALYSIS")
    sha = calculate_sha256(path)
    if sha:
        result = check_hash(sha)
        if result:
            findings.append({"issue": f"DB MALWARE DETECTED: {result['signature']}", "risk": 15})

    if cancel_event and cancel_event.is_set():
        raise DeviceRemovedDuringAnalysis("DEVICE REMOVED DURING ANALYSIS")
    findings.extend(clamav_scan_file(path))
            
    try:
        sa_findings = static_analyze(path)
        if sa_findings:
            findings.extend(sa_findings)
    except Exception as e:
        findings.append({"issue": f"Analysis error: {str(e)}", "risk": 0})
        
    return path, findings, sha


@functools.lru_cache(maxsize=1)
def scan_engine_signature():
    yara_hash = calculate_sha256(str(Path(__file__).parent / "backend" / "scanner" / "yara_rules.yar"))
    clam_version = "unavailable"
    scanner = shutil.which("clamscan")
    if scanner:
        try:
            result = subprocess.run([scanner, "--version"], capture_output=True, text=True, timeout=10)
            clam_version = (result.stdout or result.stderr).strip()
        except Exception:
            pass
    return hashlib.sha256(f"{yara_hash}|{clam_version}|risk-v2".encode()).hexdigest()


def scan_file_task_incremental(path, previous_sha=None, cache_valid=False, cancel_event=None):
    if cancel_event and cancel_event.is_set():
        raise DeviceRemovedDuringAnalysis("DEVICE REMOVED DURING ANALYSIS")
    sha = calculate_sha256(path)
    if cache_valid and previous_sha and sha == previous_sha:
        return path, [], sha, True
    result_path, findings, result_sha = scan_file_task(path, cancel_event=cancel_event)
    return result_path, findings, result_sha, False

def scan_storage(mount_path, device_info=None, previous_entry=None, cancel_event=None):
    print(Colors.CYAN + Colors.BOLD + "\n[ SCANNING ] High-Speed Threaded FS Analysis...\n" + Colors.END)
    
    master_risk_score = 0
    malware_detected = False
    all_files = []
    malicious_files = []
    file_hash_materials = []
    file_hashes = []
    cached_files = 0
    folder_count = 0
    previous_hashes = {
        item.get("relative_path"): item.get("sha256")
        for item in (previous_entry or {}).get("file_hashes", []) if isinstance(item, dict)
    }
    cache_valid = bool(previous_entry and not previous_entry.get("force_rescan") and
                       previous_entry.get("engine_signature") == scan_engine_signature())
    
    try:
        for root, dirs, files in os.walk(mount_path):
            if cancel_event and cancel_event.is_set():
                raise DeviceRemovedDuringAnalysis("DEVICE REMOVED DURING ANALYSIS")
            folder_count += len(dirs)
            for file in files:
                all_files.append(os.path.join(root, file))
    except DeviceRemovedDuringAnalysis:
        raise
    except Exception as e:
        print(f"Directory read error: {e}")
        
    log_file = os.path.join(os.path.dirname(__file__), "scan_log.json")
    
    total_files = len(all_files)
    processed = 0
    
    # 9. Performance Optimization: ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_path = {}
        for path in all_files:
            relative = os.path.relpath(path, mount_path)
            future = executor.submit(scan_file_task_incremental, path, previous_hashes.get(relative),
                                     cache_valid, cancel_event)
            future_to_path[future] = path
        
        for future in concurrent.futures.as_completed(future_to_path):
            if cancel_event and cancel_event.is_set():
                for queued in future_to_path:
                    queued.cancel()
                raise DeviceRemovedDuringAnalysis("DEVICE REMOVED DURING ANALYSIS")
            path = future_to_path[future]
            processed += 1
            if total_files > 0:
                # Reserve the beginning/end of the live gauge for descriptor,
                # policy, risk and report stages surrounding the file scan.
                progress = 35 + int((processed / total_files) * 50)
                emit_ui_event("scan_progress", {
                    "incident_id": (device_info or {}).get("incident_id") if isinstance(device_info, dict) else None,
                    "progress": progress,
                    "message": f"Scanning {os.path.basename(path)}...",
                })
                
            try:
                # 4. Timeout Protection (3 seconds)
                res_path, findings, sha, reused_cache = future.result(timeout=3.0)
                if reused_cache:
                    cached_files += 1
            except concurrent.futures.TimeoutError:
                findings = [{"issue": "File scanning timed out (>3s limit); scan is incomplete", "risk": 5}]
                sha = None
            except Exception as e:
                findings = [{"issue": f"File scan failed; scan is incomplete: {e}", "risk": 5}]
                sha = None
            
            if sha:
                relative_path = os.path.relpath(path, mount_path)
                file_hash_materials.append(f"{relative_path}:{sha}")
                file_hashes.append({"path": path, "relative_path": relative_path, "sha256": sha})

            if not findings:
                continue

            # 2. Risk Scoring Engine Integration
            risk_level = calculate_risk(findings)
            r_score = sum(f.get('risk', 0) for f in findings)
            master_risk_score += r_score
            
            if risk_level in ["HIGH", "MEDIUM"]:
                malware_detected = True
                malicious_files.append(path)
            
            # Print cleanly
            if risk_level == "HIGH":
                color = Colors.RED
            elif risk_level == "MEDIUM":
                color = Colors.YELLOW
            else:
                color = Colors.CYAN
                
            print(f"\n{color}{Colors.BOLD}[*] {risk_level} RISK FILE: {path}{Colors.END}")
            for f in findings:
                print(f"{color}  -> {f['issue']} (Risk: {f.get('risk')}){Colors.END}")
                publish_event("finding_detected", {
                    "path": path, "severity": risk_level,
                    "finding": f["issue"], "risk": f.get("risk", 0),
                }, (device_info or {}).get("incident_id") if isinstance(device_info, dict) else None)
                
            # 8. Structured Logging System
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "device": device_info if device_info else mount_path,
                "file": path,
                "risk_level": risk_level,
                "risk_score": r_score,
                "findings": findings
            }
            try:
                with open(log_file, "a") as lf:
                    lf.write(json.dumps(log_entry) + "\n")
            except Exception:
                pass

    print(" " * 80, end="\r")
    storage_fingerprint = None
    if file_hash_materials:
        digest_input = "\n".join(sorted(file_hash_materials)).encode("utf-8")
        storage_fingerprint = hashlib.sha256(digest_input).hexdigest()
    print(f"[*] Incremental scan: {cached_files} unchanged cached file(s), "
          f"{max(0, total_files - cached_files)} fully scanned file(s)")
    if isinstance(device_info, dict):
        inventory = device_info.setdefault("file_inventory", {
            "files": 0, "folders": 0, "executables": 0,
            "archives": 0, "hidden": 0,
        })
        inventory["files"] += total_files
        inventory["folders"] += folder_count
        inventory["executables"] += sum(
            1 for path in all_files if Path(path).suffix.lower() in
            {".exe", ".dll", ".com", ".bat", ".cmd", ".sh", ".bin", ".appimage"}
        )
        inventory["archives"] += sum(
            1 for path in all_files if Path(path).suffix.lower() in
            {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"}
        )
        inventory["hidden"] += sum(
            1 for path in all_files if any(part.startswith(".") for part in Path(path).parts)
        )
        coverage = device_info.setdefault("scan_coverage", {
            "total_files": 0, "cached_files": 0, "fully_scanned_files": 0,
            "engine_signature": scan_engine_signature(),
        })
        coverage["total_files"] += total_files
        coverage["cached_files"] += cached_files
        coverage["fully_scanned_files"] += max(0, total_files - cached_files)
        coverage["cache_reuse_allowed"] = cache_valid
    return master_risk_score, malware_detected, malicious_files, storage_fingerprint, file_hashes

# ==========================================
# THREAT LEVEL LABEL
# ==========================================
def threat_level(score):
    if score >= 15:
        return Colors.RED    + Colors.BOLD + "HIGH"   + Colors.END
    elif score >= 8:
        return Colors.YELLOW + Colors.BOLD + "MEDIUM" + Colors.END
    elif score > 0:
        return Colors.GREEN  + Colors.BOLD + "LOW"    + Colors.END
    else:
        return Colors.BLUE   + Colors.BOLD + "CLEAN"  + Colors.END

# ==========================================
# USB STORAGE HANDLER
# ==========================================
def analyze_descriptors(device):
    def sysattr(name, default="Unknown"):
        try:
            value = device.attributes.get(name)
            return value.decode(errors="replace") if isinstance(value, bytes) else (str(value) if value else default)
        except Exception:
            return default
    return {
        "vendor":     device.get("ID_VENDOR",                "Unknown"),
        "model":      device.get("ID_MODEL",                 "Unknown"),
        "serial":     device.get("ID_SERIAL_SHORT",          "Unknown"),
        "vid":        device.get("ID_VENDOR_ID") or sysattr("idVendor"),
        "pid":        device.get("ID_MODEL_ID") or sysattr("idProduct"),
        "subsystem":  device.properties.get("SUBSYSTEM"),
        "usb_class":  device.get("ID_USB_CLASS_FROM_DATABASE","Unknown"),
        "usb_driver": device.get("ID_USB_DRIVER",            "Unknown"),
    }

def normalize_device_type(value):
    """Map freeform user input to the device categories we understand."""
    if not value:
        return "other"

    normalized = value.strip().lower()
    aliases = {
        "storage": {"storage", "usb storage", "drive", "disk", "pendrive", "flash", "flash drive"},
        "scanner": {"scanner", "scan", "imaging", "image scanner"},
        "keyboard": {"keyboard", "kbd"},
        "mouse": {"mouse", "pointer"},
        "phone": {"phone", "mobile", "smartphone", "mtp", "ptp"},
        "printer": {"printer"},
        "camera": {"camera"},
        "hub": {"hub"},
        "other": {"other", "unknown", "something else"},
    }
    for canonical, options in aliases.items():
        if normalized == canonical or normalized in options:
            return canonical
    return normalized

DEVICE_TYPE_OPTIONS = [
    ("storage", "Storage / USB Drive"),
    ("scanner", "Scanner"),
    ("keyboard", "Keyboard"),
    ("mouse", "Mouse"),
    ("phone", "Phone / MTP / PTP"),
    ("printer", "Printer"),
    ("camera", "Camera"),
    ("hub", "Hub / Adapter"),
    ("other", "Other / Unknown"),
]

def _read_menu_key():
    """Read a single key from the terminal, including arrow keys."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch1 = sys.stdin.read(1)
        if ch1 == "\x1b":
            ch2 = sys.stdin.read(1)
            ch3 = sys.stdin.read(1)
            return ch1 + ch2 + ch3
        return ch1
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def _render_device_type_menu(selected_index, usb_info):
    os.system("clear")
    print(Colors.CYAN + "\n[ DEVICE TYPE CHECK ]" + Colors.END)
    print(f"  Vendor : {usb_info['vendor']}")
    print(f"  Model  : {usb_info['model']}")
    print(f"  VID:PID: {usb_info['vid']}:{usb_info['pid']}")
    print()
    print(Colors.BOLD + "  Use ↑ / ↓ to choose the device type, then press Enter." + Colors.END)
    print()

    for index, (_, label) in enumerate(DEVICE_TYPE_OPTIONS):
        prefix = "➜" if index == selected_index else " "
        if index == selected_index:
            print(Colors.YELLOW + Colors.BOLD + f"  {prefix} {label}" + Colors.END)
        else:
            print(f"  {prefix} {label}")

def prompt_declared_device_type(usb_info):
    """Ask the user to pick the inserted device type using arrow keys."""
    if UI_MODE:
        resp = prompt_ui("declare_device_type", {"device": usb_info})
        if resp and "answer" in resp:
            return normalize_device_type(resp["answer"])
        return "other"
        
    selected_index = 0

    if not sys.stdin.isatty():
        print(Colors.CYAN + "\n[ DEVICE TYPE CHECK ]" + Colors.END)
        print(f"  Vendor : {usb_info['vendor']}")
        print(f"  Model  : {usb_info['model']}")
        print(f"  VID:PID: {usb_info['vid']}:{usb_info['pid']}")
        declared = input(Colors.YELLOW + "  What device are you inserting? " + Colors.END).strip()
        return normalize_device_type(declared)

    while True:
        _render_device_type_menu(selected_index, usb_info)
        key = _read_menu_key()

        if key == "\x1b[A":
            selected_index = (selected_index - 1) % len(DEVICE_TYPE_OPTIONS)
        elif key == "\x1b[B":
            selected_index = (selected_index + 1) % len(DEVICE_TYPE_OPTIONS)
        elif key in ("\r", "\n"):
            return DEVICE_TYPE_OPTIONS[selected_index][0]
        elif key in ("q", "Q"):
            return DEVICE_TYPE_OPTIONS[-1][0]

def detect_actual_device_type(device, usb_info):
    """Infer the device type from udev metadata and mountability."""
    class_name = (usb_info.get("usb_class") or "Unknown").lower()
    guard_interfaces = usb_info.get("guard_interfaces", set())

    if "03" in guard_interfaces:
        model_text = f"{usb_info.get('vendor', '')} {usb_info.get('model', '')}".lower()
        if (str(device.get("ID_INPUT_MOUSE", "")).lower() in {"1", "true", "yes"} or
                str(device.get("ID_INPUT_TOUCHPAD", "")).lower() in {"1", "true", "yes"} or
                any(word in model_text for word in ("mouse", "pointer", "touchpad", "trackball"))):
            return "mouse"
        return "keyboard"
    if "08" in guard_interfaces:
        return "storage"

    if is_mtp_or_ptp_device(device):
        return "phone"

    if usb_device_has_storage(device):
        return "storage"

    if any(keyword in class_name for keyword in ("scanner", "imaging")):
        return "scanner"
    if any(keyword in class_name for keyword in ("keyboard", "human interface", "hid")):
        return "keyboard"
    if "mouse" in class_name:
        return "mouse"
    if "printer" in class_name:
        return "printer"
    if "camera" in class_name:
        return "camera"
    if "hub" in class_name:
        return "hub"

    return "other"

def log_device_decision(device_info, declared_type, detected_type, decision, reason, risk_score=0):
    """Write a device-level decision entry to the scan history log."""
    log_file = os.path.join(os.path.dirname(__file__), "scan_log.json")
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "device": device_info,
        "file": None,
        "risk_level": calculate_risk([{ "risk": risk_score }]) if risk_score else ("HIGH" if decision == "BLOCKED" else "LOW"),
        "risk_score": risk_score,
        "findings": [{"issue": reason, "risk": risk_score}] if reason else [],
        "declared_device_type": declared_type,
        "detected_device_type": detected_type,
        "decision": decision,
    }
    try:
        with open(log_file, "a") as lf:
            lf.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass

def structural_rules(descriptor):
    risk, flags = 0, []
    if descriptor["serial"] == "Unknown":
        risk += 1
        flags.append("Missing serial number")
    return risk, flags


def usb_device_has_storage(device):
    """True if this USB device exposes a storage partition."""
    context = pyudev.Context()
    device_sys_path = getattr(device, "sys_path", None)
    for block_device in context.list_devices(subsystem="block"):
        if block_device.device_type == "partition":
            parent = block_device.find_parent("usb", "usb_device")
            if parent and getattr(parent, "sys_path", None) == device_sys_path:
                return True
    return False


def print_whitelisted_hid_report(usb_info, vid_pid):
    print("\n" + "━" * 60)
    print(Colors.BOLD + Colors.GREEN + "        WHITELISTED HID DEVICE — TRUSTED        " + Colors.END)
    print("━" * 60)
    print(f" Time           : {datetime.now()}")
    print(f" Device         : {HID_WHITELIST[vid_pid]}")
    print(f" VID:PID        : {vid_pid}")
    print(f" Vendor         : {usb_info['vendor']}")
    print(f" Model          : {usb_info['model']}")
    print(f"\n✓ Device is WHITELISTED — no storage to scan, will not be blocked")
    print("━" * 60 + "\n")
    print(Colors.GREEN + "[✓] Device analysis complete. Ready for next device..." + Colors.END)

def generate_pdf_report(usb_info, base_risk, storage_risk, hid_risk, policy_risk, total_risk, malware_detected, flags, sanitized=False, declared_device_type="unknown", detected_device_type="unknown", stage="final", verdict=None):
    verdict = normalize_verdict(verdict)
    if FPDF is None:
        print(Colors.YELLOW +
              "[!] PDF skipped — install dependencies: .venv/bin/pip install -r requirements.txt" +
              Colors.END)
        return
    try:
        pdf_dir = os.path.join(os.path.dirname(__file__), "reports")
        os.makedirs(pdf_dir, mode=0o755, exist_ok=True)
            
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        incident_id = usb_info.get("incident_id")
        filename = (f"incident_{incident_id}.pdf" if incident_id else
                    f"{stage}_scan_report_{usb_info['vid']}_{usb_info['pid']}_{timestamp_str}.pdf")
        filepath = os.path.join(pdf_dir, filename)
        
        pdf = FPDF()
        pdf.add_page()
        report_original_total = usb_info.get("original_risk_breakdown", {}).get("total", total_risk)
        report_final_total = usb_info.get("final_risk_breakdown", {}).get("total", total_risk)
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            
            # 1. Header Banner
            pdf.set_fill_color(41, 128, 185) # Blue header
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", 'B', 18)
            pdf.cell(0, 15, " USB Security Scan Report ", 0, 1, 'C', fill=True)
            pdf.ln(5)
            
            # 2. Threat Level Banner
            level_str = verdict or "CLEAN"
            verdict_colors = {
                "CLEAN": (39, 174, 96), "TRUSTED": (22, 160, 133),
                "SUSPICIOUS": (243, 156, 18), "DANGEROUS": (192, 57, 43),
                "INCOMPLETE": (127, 140, 141),
            }
            fill_r, fill_g, fill_b = verdict_colors.get(level_str, (39, 174, 96))
            if verdict:
                pass
            elif sanitized:
                level_str = "HIGH RISK - DEVICE SANITIZED (ALLOWED)"
                fill_r, fill_g, fill_b = 241, 196, 15 # Yellow/Orange
            elif malware_detected or total_risk >= 15:
                level_str = "HIGH RISK - DEVICE BLOCKED"
                fill_r, fill_g, fill_b = 192, 57, 43 # Red
            elif total_risk >= 8:
                level_str = "MEDIUM RISK - DEVICE BLOCKED"
                fill_r, fill_g, fill_b = 211, 84, 0 # Orange/Yellow
            elif total_risk > 0:
                level_str = "LOW RISK"
                fill_r, fill_g, fill_b = 243, 156, 18 # Yellow
            
            pdf.set_fill_color(fill_r, fill_g, fill_b)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", 'B', 14)
            pdf.cell(0, 12, f" Overall Threat Level: {level_str} ", 0, 1, 'C', fill=True)
            pdf.ln(10)
            
            # Restore colors for text
            pdf.set_text_color(0, 0, 0)
            
            # 3. Summary Paragraph
            pdf.set_font("Helvetica", '', 11)
            pdf.multi_cell(0, 6, f"This report was automatically generated on {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}. "
                                 "It summarizes the hardware, storage, and behavioral analysis of the connected USB device. "
                                 f"Original risk was {report_original_total}; final risk is {report_final_total}. "
                                 "The verdict is based on category evidence, scan coverage, trust, and remediation state.")
            pdf.ln(8)
            
            # 4. Device Information Table
            pdf.set_fill_color(236, 240, 241) # Light gray for headers
            pdf.set_font("Helvetica", 'B', 12)
            pdf.cell(0, 8, " Device Identity", border="B", ln=1)
            pdf.ln(2)
            
            col1 = 50
            col2 = 140
            
            info_rows = [
                ("Vendor / Model", f"{usb_info['vendor']} / {usb_info['model']}"),
                ("Hardware ID (VID:PID)", f"{usb_info['vid']}:{usb_info['pid']}"),
                ("Serial Number", usb_info['serial']),
                ("USB Class", usb_info['usb_class'])
            ]
            
            for label, val in info_rows:
                pdf.set_font("Helvetica", 'B', 10)
                pdf.cell(col1, 8, label, border=0)
                pdf.set_font("Helvetica", '', 10)
                pdf.cell(col2, 8, val, border=0, ln=1)

            pdf.set_font("Helvetica", 'B', 10)
            pdf.cell(col1, 8, "Declared Type")
            pdf.set_font("Helvetica", '', 10)
            pdf.cell(col2, 8, declared_device_type.title(), ln=1)

            pdf.set_font("Helvetica", 'B', 10)
            pdf.cell(col1, 8, "Detected Type")
            pdf.set_font("Helvetica", '', 10)
            pdf.cell(col2, 8, detected_device_type.title(), ln=1)
                
            pdf.ln(6)
            
            # 5. Risk Breakdown
            pdf.set_font("Helvetica", 'B', 12)
            pdf.cell(0, 8, " Risk Score Breakdown", border="B", ln=1)
            pdf.ln(2)
            
            pdf.set_font("Helvetica", 'B', 10)
            pdf.cell(col1, 8, "Hardware Anomalies:")
            pdf.set_font("Helvetica", '', 10)
            pdf.cell(col2, 8, str(base_risk), ln=1)
            
            pdf.set_font("Helvetica", 'B', 10)
            pdf.cell(col1, 8, "Storage / Filesystem:")
            pdf.set_font("Helvetica", '', 10)
            pdf.cell(col2, 8, str(storage_risk), ln=1)
            
            pdf.set_font("Helvetica", 'B', 10)
            pdf.cell(col1, 8, "HID / Keystroke Injection:")
            pdf.set_font("Helvetica", '', 10)
            pdf.cell(col2, 8, str(hid_risk), ln=1)

            pdf.set_font("Helvetica", 'B', 10)
            pdf.cell(col1, 8, "Policy / Type Mismatch:")
            pdf.set_font("Helvetica", '', 10)
            pdf.cell(col2, 8, str(policy_risk), ln=1)
            
            pdf.ln(2)
            pdf.set_draw_color(0, 0, 0)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(2)
            
            pdf.set_font("Helvetica", 'B', 11)
            pdf.cell(col1, 8, "Final Risk Score:")
            pdf.set_font("Helvetica", 'B', 11)
            pdf.cell(col2, 8, str(report_final_total), ln=1)

            detailed = usb_info.get("risk_breakdown", {})
            original_breakdown = usb_info.get("original_risk_breakdown") or detailed
            final_breakdown = usb_info.get("final_risk_breakdown") or detailed
            if detailed:
                pdf.ln(3)
                pdf.set_font("Helvetica", 'B', 9)
                pdf.cell(52, 7, "Category")
                pdf.cell(35, 7, "Original", align="C")
                pdf.cell(35, 7, "Final", align="C")
                pdf.cell(45, 7, "Category cap", align="C", ln=1)
                caps = {"hardware": 15, "trust": 20, "interface": 30,
                        "behavior": 15, "storage": 30, "nvd": 20,
                        "malware": 70}
                pdf.set_font("Helvetica", '', 9)
                for label in ("hardware", "trust", "interface", "behavior", "storage", "nvd", "malware"):
                    pdf.cell(52, 6, label.title())
                    pdf.cell(35, 6, str(original_breakdown.get(label, 0)), align="C")
                    pdf.cell(35, 6, str(final_breakdown.get(label, 0)), align="C")
                    pdf.cell(45, 6, str(caps[label]), align="C", ln=1)
                pdf.set_font("Helvetica", 'B', 9)
                pdf.cell(52, 7, "Unified total")
                pdf.cell(35, 7, str(original_breakdown.get("total", total_risk)), align="C")
                pdf.cell(35, 7, str(final_breakdown.get("total", total_risk)), align="C")
                pdf.cell(45, 7, str(final_breakdown.get("severity", "UNKNOWN")), align="C", ln=1)

            nvd = usb_info.get("nvd", {})
            if nvd:
                pdf.ln(4)
                pdf.set_font("Helvetica", 'B', 11)
                pdf.cell(0, 7, " NVD Vulnerability Intelligence", border="B", ln=1)
                pdf.set_font("Helvetica", '', 9)
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(0, 6, (
                    f"Status: {nvd.get('status')} | CPE confidence: {nvd.get('confidence')} | "
                    f"CPE: {nvd.get('cpe') or 'not mapped'}\n"
                    f"CVEs: {len(nvd.get('cves', []))} | Highest CVSS: {nvd.get('highest_cvss', 0)} | "
                    f"KEV: {'YES' if nvd.get('kev') else 'NO'} | Risk contribution: {nvd.get('risk', 0)}\n"
                    f"Coverage: {nvd.get('message', 'not evaluated')}"
                ))

            coverage = usb_info.get("scan_coverage", {})
            if coverage:
                pdf.ln(4)
                pdf.set_x(pdf.l_margin)
                pdf.set_font("Helvetica", 'B', 11)
                pdf.cell(0, 7, " Scan Coverage and Engine Cache", border="B", ln=1)
                pdf.set_font("Helvetica", '', 9)
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(0, 6, (
                    f"Files observed: {coverage.get('total_files', 0)} | "
                    f"Fully scanned: {coverage.get('fully_scanned_files', 0)} | "
                    f"Verified cached: {coverage.get('cached_files', 0)}\n"
                    f"Cache reuse allowed: {'YES' if coverage.get('cache_reuse_allowed') else 'NO'} | "
                    f"Engine signature: {coverage.get('engine_signature', 'unavailable')}"
                ))

            fingerprints = usb_info.get("fingerprint_comparison", {})
            if fingerprints:
                pdf.ln(4)
                pdf.set_x(pdf.l_margin)
                pdf.set_font("Helvetica", 'B', 11)
                pdf.cell(0, 7, " Fingerprint and Trust Comparison", border="B", ln=1)
                pdf.set_font("Helvetica", '', 8)
                for label in ("hardware", "interfaces", "storage"):
                    pdf.set_x(pdf.l_margin)
                    pdf.multi_cell(0, 5, f"{label.title()}: {fingerprints.get(label) or 'not applicable'}")
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(0, 5, f"Trust invalidated: {'YES' if fingerprints.get('trust_invalidated') else 'NO'}")

            timing = usb_info.get("timing", {})
            session = usb_info.get("port_session", {})
            if timing or session:
                pdf.ln(4)
                pdf.set_x(pdf.l_margin)
                pdf.set_font("Helvetica", 'B', 11)
                pdf.cell(0, 7, " Incident Timing and Session", border="B", ln=1)
                pdf.set_font("Helvetica", '', 9)
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(0, 6, (
                    f"Detected: {timing.get('detected_at', session.get('started_at', 'unknown'))}\n"
                    f"Completed: {timing.get('completed_at', 'unknown')} | "
                    f"Analysis: {timing.get('analysis_duration_ms', 'n/a')} ms | "
                    f"Enforcement: {timing.get('enforcement_latency_ms', session.get('enforcement_latency_ms', 'n/a'))} ms\n"
                    f"Physical port: {session.get('port', usb_info.get('physical_port', 'unknown'))} | "
                    f"Suppressed re-enumerations: {session.get('re_enumeration_count', 0)}"
                ))

            quarantine_records = usb_info.get("quarantine_records", [])
            if quarantine_records:
                pdf.ln(4)
                pdf.set_x(pdf.l_margin)
                pdf.set_font("Helvetica", 'B', 11)
                pdf.cell(0, 7, " Quarantine Evidence", border="B", ln=1)
                pdf.set_font("Helvetica", '', 8)
                for record in quarantine_records[-10:]:
                    pdf.set_x(pdf.l_margin)
                    pdf.multi_cell(0, 5, (
                        f"Original: {record.get('original_path', 'unknown')}\n"
                        f"Vault: {record.get('quarantine_path', 'unknown')}\n"
                        f"SHA-256: {record.get('sha256', 'missing')} | Reason: {record.get('reason', 'not recorded')}"
                    ))
            
            if sanitized:
                pdf.ln(4)
                pdf.set_x(pdf.l_margin)
                pdf.set_fill_color(255, 243, 205)
                pdf.set_text_color(133, 100, 4)
                pdf.set_font("Helvetica", 'B', 10)
                pdf.multi_cell(0, 8, "[SANITIZED] Malware was detected and moved to the verified quarantine vault. The cleaned remainder was allowed by policy.", border=1, align='C', fill=True)
                pdf.set_text_color(0, 0, 0)
            
            pdf.ln(6)
            
            # 6. Malware Warning if applicable
            if malware_detected:
                pdf.set_x(pdf.l_margin)
                pdf.set_fill_color(255, 235, 238) # Light red
                pdf.set_text_color(192, 57, 43)
                pdf.set_font("Helvetica", 'B', 12)
                pdf.multi_cell(0, 10, "[!] MALWARE OR MALICIOUS SCRIPTS DETECTED ON DEVICE", border=1, align='C', fill=True)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(6)

            if declared_device_type != "unknown" and detected_device_type != "unknown":
                pdf.set_x(pdf.l_margin)
                pdf.set_fill_color(255, 248, 225)
                pdf.set_text_color(133, 100, 4)
                pdf.set_font("Helvetica", 'B', 11)
                pdf.multi_cell(
                    0,
                    8,
                    f"[TYPE CHECK] Declared: {declared_device_type.title()} | Detected: {detected_device_type.title()}",
                    border=1,
                    align='C',
                    fill=True,
                )
                pdf.set_text_color(0, 0, 0)
                pdf.ln(4)
            
            # 7. Detailed Findings
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", 'B', 12)
            pdf.cell(0, 8, " Detailed Findings & Flags", border="B", ln=1)
            pdf.ln(4)
            
            pdf.set_font("Helvetica", '', 10)
            if not flags and not malware_detected:
                pdf.cell(0, 8, "No anomalies or malicious indicators were found on this device.", ln=1)
            else:
                flags_text = "\n".join(f"- {f}" for f in flags)
                if flags_text:
                    pdf.set_x(pdf.l_margin)
                    pdf.multi_cell(0, 6, flags_text)
            
            pdf.ln(15)
            # Footer
            pdf.set_text_color(127, 140, 141)
            pdf.set_font("Helvetica", 'I', 9)
            pdf.set_x(pdf.l_margin)
            pdf.cell(0, 10, "End of automated security report.", 0, 1, 'C')
        
        pdf.output(filepath)
        print(Colors.GREEN + f"[+] PDF Report Generated: {filepath}" + Colors.END)
        return filepath
    except Exception as e:
        print(Colors.RED + f"[!] Failed to generate PDF: {e}" + Colors.END)
        return None


def generate_json_report(usb_info, **data):
    """Write machine-readable scan state for diagnostics and future dashboard use."""
    report_dir = os.path.join(os.path.dirname(__file__), "reports")
    os.makedirs(report_dir, mode=0o755, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    incident_id = usb_info.get("incident_id")
    filename = (f"incident_{incident_id}.json" if incident_id else
                f"scan_{usb_info['vid']}_{usb_info['pid']}_{timestamp}.json")
    path = os.path.join(report_dir, filename)
    if "verdict" in data:
        data["verdict"] = normalize_verdict(data["verdict"])
    payload = {"timestamp": datetime.now().isoformat(), "device": dict(usb_info), **data}
    payload["device"]["guard_interfaces"] = sorted(payload["device"].get("guard_interfaces", []))
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, default=str)
    print(f"[+] JSON Report Generated: {path}")
    return path


def normalized_verdict(allowed=False, trusted=False, incomplete=False,
                       malware=False, total_risk=0, remediated=False):
    return incident_verdict(
        allowed=allowed, trusted=trusted, incomplete=incomplete,
        malware=malware, total_risk=total_risk, remediated=remediated,
    )


VALID_VERDICTS = {"CLEAN", "TRUSTED", "SUSPICIOUS", "DANGEROUS", "INCOMPLETE"}


def normalize_verdict(value):
    """Keep reports, notifications, and dashboard state on one verdict set."""
    value = str(value or "").upper().strip()
    return value if value in VALID_VERDICTS else "INCOMPLETE"


def blocked_incident_breakdown(session, detected_type):
    """Build an explainable category score for pre-authorization blocks."""
    evidence = " ".join(session.get("findings", [])).lower()
    is_hid = detected_type in {"keyboard", "hid-fingerprint-changed", "badusb-multi-stage"}
    is_composite = "composite" in detected_type or "storage interfaces" in evidence
    hardware = 5 if any(token in evidence for token in ("identity changed", "attack-platform")) else 0
    trust = 20
    interface = 30 if is_hid or "hid" in evidence else 15
    behavior = 15 if (session.get("re_enumeration_count", 0) or
                      "multi-stage" in detected_type or "attack-platform" in evidence) else 0
    storage = 15 if is_composite else 0
    return risk_breakdown(hardware=hardware, trust=trust, interface=interface,
                          behavior=behavior, storage=storage, nvd=0)


def report_preblocked_device(usb_info, detected_type, reason, risk=15):
    """Record an enforcement decision without delaying the enforcement worker."""
    port = usb_info.get("physical_port", usb_info.get("port", "unknown"))
    session = port_session(port)
    session["last_usb_info"] = dict(usb_info)
    session["detected_type"] = detected_type
    session["risk"] = max(session.get("risk", 0), risk)
    if reason not in session["findings"]:
        session["findings"].append(reason)
    if session.get("enforcement_recorded"):
        session["re_enumeration_count"] = session.get("re_enumeration_count", 0) + 1
        return False
    blocked_at = session.get("blocked_monotonic") or time.monotonic()
    latency_ms = round((blocked_at - session["detected_monotonic"]) * 1000, 1)
    session["enforcement_latency_ms"] = max(0, latency_ms)
    print(Colors.RED + Colors.BOLD +
          f"[ENFORCED] Device blocked in {session['enforcement_latency_ms']:.1f} ms; report queued." +
          Colors.END)
    # Persist minimal evidence immediately; the background renderer enriches
    # and overwrites this same incident JSON, so a crash cannot erase the block.
    immediate_info = dict(usb_info)
    immediate_info["incident_id"] = session["incident_id"]
    generate_json_report(
        immediate_info, stage="enforced", decision="BLOCKED",
        verdict="DANGEROUS" if session["risk"] >= 40 else "SUSPICIOUS",
        detected_type=detected_type, total_risk=session["risk"],
        flags=list(session["findings"]),
        timing={"enforcement_latency_ms": session["enforcement_latency_ms"]},
    )
    session["enforcement_recorded"] = True
    queue_session_report(port)
    return True


def queue_session_report(port, final=False):
    """Coalesce rapid re-enumerations into one asynchronously generated incident."""
    session = PORT_SESSIONS.get(port)
    if not session or not session.get("last_usb_info"):
        return
    with REPORT_LOCK:
        pending = REPORT_PENDING.setdefault(port, {"generation": 0})
        old_timer = pending.get("timer")
        if old_timer and old_timer.is_alive() and not final:
            # Refresh evidence without extending the deadline. A device that
            # re-enumerates continuously must still receive a prompt report.
            pending["session"] = json.loads(json.dumps(session, default=str))
            return
        if old_timer:
            old_timer.cancel()
        pending["generation"] += 1
        generation = pending["generation"]
        pending["final"] = pending.get("final", False) or final
        pending["session"] = json.loads(json.dumps(session, default=str))
        timer = threading.Timer(0.1 if final else 2.0, _produce_session_report,
                                args=(port, generation))
        timer.daemon = True
        pending["timer"] = timer
        timer.start()


def _produce_session_report(port, generation):
    """Generate one consolidated incident after the port becomes quiet."""
    try:
        with REPORT_LOCK:
            pending = REPORT_PENDING.get(port)
            if not pending or pending["generation"] != generation:
                return
            session = pending.get("session")
            REPORT_PENDING.pop(port, None)
        if not session or not session.get("last_usb_info"):
            return
        live_session = PORT_SESSIONS.get(port)
        if live_session:
            live_session["report_generated"] = True
        usb_info = dict(session["last_usb_info"])
        usb_info["port_session"] = dict(session)
        flags = list(session.get("findings", []))
        flags.append(f"Suppressed re-enumerations: {session.get('re_enumeration_count', 0)}")
        detected_type = session.get("detected_type", "unknown")
        breakdown = blocked_incident_breakdown(session, detected_type)
        risk = max(15, session.get("risk", 15), breakdown["total"])
        usb_info["risk_breakdown"] = breakdown
        usb_info["nvd"] = {
            "status": "not_evaluated_fast_path", "cves": [], "risk": 0,
            "message": "Network intelligence never delays HID enforcement",
        }
        usb_info["fingerprint_comparison"] = {
            "hardware": usb_info.get("hardware_fingerprint"),
            "interfaces": usb_info.get("interface_fingerprint"),
            "storage": None, "trust_invalidated": True,
        }
        usb_info["timing"] = {
            "detected_at": session.get("started_at"),
            "completed_at": datetime.now().isoformat(),
            "enforcement_latency_ms": session.get("enforcement_latency_ms"),
        }
        with REPORT_RENDER_LOCK:
            json_path = generate_json_report(
                usb_info, stage="blocked", decision="BLOCKED",
                verdict="DANGEROUS" if risk >= 40 else "SUSPICIOUS",
                detected_type=detected_type, total_risk=risk, flags=flags,
                risk_breakdown=breakdown,
                fingerprint_comparison={
                    "hardware": usb_info.get("hardware_fingerprint"),
                    "interfaces": usb_info.get("interface_fingerprint"),
                    "usbguard_hash": usb_info.get("usbguard_hash"),
                },
                nvd={"status": "not_evaluated_fast_path", "cves": [],
                     "message": "Network intelligence never delays HID enforcement"},
                enforcement_latency_ms=session.get("enforcement_latency_ms"),
                reporting_completed_at=datetime.now().isoformat(),
                device_connected=session.get("connected", False),
            )
            verdict = "DANGEROUS" if risk >= 40 else "SUSPICIOUS"
            pdf_path = generate_pdf_report(
                usb_info, 0, 0, risk, 0, risk, False, flags,
                declared_device_type="automatic", detected_device_type=detected_type,
                stage="blocked", verdict=verdict)
        notify_incident(usb_info, verdict, json_path, pdf_path)
        print(f"[REPORT] Consolidated incident completed for physical port {port}")
        print("[READY] Incident completed. Monitoring for the next USB device...")
    except Exception as exc:
        print(Colors.RED + f"[REPORT] Background report failed for {port}: {exc}" + Colors.END)


def report_trusted_hid(usb_info, trust_status, nvd_result=None):
    if nvd_result is None:
        nvd_result = NVDClient().lookup(format_vid_pid(usb_info.get("vid"), usb_info.get("pid")))
    findings = [
        f"Trust record: {trust_status}",
        f"Hardware fingerprint: {usb_info.get('hardware_fingerprint', 'unavailable')}",
        f"Interface fingerprint: {usb_info.get('interface_fingerprint', 'unavailable')}",
        f"Interfaces: {', '.join(sorted(usb_info.get('guard_interfaces', [])))}",
        f"NVD status: {nvd_result.status} - {nvd_result.message}",
    ]
    if usb_info.get("serial") in {None, "", "Unknown"}:
        findings.append("Device provides no unique serial; descriptor/interface evidence is required")
    for cve in (nvd_result.cves or [])[:10]:
        findings.append(f"{cve['id']} CVSS {cve['cvss']} {cve['severity']}: {cve['description']}")
    scores = risk_breakdown(nvd=nvd_result.risk)
    usb_info["nvd"] = nvd_result.to_dict()
    usb_info["risk_breakdown"] = scores
    json_path = generate_json_report(usb_info, stage="final", decision="TRUSTED_HID_ALLOWED",
                         verdict="TRUSTED", risk_breakdown=scores,
                         fingerprint_comparison={
                             "hardware": usb_info.get("hardware_fingerprint"),
                             "interfaces": usb_info.get("interface_fingerprint"),
                             "trust_status": trust_status,
                         }, nvd=nvd_result.to_dict(),
                         findings=findings, recommendations=[
                             "Block if descriptor or interface fingerprint changes",
                             "Review vendor firmware guidance for confirmed CVEs",
                             "Do not interpret trusted HID as a malware-clean storage verdict",
                         ])
    pdf_path = generate_pdf_report(usb_info, 0, 0, 0, 0, scores["total"], False, findings,
                                   declared_device_type="automatic", detected_device_type="trusted-hid",
                                   stage="trusted_hid", verdict="TRUSTED")
    notify_incident(usb_info, "TRUSTED", json_path, pdf_path)
    print("Decision       : TRUSTED HID - ALLOWED")
    print(f"Risk breakdown : {scores}")
    print("This is an identity/trust verdict, not a storage malware-clean verdict.")

def handle_usb_device(device):
    device_id = getattr(device, "sys_path", None) or getattr(device, "sys_name", "unknown")
    physical_port = getattr(device, "sys_name", "unknown")
    PORT_SESSION_GENERATION[physical_port] = PORT_SESSION_GENERATION.get(physical_port, 0) + 1
    existing_session = PORT_SESSIONS.get(physical_port)
    # Establish the incident before the first lifecycle event so the dashboard
    # never creates a second, device-path-only active record.
    session = existing_session or port_session(physical_port)
    if (existing_session and existing_session.get("blocked") and
            existing_session.get("enforcement_recorded")):
        existing_session["connected"] = True
        existing_session["re_enumeration_count"] = existing_session.get("re_enumeration_count", 0) + 1
        vid = str(device.get("ID_VENDOR_ID", "unknown")).lower()
        pid = str(device.get("ID_MODEL_ID", "unknown")).lower()
        identity = f"{vid}:{pid}"
        if identity not in existing_session["vid_pid_history"]:
            existing_session["vid_pid_history"].append(identity)
        deauthorize_usb_device(physical_port, quiet=True)
        if not existing_session.get("report_generated"):
            queue_session_report(physical_port)
        count = existing_session["re_enumeration_count"]
        print(Colors.RED +
              f"[BLOCKED] Re-enumeration #{count} suppressed on locked port {physical_port}" +
              Colors.END)
        ACTIVE_DEVICE_PATHS.discard(getattr(device, "sys_path", None))
        return
    port_session(physical_port)["connected"] = True
    cancel_event = threading.Event()
    DEVICE_CANCEL_EVENTS[device_id] = cancel_event
    set_device_state(device_id, "DETECTED")
    try:
        if device_id in DISCONNECTED_DEVICE_PATHS:
            set_device_state(device_id, "INCOMPLETE", "device removed before analysis began")
            return
        load_whitelist()
        load_storage_whitelist()
        usb_info = analyze_descriptors(device)
        usb_info["physical_port"] = physical_port
        vid_pid = format_vid_pid(usb_info["vid"], usb_info["pid"])
        trust_status = "not evaluated"
        usb_info["incident_id"] = session["incident_id"]
        # Publish identity immediately after descriptor analysis. Fast-blocked
        # HID devices may return before the full storage workflow, but the live
        # dashboard must still show the physical device and its incident.
        emit_ui_event("device_detected", {
            "incident_id": usb_info.get("incident_id"),
            "device_id": str(device_id),
            "vid": usb_info.get("vid", ""), "pid": usb_info.get("pid", ""),
            "name": usb_info.get("model", "USB Device"),
            "manufacturer": usb_info.get("vendor", "Unknown"),
            "serial": usb_info.get("serial", "Unknown"),
            "usb_version": usb_info.get("usb_version", "2.0"),
        })
        emit_ui_event("scan_progress", {
            "incident_id": usb_info.get("incident_id"), "progress": 5,
            "message": "USB descriptors captured; enforcing isolation policy…",
        })
        session["connected"] = True
        previous_identity = session["vid_pid_history"][-1] if session["vid_pid_history"] else None
        if vid_pid not in session["vid_pid_history"]:
            session["vid_pid_history"].append(vid_pid)
        if previous_identity and previous_identity != vid_pid:
            lock_port_session(physical_port,
                              f"USB identity changed on one port: {previous_identity} -> {vid_pid}", 15)
        model_indicator = f"{usb_info.get('vendor', '')} {usb_info.get('model', '')}".lower()
        if any(name in model_indicator for name in ("p4wnp1", "rubber_ducky", "rubber ducky",
                                                     "bash_bunny", "bash bunny", "badusb", "digispark")):
            lock_port_session(physical_port, "Known USB attack-platform descriptor indicator", 15)
        if session["blocked"]:
            deauthorize_usb_device(physical_port)
            reason = "; ".join(session["findings"] or ["Physical-port session already blocked"])
            usb_info["port_session"] = dict(session)
            report_preblocked_device(usb_info, "badusb-multi-stage", reason,
                                     risk=max(70, session["risk"]))
            print(Colors.RED + Colors.BOLD +
                  f"[CRITICAL] Multi-stage/re-enumerated USB blocked on port {physical_port}" + Colors.END)
            set_device_state(device_id, "BLOCKED", "locked physical-port session")
            return

        guard = usbguard_device(usb_info["vid"], usb_info["pid"],
                                port=getattr(device, "sys_name", None), serial=usb_info.get("serial"))
        if not guard:
            usb_port = getattr(device, "sys_name", None)
            deauthorize_usb_device(usb_port)
            print(Colors.RED +
                  f"[!] USBGuard could not classify {vid_pid}; device blocked by default." +
                  Colors.END)
            log_device_decision(usb_info, "automatic", "unknown", "BLOCKED",
                                "USBGuard classification unavailable", risk_score=15)
            report_preblocked_device(usb_info, "unknown", "USBGuard classification unavailable")
            set_device_state(device_id, "BLOCKED", "USBGuard classification unavailable")
            return
        if guard:
            usb_info["guard_interfaces"] = guard["interfaces"]
            usb_info["usbguard_hash"] = guard.get("hash", "")
            session["interface_history"].append(sorted(guard["interfaces"]))
            usb_info["hardware_fingerprint"] = hardware_fingerprint(usb_info, guard["interfaces"])
            usb_info["interface_fingerprint"] = interface_fingerprint(guard["interfaces"])
            usb_info["port_session"] = dict(session)
            is_guard_hid = "03" in guard["interfaces"]
            is_guard_storage = "08" in guard["interfaces"]
            early_type = detect_actual_device_type(device, usb_info)
            set_device_state(device_id, "CLASSIFIED", early_type)
            emit_ui_event("scan_progress", {
                "incident_id": usb_info.get("incident_id"), "progress": 20,
                "message": f"USBGuard interfaces verified; classified as {early_type}.",
            })
            if not guard["interfaces"]:
                usbguard_set_state(guard["id"], False)
                print(Colors.RED + "[!] Device exposes no classifiable interfaces; blocked by default." + Colors.END)
                log_device_decision(usb_info, "automatic", "unknown", "BLOCKED",
                                    "Empty USBGuard interface set", risk_score=15)
                report_preblocked_device(usb_info, "unknown", "Empty USBGuard interface set")
                set_device_state(device_id, "BLOCKED", "unclassified interfaces")
                return
            if is_guard_hid and is_guard_storage:
                usbguard_set_state(guard["id"], False)
                print(Colors.RED + Colors.BOLD +
                      "[BLOCKED] Composite HID + storage device is not authorized." + Colors.END)
                log_device_decision(usb_info, "automatic", "composite-hid-storage", "BLOCKED",
                                    "Composite device exposes HID and storage", risk_score=20)
                lock_port_session(physical_port, "HID and storage interfaces appeared together", 20)
                report_preblocked_device(usb_info, "composite-hid-storage",
                                         "Composite device exposes HID and storage", risk=20)
                set_device_state(device_id, "BLOCKED", "composite HID + storage")
                return
            if is_guard_hid and vid_pid not in HID_WHITELIST:
                usbguard_set_state(guard["id"], False)
                print(Colors.RED + Colors.BOLD +
                      f"\n[BLOCKED BEFORE DRIVER BIND] Unknown HID {vid_pid}" + Colors.END)
                print("The device remains isolated by USBGuard; no keyboard/mouse driver was loaded.")
                log_device_decision(usb_info, "automatic", "keyboard", "BLOCKED",
                                    "Unknown HID blocked by USBGuard before authorization", risk_score=15)
                lock_port_session(physical_port, "Unknown HID interface blocked", 15)
                report_preblocked_device(usb_info, "keyboard",
                                         "Unknown HID blocked by USBGuard before authorization")
                if not session.get("alert_sent"):
                    session["alert_sent"] = True
                    threading.Thread(target=alert_hid_blocked,
                                     args=(usb_info.get("model", "Unknown HID Device"),),
                                     daemon=True).start()
                set_device_state(device_id, "BLOCKED", "unknown HID")
                return
            if is_guard_hid and vid_pid in HID_WHITELIST:
                trust_store = SignedTrustStore()
                identity = f"hid:{vid_pid}"
                trusted_record, trust_status = trust_store.get(identity)
                current_hardware = usb_info["hardware_fingerprint"]
                current_interfaces = usb_info["interface_fingerprint"]
                current_identity = device_identity_fingerprint(usb_info, guard["interfaces"])
                if trusted_record and (trusted_record.get("hardware_fingerprint") != current_hardware or
                                       trusted_record.get("interface_fingerprint") != current_interfaces or
                                       (trusted_record.get("identity_fingerprint") and
                                        trusted_record.get("identity_fingerprint") != current_identity)):
                    usbguard_set_state(guard["id"], False)
                    lock_port_session(physical_port, "Trusted HID fingerprint changed", 20)
                    report_preblocked_device(usb_info, "hid-fingerprint-changed",
                                             "Trusted HID hardware/interface fingerprint changed", risk=20)
                    set_device_state(device_id, "BLOCKED", "trusted HID fingerprint changed")
                    return
                if not trusted_record:
                    trust_store.put(identity, {
                        "kind": "hid", "vid_pid": vid_pid,
                        "name": HID_WHITELIST[vid_pid],
                        "hardware_fingerprint": current_hardware,
                        "interface_fingerprint": current_interfaces,
                        "identity_fingerprint": current_identity,
                        "enrolled_at": datetime.now().isoformat(),
                    })
                    trust_status = "legacy whitelist migrated to signed fingerprint"
                if not usbguard_set_state(guard["id"], True):
                    print(Colors.RED + "[!] USBGuard could not authorize trusted HID." + Colors.END)
                    return
                print(Colors.GREEN + f"[+] Trusted HID authorized: {vid_pid}" + Colors.END)
            elif is_guard_storage:
                if not usbguard_set_state(guard["id"], True):
                    print(Colors.RED + "[!] USBGuard could not authorize storage for scanning." + Colors.END)
                    return
                subprocess.run(["udevadm", "settle", "--timeout=10"], check=False)
                set_device_state(device_id, "ISOLATED", "storage authorized for read-only scan")

        detected_device_type = detect_actual_device_type(device, usb_info)
        declared_device_type = detected_device_type
        print(Colors.CYAN + f"[*] Automatically detected device type: {detected_device_type}" + Colors.END)
        set_device_state(device_id, "CLASSIFIED", detected_device_type)
        if detected_device_type == "other":
            usbguard_set_state(guard["id"], False)
            lock_port_session(physical_port, "Unsupported or unclassified USB interfaces", 20)
            usb_info["port_session"] = dict(port_session(physical_port))
            report_preblocked_device(usb_info, "unknown", "Unsupported or unclassified USB interfaces",
                                     risk=max(20, port_session(physical_port)["risk"]))
            print(Colors.RED + "[BLOCKED] Unknown/other devices are never treated as clean." + Colors.END)
            set_device_state(device_id, "BLOCKED", "unsupported device type")
            return

        # Whitelisted HID devices are only skipped when the hardware really behaves like HID.
        if (
            vid_pid in HID_WHITELIST
            and detected_device_type in {"keyboard", "mouse"}
            and not usb_device_has_storage(device)
            and declared_device_type == detected_device_type
        ):
            emit_ui_event("scan_progress", {
                "incident_id": usb_info.get("incident_id"), "progress": 85,
                "message": "Trusted HID fingerprint verified; generating incident report…",
            })
            print(Colors.CYAN + f"\n[ EVENT ] Whitelisted device connected: {HID_WHITELIST[vid_pid]}" + Colors.END)
            print_whitelisted_hid_report(usb_info, vid_pid)
            set_device_state(device_id, "ALLOWED", "trusted HID fingerprint verified")
            print("[READY] Trusted HID authorized. Monitoring continues while its report is generated.")
            report_info = json.loads(json.dumps(usb_info, default=str))
            threading.Thread(target=report_trusted_hid,
                             args=(report_info, trust_status), daemon=True).start()
            return

        print(Colors.CYAN + "\n[ EVENT ] USB Device Detected - Analyzing..." + Colors.END)
        if cancel_event.wait(0.25):
            raise DeviceRemovedDuringAnalysis("DEVICE REMOVED DURING ANALYSIS")

        # ── Phase 1: Hardware / HID analysis ──────────────────────────────────
        base_risk, flags = structural_rules(usb_info)
        emit_ui_event("scan_progress", {
            "incident_id": usb_info.get("incident_id"), "progress": 30,
            "message": "Hardware, interface and vulnerability analysis completed.",
        })
        hid_data = HID_RISK_CACHE.get(vid_pid, {"risk": 0, "flags": []})
        hid_risk = hid_data["risk"]
        flags.extend(hid_data["flags"])
        nvd_result = NVDClient().lookup(vid_pid)
        usb_info["nvd"] = nvd_result.to_dict()
        flags.append(f"NVD: {nvd_result.status} ({nvd_result.confidence}) - {nvd_result.message}")
        for cve in (nvd_result.cves or [])[:10]:
            flags.append(f"NVD {cve['id']}: CVSS {cve['cvss']} {cve['severity']} - {cve['description']}")
        
        # ── Phase 2: Storage scan ─────────────────────────────────────────────
        storage_risk = 0
        malware_detected = False
        has_storage = False
        scanned_paths = []
        scanned_storage = []
        all_malicious_files = []
        file_hashes = []
        storage_fingerprint_materials = []
        storage_fingerprint = None
        previous_storage_entry = STORAGE_WHITELIST.get(vid_pid)
        signed_storage, signed_status = SignedTrustStore().get(
            f"storage:{vid_pid}:{usb_info.get('serial', 'Unknown')}")
        if signed_status == "verified":
            previous_storage_entry = signed_storage
        elif previous_storage_entry:
            # Migrate a legacy record once; later edits must pass HMAC verification.
            SignedTrustStore().put(f"storage:{vid_pid}:{usb_info.get('serial', 'Unknown')}",
                                   previous_storage_entry)
            signed_status = "legacy record migrated"
        if (not isinstance(previous_storage_entry, dict) or
                previous_storage_entry.get("serial") != usb_info.get("serial") or
                previous_storage_entry.get("hardware_fingerprint") not in {None, usb_info.get("hardware_fingerprint")}):
            previous_storage_entry = None
        antivirus_available = _clamav_command() is not None
        yara_available = load_yara_rules() is not None

        # Retry partition detection — kernel may need extra time to register block devices
        for attempt in range(5):
            context = pyudev.Context()
            for block_device in context.list_devices(subsystem="block"):
                # A block device is mountable if it has a filesystem. This catches both normal partitions
                # (/dev/sda1) and superfloppy formatted drives that have the filesystem directly on the disk (/dev/sda).
                is_mountable = block_device.get("ID_FS_USAGE") == "filesystem"
                if is_mountable or block_device.device_type == "partition":
                    parent = block_device.find_parent("usb", "usb_device")
                    if parent and getattr(parent, "sys_path", None) == getattr(device, "sys_path", None):
                        has_storage = True
                        if not antivirus_available:
                            storage_risk += 5
                            flags.append("ClamAV unavailable; storage cannot be accepted as safe")
                        if not yara_available:
                            storage_risk += 5
                            flags.append("YARA unavailable; storage cannot be accepted as safe")
                        print(Colors.CYAN + f"[*] Found partition: {block_device.device_node}" + Colors.END)
                        mount, quarantine_mount = mount_for_quarantine_scan(block_device.device_node)
                        if mount:
                            print(f"[+] Scanning from {mount}")
                            scanned_paths.append(mount)
                            scanned_storage.append({
                                "device_node": block_device.device_node,
                                "mount_path": mount,
                                "quarantine_mount": quarantine_mount,
                                "safe": False,
                            })
                            pr, pm, pbad, current_storage_fingerprint, current_file_hashes = scan_storage(
                                mount, usb_info, previous_entry=previous_storage_entry,
                                cancel_event=cancel_event)
                            storage_risk += pr
                            if pm:
                                malware_detected = True
                                all_malicious_files.extend(pbad)
                            if current_storage_fingerprint:
                                storage_fingerprint_materials.append(current_storage_fingerprint)
                            if current_file_hashes:
                                file_hashes.extend(current_file_hashes)
                        else:
                            storage_risk += 15
                            flags.append(f"Could not mount {block_device.device_node} for safety scan (blocked by default)")
                            print(Colors.RED + f"[!] Could not mount {block_device.device_node} for safety scan" + Colors.END)
            if has_storage:
                break
            if attempt < 4:
                print(Colors.YELLOW + f"[*] Waiting for partitions to appear... (attempt {attempt + 2}/5)" + Colors.END)
                if cancel_event.wait(2):
                    raise DeviceRemovedDuringAnalysis("DEVICE REMOVED DURING ANALYSIS")

        if not has_storage and is_mtp_or_ptp_device(device):
            has_storage = True
            flags.append("Mobile phone detected through MTP/PTP")
            if not antivirus_available:
                storage_risk += 5
                flags.append("ClamAV unavailable; phone storage cannot be accepted as safe")
            if not yara_available:
                storage_risk += 5
                flags.append("YARA unavailable; phone storage cannot be accepted as safe")
            print(Colors.CYAN + "[*] Mobile phone storage mode detected (MTP/PTP)" + Colors.END)
            print(Colors.CYAN + "[*] Waiting for phone file-transfer mount..." + Colors.END)
            mtp_mounts = wait_for_mtp_mount(device)
            if mtp_mounts:
                for mount in mtp_mounts:
                    print(f"[+] Phone storage accessible at {mount}")
                    scanned_paths.append(mount)
                    pr, pm, pbad, current_storage_fingerprint, current_file_hashes = scan_storage(
                        mount, usb_info, previous_entry=previous_storage_entry,
                        cancel_event=cancel_event)
                    storage_risk += pr
                    if pm:
                        malware_detected = True
                        all_malicious_files.extend(pbad)
                    if current_storage_fingerprint:
                        storage_fingerprint_materials.append(current_storage_fingerprint)
                    if current_file_hashes:
                        file_hashes.extend(current_file_hashes)
            else:
                storage_risk += 15
                flags.append("MTP/PTP phone detected but no accessible file-transfer mount found (blocked by default)")
                print(Colors.YELLOW +
                      "[!] Phone detected, but files are not accessible. Unlock the phone and select File Transfer/MTP." +
                      Colors.END)

        if storage_fingerprint_materials:
            aggregate_input = "\n".join(sorted(storage_fingerprint_materials)).encode("utf-8")
            storage_fingerprint = hashlib.sha256(aggregate_input).hexdigest()

        if not has_storage:
            flags.append("No block storage or MTP/PTP file-transfer interface found")

        if has_storage:
            detected_device_type = "storage"

        type_mismatch = declared_device_type != detected_device_type
        policy_risk = 15 if type_mismatch else 0
        if type_mismatch:
            flags.append(
                f"DEVICE TYPE MISMATCH: user declared '{declared_device_type}' but detected '{detected_device_type}'"
            )

        # ── Phase 3: Save ORIGINAL scan results (before any user intervention) ──
        original_storage_risk = storage_risk
        original_malware_detected = malware_detected
        detailed_risk = risk_breakdown(
            hardware=base_risk, trust=policy_risk, interface=hid_risk,
            storage=storage_risk, nvd=nvd_result.risk,
            malware=70 if original_malware_detected else 0,
        )
        usb_info["risk_breakdown"] = detailed_risk
        usb_info["original_risk_breakdown"] = dict(detailed_risk)
        original_total_risk = detailed_risk["total"]
        publish_event("risk_updated", dict(detailed_risk), usb_info.get("incident_id"))

        # Findings remain in memory until the single consolidated final incident
        # report is written. This avoids contradictory initial/final files.

        emit_ui_event("scan_complete", {
            "incident_id": usb_info.get("incident_id"),
            "malware_detected": malware_detected,
            "threats": len(all_malicious_files),
            "files": len(file_hashes) if has_storage else 0,
            "duration": "Completed",
            "base_risk": base_risk,
            "storage_risk": storage_risk,
            "hid_risk": hid_risk,
            "policy_risk": policy_risk,
            "inventory": dict(usb_info.get("file_inventory", {})),
            "original_risk": dict(detailed_risk),
        })

        trusted_storage = False
        storage_trust_invalidated = False
        storage_trust_entry = None
        if detected_device_type == "storage":
            storage_trust_entry = STORAGE_WHITELIST.get(vid_pid)
            if storage_trust_entry:
                if storage_trust_entry.get("serial") == usb_info.get("serial") and storage_trust_entry.get("fingerprint") == storage_fingerprint:
                    trusted_storage = True
                    flags.append("Storage whitelist verified: serial and fingerprint match")
                    if storage_trust_entry.get("force_rescan"):
                        trust_storage_device(vid_pid, usb_info, storage_fingerprint, file_hashes)
                        flags.append("Requested full trusted-storage rescan completed; cache refreshed")
                else:
                    storage_trust_invalidated = True
                    flags.append("Storage whitelist invalidated: serial or fingerprint changed")
                    invalidate_storage_trust(vid_pid, "storage trust changed")
        if type_mismatch:
            reason_str = (
                f"declared type '{declared_device_type}' does not match detected type '{detected_device_type}'"
            )
            print(Colors.RED + f"[!] Device is NOT SAFE. Keeping storage unavailable." + Colors.END)
            print(Colors.RED + f"    Reason: {reason_str}" + Colors.END)
            if storage_fingerprint:
                print(f"    Storage Hash: {storage_fingerprint}")
            for item in scanned_storage:
                keep_storage_blocked(
                    item["device_node"],
                    item["mount_path"],
                    item["quarantine_mount"],
                )
            usb_port = _sysfs_port_from_vid_pid(usb_info['vid'], usb_info['pid'], usb_info.get('serial'))
            if usb_port:
                deauthorize_usb_device(usb_port)

            print("\n" + "=" * 60)
            print(Colors.BOLD + Colors.CYAN + "        DEVICE TYPE MISMATCH REPORT        " + Colors.END)
            print("=" * 60)
            print(f"  Time           : {datetime.now()}")
            print(f"  Vendor         : {usb_info['vendor']}")
            print(f"  Model          : {usb_info['model']}")
            print(f"  VID:PID        : {vid_pid}")
            print(f"  Serial         : {usb_info['serial']}")
            print(f"  USB Class      : {usb_info['usb_class']}")
            print(f"  Declared Type  : {declared_device_type}")
            print(f"  Detected Type  : {detected_device_type}")
            print(f"  Policy Risk    : {policy_risk}")
            print(f"  Total Risk     : {original_total_risk}")
            print(f"  Threat Level   : {threat_level(original_total_risk)}")
            print(Colors.RED + Colors.BOLD + "  Status         : BLOCKED - Type mismatch" + Colors.END)
            if flags:
                print("  Flags / Findings:")
                for f in flags:
                    print(f"    - {f}")
            print("=" * 60 + "\n")

            mismatch_verdict = "DANGEROUS" if original_total_risk >= 40 else "SUSPICIOUS"
            pdf_path = generate_pdf_report(
                usb_info,
                base_risk,
                original_storage_risk,
                hid_risk,
                policy_risk,
                original_total_risk,
                original_malware_detected,
                flags,
                sanitized=False,
                declared_device_type=declared_device_type,
                detected_device_type=detected_device_type,
                verdict=mismatch_verdict,
            )
            json_path = generate_json_report(
                usb_info, stage="final", decision="BLOCKED",
                verdict=mismatch_verdict,
                detected_type=detected_device_type, total_risk=original_total_risk,
                flags=flags, risk_breakdown=detailed_risk, nvd=nvd_result.to_dict(),
                fingerprint_comparison={
                    "hardware": usb_info.get("hardware_fingerprint"),
                    "interfaces": usb_info.get("interface_fingerprint"),
                    "storage": storage_fingerprint,
                },
            )
            notify_incident(usb_info, mismatch_verdict, json_path, pdf_path)

            log_device_decision(
                usb_info,
                declared_device_type,
                detected_device_type,
                "BLOCKED",
                reason_str,
                risk_score=policy_risk + (5 if storage_trust_invalidated else 0),
            )
            print(Colors.GREEN + "[OK] Device analysis complete. Ready for next device..." + Colors.END)
            return

        # ── Phase 4: Sanitization prompt ──────────────────────────────────────
        sanitized = False
        if malware_detected and all_malicious_files:
            alert_threat_detected(usb_info.get('model', 'USB Device'), len(all_malicious_files))
            print("\n" + "=" * 60)
            print(Colors.RED + Colors.BOLD + "  [!] MALICIOUS FILES DETECTED ON THIS DRIVE" + Colors.END)
            print("=" * 60)
            print(Colors.YELLOW + f"  Found {len(all_malicious_files)} dangerous file(s):" + Colors.END)
            for i, f in enumerate(all_malicious_files, 1):
                print(Colors.RED + f"    {i}. {f}" + Colors.END)
            print()
            print(Colors.CYAN + "  You have two options:" + Colors.END)
            print("    [y] QUARANTINE the malicious files and allow access to the rest of the drive")
            print("    [n] BLOCK the entire drive (no access)")
            print()
            print(Colors.CYAN + "  Note: Quarantined files are moved to a secure vault and can be" + Colors.END)
            print(Colors.CYAN + "  restored later if they turn out to be false positives." + Colors.END)
            print()
            if UI_MODE:
                resp = prompt_ui("sanitize_prompt", {"device": usb_info, "malicious_files": all_malicious_files})
                user_input = resp.get("answer", "n") if resp else "n"
            else:
                user_input = request_user_action(
                    "Malware was detected on this USB storage device.",
                    f"{usb_info.get('vendor', 'Unknown')} {usb_info.get('model', 'USB Device')}",
                    f"Threats found: {len(all_malicious_files)}\n"
                    "Current access: BLOCKED (read-only isolation mount)\n"
                    "Choosing quarantine temporarily enables write access only to remove the verified threats.\n"
                    "If removal or verification fails, the entire device remains blocked.",
                    {
                        "1": ("y", "CONFIRM quarantine, verify removal, then rescan/release by policy"),
                        "y": ("y", "CONFIRM quarantine, verify removal, then rescan/release by policy"),
                        "yes": ("y", "CONFIRM quarantine, verify removal, then rescan/release by policy"),
                        "2": ("n", "BLOCK the entire device; do not modify its files"),
                        "n": ("n", "BLOCK the entire device; do not modify its files"),
                        "no": ("n", "BLOCK the entire device; do not modify its files"),
                    },
                    default="n", timeout=60,
                )

            if user_input == 'y':
                print()
                
                # The drive was mounted read-only for safety during the scan.
                # We must temporarily remount it as read-write to delete the viruses.
                for item in scanned_storage:
                    if item["quarantine_mount"]:
                        try:
                            subprocess.run(["mount", "-o", "remount,rw", item["mount_path"]], capture_output=True)
                        except Exception:
                            pass

                all_quarantined = True
                quarantined_count = 0
                for f in all_malicious_files:
                    try:
                        q_path = move_to_quarantine(
                            f, usb_info,
                            reason="ClamAV/YARA/hash/static analysis classified the file as malicious",
                        )
                        quarantined_count += 1
                        flags.append(f"QUARANTINE PATH: {q_path}")
                        print(Colors.GREEN + f"  [OK] Quarantined: {os.path.basename(f)} -> vault" + Colors.END)
                    except Exception as e:
                        print(Colors.RED + f"  [FAIL] Could not quarantine {f}: {e}" + Colors.END)
                        all_quarantined = False
                
                if all_quarantined:
                    malware_detected = False
                    storage_risk = 0
                    sanitized = True
                    flags.append(f"REMEDIATION: {quarantined_count} malicious file(s) moved to quarantine vault")
                    print(Colors.GREEN + Colors.BOLD + f"\n  [OK] All {quarantined_count} malicious files quarantined. Drive is now safe to use." + Colors.END)
                    print(Colors.CYAN + f"  Quarantine vault: {QUARANTINE_DIR}" + Colors.END)
                    print(Colors.CYAN + f"  To manage: python3 changed.py --quarantine list" + Colors.END)
                else:
                    flags.append("REMEDIATION FAILED: Some malicious files could not be quarantined")
                    print(Colors.RED + "\n  [!] Some files could not be quarantined. Drive will remain BLOCKED." + Colors.END)
            else:
                flags.append("User declined sanitization; drive blocked")
                print(Colors.RED + "\n  [!] User declined. Drive will remain BLOCKED." + Colors.END)
            print("=" * 60)

        # ── Phase 5: Final risk calculation (post-sanitization) ───────────────
        final_risk_breakdown = risk_breakdown(hardware=base_risk, trust=policy_risk,
                                             interface=hid_risk, storage=storage_risk,
                                             nvd=nvd_result.risk)
        total_risk = final_risk_breakdown["total"]
        usb_info["risk_breakdown"] = final_risk_breakdown
        usb_info["final_risk_breakdown"] = dict(final_risk_breakdown)
        final_risk_event = dict(final_risk_breakdown)
        final_risk_event.update({
            "original": dict(detailed_risk), "final": dict(final_risk_breakdown),
            "total": original_total_risk if sanitized else total_risk,
            "final_total": total_risk, "remediated": sanitized,
        })
        publish_event("risk_updated", final_risk_event, usb_info.get("incident_id"))

        # ── Phase 6: Terminal Report ──────────────────────────────────────────
        print("\n" + "=" * 60)
        print(Colors.BOLD + Colors.CYAN + "        COMPLETE USB DEVICE SECURITY REPORT        " + Colors.END)
        print("=" * 60)
        print(f"  Time           : {datetime.now()}")
        print(f"  Vendor         : {usb_info['vendor']}")
        print(f"  Model          : {usb_info['model']}")
        print(f"  VID:PID        : {vid_pid}")
        print(f"  Serial         : {usb_info['serial']}")
        print(f"  USB Class      : {usb_info['usb_class']}")
        print(f"  USB Driver     : {usb_info['usb_driver']}")
        print("-" * 60)
        print(f"  Hardware Risk  : {base_risk}")
        print(f"  Storage Risk   : {original_storage_risk}" + (f" -> 0 (sanitized)" if sanitized else ""))
        print(f"  HID Risk       : {hid_risk}")
        print(f"  Policy Risk    : {policy_risk}")
        print(f"  Trust Risk     : {final_risk_breakdown.get('trust', 0)}")
        print(f"  Interface Risk : {final_risk_breakdown.get('interface', 0)}")
        print(f"  Behavior Risk  : {final_risk_breakdown.get('behavior', 0)}")
        print(f"  NVD Risk       : {final_risk_breakdown.get('nvd', 0)}")
        if sanitized:
            print(f"  Original Total : {original_total_risk}")
            print(f"  Final Total    : {total_risk} (after sanitization)")
        else:
            print(f"  Total Risk     : {total_risk}")
        print(f"  Threat Level   : {threat_level(total_risk)}")
        print(f"  Declared Type  : {declared_device_type}")
        print(f"  Detected Type  : {detected_device_type}")
        if storage_fingerprint:
            print(f"  Storage Hash   : {storage_fingerprint}")
        if type_mismatch:
            print(Colors.RED + Colors.BOLD + "  Status         : BLOCKED - Type mismatch" + Colors.END)
        elif sanitized:
            print(Colors.GREEN + Colors.BOLD + "  Status         : SANITIZED - Drive cleaned and allowed" + Colors.END)
        elif malware_detected:
            print(Colors.RED + Colors.BOLD + "  Status         : BLOCKED - Malware detected" + Colors.END)
        if scanned_paths:
            print(f"\n  Scanned Paths:")
            for path in scanned_paths:
                print(f"    - {path}")
        coverage = usb_info.get("scan_coverage", {})
        if coverage:
            print("\n  Scan Coverage:")
            print(f"    Total files  : {coverage.get('total_files', 0)}")
            print(f"    Fully scanned: {coverage.get('fully_scanned_files', 0)}")
            print(f"    Cached/verified: {coverage.get('cached_files', 0)}")
            print(f"    Cache permitted: {coverage.get('cache_reuse_allowed', False)}")
        if detected_device_type in {"keyboard", "mouse"} and vid_pid in HID_WHITELIST:
            print(f"\n  HID Whitelist  : {HID_WHITELIST[vid_pid]}")
        if flags:
            print(f"\n  Flags / Findings:")
            for f in flags:
                print(f"    - {f}")
        print("=" * 60 + "\n")
        
        # ── Phase 7: Generate PDF Report ──────────────────────────────────────
        # The PDF must reflect the ORIGINAL scan findings, not the post-sanitization state.
        # We pass both original and sanitized values so the PDF is accurate.
        final_pdf_path = None
        
        # ── Phase 8: Device access decision ───────────────────────────────────
        # A sanitized device is safe. A clean-scanned device is safe.
        # Everything else stays blocked.
        if type_mismatch:
            reason_str = (
                f"declared type '{declared_device_type}' does not match detected type '{detected_device_type}'"
            )
            print(Colors.RED + f"[!] Device is NOT SAFE. Keeping storage unavailable." + Colors.END)
            print(Colors.RED + f"    Reason: {reason_str}" + Colors.END)
            for item in scanned_storage:
                keep_storage_blocked(
                    item["device_node"],
                    item["mount_path"],
                    item["quarantine_mount"],
                )
            usb_port = _sysfs_port_from_vid_pid(usb_info['vid'], usb_info['pid'], usb_info.get('serial'))
            if usb_port:
                deauthorize_usb_device(usb_port)
            log_device_decision(
                usb_info,
                declared_device_type,
                detected_device_type,
                "BLOCKED",
                reason_str,
                risk_score=policy_risk,
            )
            print(Colors.GREEN + "[OK] Device analysis complete. Ready for next device..." + Colors.END)
            return

        if storage_trust_invalidated:
            print(Colors.RED + "[!] Stored fingerprint no longer matches. Whitelist entry removed and device will be treated as untrusted." + Colors.END)

        if not has_storage:
            # For pure HID devices (mice/keyboards), allow them if there's no active HID attack.
            # A base_risk of 1 or 2 (e.g., missing serial number) is common for cheap generic mice and shouldn't cause a strict block.
            safe_to_use = (hid_risk == 0 and base_risk < 8)
        else:
            # If the fingerprint changed, trusted_storage is False, so it falls back to checking the scan results!
            safe_to_use = sanitized or trusted_storage or (bool(scanned_paths) and not malware_detected and storage_risk == 0)
            
        if safe_to_use:
            alert_device_clean(usb_info.get('model', 'USB Device'))
            if not has_storage:
                print(Colors.GREEN + "[*] Device is CLEAN. No storage to mount." + Colors.END)
            elif sanitized:
                print(Colors.GREEN + "[*] Device SANITIZED. Accepting device for user access..." + Colors.END)
            else:
                print(Colors.GREEN + "[*] Device is CLEAN. Accepting device for user access..." + Colors.END)
                
            # Ask the user if they want to whitelist this clean device
            if detected_device_type in {"keyboard", "mouse"} and not sanitized and vid_pid not in HID_WHITELIST:
                print()
                while True:
                    if UI_MODE:
                        resp = prompt_ui("trust_hid", {"vid_pid": vid_pid, "device": usb_info})
                        wl_input = resp.get("answer", "n") if resp else "n"
                    else:
                        wl_input = request_user_action(
                            "Trust this clean HID device for future connections?",
                            f"{usb_info.get('vendor', 'Unknown')} {usb_info.get('model', 'USB Device')}",
                            f"VID:PID: {vid_pid}\nDefault action: do not change the whitelist.",
                            {"1": ("y", "ADD device to HID whitelist"), "y": ("y", "ADD device to HID whitelist"),
                             "2": ("n", "DO NOT trust this device"), "n": ("n", "DO NOT trust this device")},
                            default="n", timeout=30,
                        )
                    if wl_input in ['y', 'n']:
                        break
                if wl_input == 'y':
                    HID_WHITELIST[vid_pid] = f"{usb_info.get('vendor', 'Unknown')} {usb_info.get('model', 'USB Device')}"
                    save_whitelist()
                    print(Colors.GREEN + f"  [+] Device {vid_pid} permanently added to whitelist." + Colors.END)
                print()
            elif detected_device_type == "storage" and not sanitized and not trusted_storage:
                print()
                while True:
                    if UI_MODE:
                        resp = prompt_ui("trust_storage", {"vid_pid": vid_pid, "device": usb_info})
                        wl_input = resp.get("answer", "n") if resp else "n"
                    else:
                        wl_input = request_user_action(
                            "Trust this clean storage fingerprint for future checks?",
                            f"{usb_info.get('vendor', 'Unknown')} {usb_info.get('model', 'USB Device')}",
                            f"VID:PID: {vid_pid}\nDefault action: do not store trust.",
                            {"1": ("y", "STORE serial and storage fingerprint"), "y": ("y", "STORE serial and storage fingerprint"),
                             "2": ("n", "DO NOT trust this storage device"), "n": ("n", "DO NOT trust this storage device")},
                            default="n", timeout=30,
                        )
                    if wl_input in ['y', 'n']:
                        break
                if wl_input == 'y':
                    trust_saved = trust_storage_device(
                        vid_pid, usb_info, storage_fingerprint, file_hashes
                    )
                    if trust_saved:
                        print(Colors.GREEN + f"  [+] Storage device {vid_pid} stored with serial and fingerprint." + Colors.END)
                        publish_event("trust_updated", {
                            "status": "SAVED", "device_type": "storage",
                            "vid_pid": vid_pid, "message": "Fingerprint saved and verified",
                        }, usb_info.get("incident_id"))
                    else:
                        print(Colors.RED + "  [!] Trust was NOT saved: persistent verification failed." + Colors.END)
                        publish_event("trust_updated", {
                            "status": "FAILED", "device_type": "storage",
                            "vid_pid": vid_pid,
                            "message": "Fingerprint could not be saved or verified",
                        }, usb_info.get("incident_id"))
                print()

            if base_risk > 0:
                print(Colors.YELLOW + f"[*] Hardware warning kept for report only; storage scan is clean. Hardware risk: {base_risk}" + Colors.END)
            for item in scanned_storage:
                release_storage_for_use(
                    item["device_node"],
                    item["mount_path"],
                    item["quarantine_mount"],
                )
            usb_port = _sysfs_port_from_vid_pid(usb_info['vid'], usb_info['pid'], usb_info.get('serial'))
            if usb_port:
                authorize_usb_device(usb_port)
            else:
                print(Colors.YELLOW + "[!] Could not determine sysfs port to authorize." + Colors.END)
        else:
            reason_parts = []
            if malware_detected:
                reason_parts.append("malware found on device")
            if storage_risk > 0:
                reason_parts.append(f"storage risk score = {storage_risk}")
            if not scanned_paths:
                reason_parts.append("no partitions could be scanned")
            if storage_trust_invalidated:
                reason_parts.append("stored fingerprint changed")
            reason_str = ", ".join(reason_parts) if reason_parts else "unknown"
            print(Colors.RED + f"[!] Device is NOT SAFE. Keeping storage unavailable." + Colors.END)
            print(Colors.RED + f"    Reason: {reason_str}" + Colors.END)
            for item in scanned_storage:
                keep_storage_blocked(
                    item["device_node"],
                    item["mount_path"],
                    item["quarantine_mount"],
                )
            usb_port = _sysfs_port_from_vid_pid(usb_info['vid'], usb_info['pid'])
            if usb_port:
                deauthorize_usb_device(usb_port)

        if not type_mismatch:
            log_device_decision(
                usb_info,
                declared_device_type,
                detected_device_type,
                "ALLOWED" if safe_to_use else "BLOCKED",
                "scan completed",
                risk_score=policy_risk + (5 if storage_trust_invalidated else 0),
            )

        final_decision = "ALLOWED" if safe_to_use else "BLOCKED"
        # Successful quarantine permits access to the cleaned remainder but the
        # incident must retain its historical malware verdict. CLEAN means no
        # threat was found, never "threat found and remediated".
        verdict = normalized_verdict(
            allowed=safe_to_use, trusted=trusted_storage,
            malware=original_malware_detected, total_risk=total_risk,
            remediated=sanitized,
        )
        timing = {
            "detected_at": port_session(physical_port).get("started_at"),
            "completed_at": datetime.now().isoformat(),
            "enforcement_latency_ms": port_session(physical_port).get("enforcement_latency_ms"),
            "analysis_duration_ms": round(
                (time.monotonic() - port_session(physical_port)["detected_monotonic"]) * 1000, 1),
        }
        usb_info["timing"] = timing
        usb_info["fingerprint_comparison"] = {
            "hardware": usb_info.get("hardware_fingerprint"),
            "interfaces": usb_info.get("interface_fingerprint"),
            "storage": storage_fingerprint,
            "trust_invalidated": storage_trust_invalidated,
        }
        usb_info["quarantine_records"] = _read_quarantine_entries_for_device(vid_pid)
        flags.extend([
            f"VERDICT: {verdict}",
            f"Hardware fingerprint: {usb_info.get('hardware_fingerprint', 'unavailable')}",
            f"Interface fingerprint: {usb_info.get('interface_fingerprint', 'unavailable')}",
            f"Storage fingerprint: {storage_fingerprint or 'not applicable'}",
            f"Completed at: {timing['completed_at']}",
            f"Analysis duration: {timing['analysis_duration_ms']} ms",
        ])
        final_pdf_path = generate_pdf_report(
            usb_info, base_risk, original_storage_risk, hid_risk, policy_risk,
            original_total_risk, original_malware_detected, flags,
            sanitized=sanitized, declared_device_type=declared_device_type,
            detected_device_type=detected_device_type, stage="final", verdict=verdict,
        )
        final_json_path = generate_json_report(
            usb_info, stage="final", decision=final_decision, verdict=verdict, sanitized=sanitized,
            original_malware_detected=original_malware_detected,
            original_risk_breakdown=detailed_risk,
            detected_type=detected_device_type, total_risk=total_risk,
            malware_detected=malware_detected, malicious_files=all_malicious_files,
            scanned_paths=scanned_paths, flags=flags,
            risk_breakdown=final_risk_breakdown, nvd=nvd_result.to_dict(),
            fingerprint_comparison={
                "hardware": usb_info.get("hardware_fingerprint"),
                "interfaces": usb_info.get("interface_fingerprint"),
                "storage": storage_fingerprint,
                "trust_invalidated": storage_trust_invalidated,
            },
            quarantine_paths=[entry.get("quarantine_path") for entry in
                              _read_quarantine_entries_for_device(vid_pid)],
            timing=timing,
            recommendations=[
                "Keep device blocked when scan coverage is incomplete",
                "Apply vendor firmware updates for verified NVD findings",
                "Re-run a full scan whenever hardware, content, or engine fingerprints change",
            ],
        )
        notify_incident(usb_info, verdict, final_json_path, final_pdf_path)
        set_device_state(device_id, final_decision, "scan workflow completed")

        print("\n" + "=" * 68)
        print("SCAN WORKFLOW COMPLETED")
        print("=" * 68)
        print(f"Final decision : {final_decision}")
        print(f"Device access  : {'AUTHORIZED' if safe_to_use else 'BLOCKED'}")
        print(f"PDF report     : {final_pdf_path or 'generation failed'}")
        print(f"JSON report    : {final_json_path}")
        print("No further user action is required.")
        print("=" * 68)

        print(Colors.GREEN + "[OK] Device analysis complete. Ready for next device..." + Colors.END)
    except DeviceRemovedDuringAnalysis as e:
        for mount_path in list(ACTIVE_ISOLATION_MOUNTS):
            unmount_storage(mount_path=mount_path)
            ACTIVE_ISOLATION_MOUNTS.discard(mount_path)
        findings = ["DEVICE REMOVED DURING ANALYSIS", str(e)]
        if "usb_info" not in locals():
            usb_info = {"vid": "unknown", "pid": "unknown", "vendor": "Unknown",
                        "model": "Removed USB device", "serial": "Unknown",
                        "usb_class": "unknown", "physical_port": physical_port}
        verdict = normalized_verdict(incomplete=True)
        json_path = generate_json_report(
            usb_info, stage="final", decision="BLOCKED", verdict=verdict,
            flags=findings, timing={"removed_at": datetime.now().isoformat()})
        pdf_path = generate_pdf_report(
            usb_info, 0, 0, 0, 0, 0, False, findings,
            detected_device_type="incomplete", stage="final", verdict=verdict)
        notify_incident(usb_info, verdict, json_path, pdf_path)
        set_device_state(device_id, "INCOMPLETE", "DEVICE REMOVED DURING ANALYSIS")
    except Exception as e:
        print(Colors.RED + f"\n[!] Error handling USB device: {e}" + Colors.END)
        set_device_state(device_id, "ERROR", str(e))
    finally:
        ACTIVE_DEVICE_PATHS.discard(getattr(device, "sys_path", None))
        DEVICE_CANCEL_EVENTS.pop(device_id, None)


def monitor_usb():
    print(Colors.CYAN + Colors.BOLD + "\n[*] Intelligent USB Security Engine Started" + Colors.END)
    print(Colors.GREEN + "[*] Monitoring for USB devices... (Press Ctrl+C to stop)\n" + Colors.END)
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem="usb")
    monitor.start()
    processed_devices = set()
    try:
        for device in iter(monitor.poll, None):
            if device.get("DEVTYPE") == "usb_device":
                # Use sys_path as the unique identifier since it is consistent across add and remove events
                device_id = getattr(device, 'sys_path', None)
                if not device_id:
                    continue
                if device.action == "add":
                    if device_id in processed_devices or device_id in ACTIVE_DEVICE_PATHS:
                        continue
                    processed_devices.add(device_id)
                    DISCONNECTED_DEVICE_PATHS.discard(device_id)
                    ACTIVE_DEVICE_PATHS.add(device_id)
                    DEVICE_EVENT_QUEUE.put(device)
                elif device.action == "remove":
                    processed_devices.discard(device_id)
                    ACTIVE_DEVICE_PATHS.discard(device_id)
                    DISCONNECTED_DEVICE_PATHS.add(device_id)
                    cancel_event = DEVICE_CANCEL_EVENTS.get(device_id)
                    if cancel_event:
                        cancel_event.set()
                    schedule_session_clear(getattr(device, "sys_name", "unknown"))
                    
                if len(processed_devices) > 100:
                    processed_devices.clear()
    except KeyboardInterrupt:
        for mount_path in list(ACTIVE_ISOLATION_MOUNTS):
            unmount_storage(mount_path=mount_path)
            ACTIVE_ISOLATION_MOUNTS.discard(mount_path)
            print(f"[CLEANUP] Unmounted isolation path: {mount_path}")
        print("\n" + Colors.YELLOW + "[!] Stopping USB Security Engine..." + Colors.END)
        print(Colors.GREEN + "[✓] Shutdown complete. Goodbye.\n" + Colors.END)

def device_worker():
    """Serialize complete device workflows so prompts and reports cannot overlap."""
    while True:
        device = DEVICE_EVENT_QUEUE.get()
        try:
            device_id = getattr(device, "sys_path", None)
            if device_id in DISCONNECTED_DEVICE_PATHS:
                set_device_state(device_id or "unknown", "INCOMPLETE",
                                 "device removed; queued analysis cancelled")
                port = getattr(device, "sys_name", "unknown")
                session = port_session(port)
                info = {
                    "vid": device.get("ID_VENDOR_ID", "unknown"),
                    "pid": device.get("ID_MODEL_ID", "unknown"),
                    "vendor": device.get("ID_VENDOR", "Unknown"),
                    "model": device.get("ID_MODEL", "Removed USB device"),
                    "serial": device.get("ID_SERIAL_SHORT", "Unknown"),
                    "usb_class": device.get("bDeviceClass", "unknown"),
                    "physical_port": port, "incident_id": session["incident_id"],
                }
                findings = ["DEVICE REMOVED DURING ANALYSIS",
                            "Queued analysis cancelled before it began"]
                json_path = generate_json_report(info, stage="final", decision="BLOCKED",
                                                 verdict="INCOMPLETE", flags=findings)
                pdf_path = generate_pdf_report(
                    info, 0, 0, 0, 0, 0, False, findings,
                    detected_device_type="incomplete", stage="final", verdict="INCOMPLETE")
                notify_incident(info, "INCOMPLETE", json_path, pdf_path)
            else:
                handle_usb_device(device)
        finally:
            DEVICE_EVENT_QUEUE.task_done()


def scan_connected_usb_devices():
    """Run the existing workflow for USB devices attached before startup."""
    context = pyudev.Context()
    found = 0
    for device in context.list_devices(subsystem="usb", DEVTYPE="usb_device"):
        device_id = getattr(device, "sys_path", None)
        if (not device_id or device_id in ACTIVE_DEVICE_PATHS
                or not device.get("ID_VENDOR_ID") or not device.get("ID_MODEL_ID")):
            continue
        ACTIVE_DEVICE_PATHS.add(device_id)
        found += 1
        DEVICE_EVENT_QUEUE.put(device)
    if not found:
        emit_ui_event("log", "No unscanned USB device is currently connected.")


def ui_command_reader():
    """Own stdin so commands and prompt responses cannot race each other."""
    while UI_MODE:
        line = sys.stdin.readline()
        if not line:
            return
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            emit_ui_event("log", "Ignored invalid UI command")
            continue
        if payload.get("command") == "scan_connected":
            scan_connected_usb_devices()
        else:
            UI_RESPONSES.put(payload)


# ==========================================
# /proc/bus/input/devices PARSER
# Keyed by eventX — unique per interface.
# ==========================================
def _parse_proc_input(filter_event=None):
    """
    Parse /proc/bus/input/devices.
    If filter_event is given (e.g. 'event5'), return only that entry or None.
    Otherwise return a dict of all USB HID entries keyed by eventX.
    Filters out non-USB buses.
    """
    results = {}
    try:
        with open("/proc/bus/input/devices") as f:
            content = f.read()
        for entry in content.split("\n\n"):
            if not entry.strip():
                continue
            info = {}
            for line in entry.strip().split("\n"):
                if line.startswith("I:"):
                    m = re.search(r"Bus=(\w+)\s+Vendor=([0-9a-f]+)\s+Product=([0-9a-f]+)", line)
                    if m:
                        info["bus"]        = m.group(1)
                        info["vendor_id"]  = m.group(2)
                        info["product_id"] = m.group(3)
                elif line.startswith("N:"):
                    m = re.search(r'Name="([^"]*)"', line)
                    if m:
                        info["name"] = m.group(1)
                elif line.startswith("P:"):
                    m = re.search(r"Phys=(\S+)", line)
                    if m:
                        info["phys"] = m.group(1)
                elif line.startswith("U:"):
                    m = re.search(r"Uniq=(\S+)", line)
                    if m:
                        info["uniq"] = m.group(1)
                elif line.startswith("H:"):
                    m = re.search(r"Handlers=(.+)", line)
                    if m:
                        parts = m.group(1).split()
                        info["handlers"]        = [h for h in parts if h.startswith("event")]
                        info["has_kbd_handler"] = "kbd" in parts
                elif line.startswith("B:"):
                    if "KEY=" in line:
                        info["has_key"] = True
                    if "BTN=" in line and not line.endswith("BTN="):
                        info["has_btn"] = True
                    if "REL=" in line and not line.endswith("REL="):
                        info["has_rel"] = True
                    if "ABS=" in line and not line.endswith("ABS="):
                        info["has_abs"] = True

            # Must be USB bus
            if info.get("bus") != USB_BUS_TYPE:
                continue
            handlers = info.get("handlers", [])
            if not handlers:
                continue
            if "vendor_id" not in info:
                continue

            info["device_id"] = f"{info['vendor_id']}:{info['product_id']}"
            key = handlers[0]

            if filter_event:
                if filter_event in handlers:
                    return info   # return single entry directly
            else:
                results[key] = info

    except Exception as e:
        print(f"[!] Error parsing /proc/bus/input/devices: {e}")

    return None if filter_event else results

# ==========================================
# HID RISK SCORING
# ==========================================
def has_serial(device_info):
    phys = device_info.get("phys", "")
    try:
        m = re.search(r"usb-(.+?)/", phys)
        if m:
            serial_path = f"/sys/bus/usb/devices/{m.group(1)}/serial"
            if os.path.exists(serial_path):
                with open(serial_path) as f:
                    return len(f.read().strip()) > 0
    except Exception:
        pass
    return False

def calculate_hid_risk(device_info, event_key):
    risk, flags = 0, []
    vid_pid = device_info.get("device_id", event_key)

    if vid_pid not in HID_WHITELIST:
        risk += 5
        flags.append("Unknown vendor/product ID (not in whitelist)")

    if not has_serial(device_info):
        risk += 3
        flags.append("Missing or empty serial number")

    if device_info.get("has_key") and (device_info.get("has_btn") or device_info.get("has_rel")):
        risk += 7
        flags.append("Composite HID (keyboard + mouse in one interface)")

    handlers = device_info.get("handlers", [])
    if len(handlers) > 1:
        risk += 4
        flags.append(f"Multiple event handlers: {handlers}")

    name = device_info.get("name", "").lower()
    if name in {"usb keyboard", "usb mouse", "usb input device", "keyboard",
                "hid keyboard", "hid mouse", "generic keyboard"}:
        risk += 3
        flags.append("Generic device name (common HID spoof)")

    if device_info.get("has_kbd_handler"):
        risk += 6
        flags.append("Keyboard handler (kbd) — keystroke injection capable")

    return risk, flags

# ==========================================
# SYSFS / UNBIND HELPERS
# ==========================================
def authorize_usb_device(usb_port):
    """
    Explicitly allow the OS to load drivers.
    Requires the udev default-deny rule to be active.
    """
    if not usb_port: return False
    try:
        auth_path = f"/sys/bus/usb/devices/{usb_port}/authorized"
        if os.path.exists(auth_path):
            with open(auth_path, "w") as f:
                f.write("1")
            print(Colors.GREEN + f"  [✓] Authorized USB port {usb_port} for use." + Colors.END)
            return True
    except PermissionError:
        print(Colors.RED + "  [!] Permission denied. Must run scanner as root/sudo to authorize USBs." + Colors.END)
    except Exception as e:
        print(Colors.YELLOW + f"  [!] Failed to authorize {usb_port}: {e}" + Colors.END)
    return False


def deauthorize_usb_device(usb_port, quiet=False):
    """Deny a USB device after an unsafe verdict, when sysfs authorization is available."""
    if not usb_port:
        return False
    try:
        auth_path = f"/sys/bus/usb/devices/{usb_port}/authorized"
        if os.path.exists(auth_path):
            with open(auth_path, "w") as f:
                f.write("0")
            if not quiet:
                print(Colors.RED + f"  [✓] Deauthorized USB port {usb_port}; device blocked." + Colors.END)
            return True
    except PermissionError:
        print(Colors.RED + "  [!] Permission denied. Run with sudo to deauthorize unsafe USBs." + Colors.END)
    except Exception as e:
        print(Colors.YELLOW + f"  [!] Failed to deauthorize {usb_port}: {e}" + Colors.END)
    return False

def _sysfs_port_from_phys(phys):
    """Return the USB device port (e.g. '1-1.4') from a phys string."""
    if not phys:
        return None
    phys_prefix = phys.split("/")[0]
    try:
        base = "/sys/bus/usb/devices"
        for dev_entry in os.listdir(base):
            if ":" in dev_entry:
                continue
            dev_path = os.path.join(base, dev_entry)
            try:
                for iface in os.listdir(dev_path):
                    input_path = os.path.join(dev_path, iface, "input")
                    if not os.path.isdir(input_path):
                        continue
                    for input_dev in os.listdir(input_path):
                        phys_file = os.path.join(input_path, input_dev, "phys")
                        if not os.path.exists(phys_file):
                            continue
                        try:
                            with open(phys_file) as pf:
                                if pf.read().strip().startswith(phys_prefix):
                                    return dev_entry
                        except Exception:
                            pass
            except Exception:
                pass
    except Exception:
        pass
    return None

def _sysfs_port_from_vid_pid(vendor_id, product_id, serial=None):
    """Resolve a USB port, preferring serial identity over VID/PID fallback."""
    try:
        base = "/sys/bus/usb/devices"
        for entry in os.listdir(base):
            if ":" in entry:
                continue
            vp = os.path.join(base, entry, "idVendor")
            pp = os.path.join(base, entry, "idProduct")
            if os.path.exists(vp) and os.path.exists(pp):
                with open(vp) as fv, open(pp) as fp:
                    if fv.read().strip() != vendor_id or fp.read().strip() != product_id:
                        continue
                    if serial and str(serial) not in {"", "Unknown", "unknown"}:
                        serial_path = os.path.join(base, entry, "serial")
                        if not os.path.exists(serial_path):
                            continue
                        with open(serial_path, encoding="utf-8", errors="replace") as fs:
                            if fs.read().strip() != str(serial):
                                continue
                    return entry
    except Exception:
        pass
    return None

def _unbind_usbhid(usb_port):
    unbind_path = "/sys/bus/usb/drivers/usbhid/unbind"
    base = "/sys/bus/usb/devices"
    unbound = 0
    try:
        for entry in os.listdir(base):
            if not entry.startswith(usb_port + ":"):
                continue
            driver_link = os.path.join(base, entry, "driver")
            if os.path.islink(driver_link) and \
               os.path.basename(os.readlink(driver_link)) == "usbhid":
                try:
                    with open(unbind_path, "w") as f:
                        f.write(entry)
                    print(Colors.RED + f"  [✓] Unbound {entry} from usbhid" + Colors.END)
                    unbound += 1
                except Exception as e:
                    print(Colors.YELLOW + f"  [!] Unbind failed for {entry}: {e}" + Colors.END)
    except Exception as e:
        print(Colors.YELLOW + f"  [!] sysfs unbind error: {e}" + Colors.END)
    return unbound

# ==========================================
# EVIOCREVOKE  (_IOW('E', 0x91, int))
# ==========================================
EVIOCREVOKE = 0x40044591

def _revoke_event_node(event_path):
    try:
        fd = os.open(event_path, os.O_RDWR | os.O_NONBLOCK)
        try:
            fcntl.ioctl(fd, EVIOCREVOKE, 0)
            return True
        finally:
            os.close(fd)
    except PermissionError:
        return None
    except Exception:
        return False

# ==========================================
# HID BLOCKING ENGINE
# ==========================================
def block_hid_device(device_info, event_key):
    handlers   = device_info.get("handlers", [])
    vendor_id  = device_info.get("vendor_id", "")
    product_id = device_info.get("product_id", "")
    phys       = device_info.get("phys", "")

    print(Colors.RED + Colors.BOLD + "\n[BLOCKING] Disabling HID device NOW..." + Colors.END)
    any_success = False
    need_root   = False

    # Method 1: EVIOCREVOKE (instant)
    print(Colors.YELLOW + "  [→] Method 1: EVIOCREVOKE ioctl..." + Colors.END)
    for handler in handlers:
        ep = f"/dev/input/{handler}"
        if not os.path.exists(ep):
            continue
        r = _revoke_event_node(ep)
        if r is True:
            print(Colors.RED + f"  [✓] REVOKED {ep} — kernel stopped all input" + Colors.END)
            any_success = True
        elif r is None:
            print(Colors.YELLOW + f"  [!] {ep}: need root" + Colors.END)
            need_root = True
        else:
            print(Colors.YELLOW + f"  [!] {ep}: EVIOCREVOKE failed" + Colors.END)

    # Method 2: usbhid driver unbind
    print(Colors.YELLOW + "  [→] Method 2: usbhid driver unbind..." + Colors.END)
    usb_port = _sysfs_port_from_phys(phys) if phys else None
    if usb_port:
        print(f"  [*] sysfs port (phys): {usb_port}")
    else:
        usb_port = _sysfs_port_from_vid_pid(vendor_id, product_id)
        if usb_port:
            print(f"  [*] sysfs port (VID:PID): {usb_port}")
    if usb_port:
        n = _unbind_usbhid(usb_port)
        if n > 0:
            any_success = True
        else:
            print(Colors.YELLOW + f"  [!] No usbhid interfaces found under {usb_port}" + Colors.END)
    else:
        print(Colors.YELLOW + "  [!] Could not determine sysfs port — skipping unbind" + Colors.END)

    # Method 3: chmod 000
    print(Colors.YELLOW + "  [→] Method 3: Revoking event node permissions..." + Colors.END)
    for handler in handlers:
        ep = f"/dev/input/{handler}"
        if not os.path.exists(ep):
            continue
        try:
            os.chmod(ep, 0o000)
            print(Colors.RED + f"  [✓] chmod 000 on {ep}" + Colors.END)
            any_success = True
        except PermissionError:
            print(Colors.YELLOW + f"  [!] chmod {ep}: need root" + Colors.END)
            need_root = True
        except Exception as e:
            print(Colors.YELLOW + f"  [!] chmod error: {e}" + Colors.END)

    print()
    if any_success:
        print(Colors.RED + Colors.BOLD + "★ HID DEVICE BLOCKED — keystrokes suppressed ★\n" + Colors.END)
    elif need_root:
        print(Colors.RED + Colors.BOLD + "✗ NEED ROOT — run: sudo python3 usb_hid_scanner.py\n" + Colors.END)
    else:
        print(Colors.RED + Colors.BOLD + "✗ BLOCKING FAILED (device may already be gone)\n" + Colors.END)
    return any_success

# ==========================================
# KEYSTROKE INJECTION DETECTOR
# ==========================================
def detect_keystroke_injection(event_path, timeout=0.5):
    try:
        if not os.path.exists(event_path):
            return False
        with open(event_path, "rb") as f:
            start = time.time()
            times = []
            while (time.time() - start) < timeout:
                data = f.read(16)
                if len(data) < 16:
                    break
                ev_type = int.from_bytes(data[8:10], "little")
                if ev_type == 1:
                    now = time.time()
                    times.append(now)
                    if len(times) >= 2 and 0 < (times[-1] - times[-2]) * 1000 < 10:
                        return True
        return False
    except PermissionError:
        return None
    except Exception:
        return False

# ==========================================
# PROCESS CORRELATION
# ==========================================
ATTACK_CMDS = ["wget", "curl", "nc", "ncat", "nmap", "xterm",
               "gnome-terminal", "konsole", "terminator",
               "perl", "ruby", "php", "powershell"]

def check_suspicious_processes(since_time, timeout=2):
    suspicious = []
    if time.time() - since_time > timeout:
        return suspicious
    try:
        for pid in os.listdir("/proc"):
            if not pid.isdigit():
                continue
            try:
                with open(f"/proc/{pid}/cmdline", "rb") as f:
                    cmd = f.read().decode("utf-8", errors="ignore").replace("\x00", " ").strip()
                for ac in ATTACK_CMDS:
                    if ac in cmd:
                        suspicious.append({"pid": pid, "cmdline": cmd[:100], "type": ac})
                        break
            except Exception:
                pass
    except Exception:
        pass
    return suspicious

# ==========================================
# HID MONITOR — pyudev kernel event driven
#
# WHY pyudev INSTEAD OF POLLING:
# The old approach polled /proc/bus/input/devices every 100ms. P4wnP1 and
# similar attack tools connect, inject a full payload, and disconnect in
# under one second. The poll loop simply never caught the device — it was
# already gone before the next poll ran.
#
# Now we subscribe directly to kernel uevents on the 'input' subsystem via
# pyudev. The moment the kernel registers a new /dev/input/eventX node we
# receive the callback in milliseconds — no polling delay at all. We then
# immediately fast-block any keyboard interface that isn't whitelisted,
# BEFORE doing any further scoring or analysis.
# ==========================================
def _process_hid_event(event_name, seen_events):
    """Analyse and optionally block a newly appeared HID interface."""
    if event_name in seen_events:
        return
    seen_events.add(event_name)

    load_whitelist()
    connection_time = time.time()

    device_info = None
    for delay in (0.05, 0.15, 0.3, 0.5, 1.0):
        time.sleep(delay)
        device_info = _parse_proc_input(filter_event=event_name)
        if device_info is not None:
            break
    if device_info is None:
        print(Colors.YELLOW +
              f"[!] {event_name}: not found in /proc/bus/input/devices "
              f"(non-USB or already disconnected — skipping)" +
              Colors.END)
        return

    vid_pid = device_info.get("device_id", event_name)
    if vid_pid in HID_WHITELIST:
        print(Colors.GREEN + f"\n[ HID ] WHITELISTED device connected: {HID_WHITELIST[vid_pid]} ({vid_pid})" + Colors.END)
        return

    risk_score, flags = calculate_hid_risk(device_info, event_name)

    print(Colors.CYAN + "\n[ HID DEVICE DETECTED ]\n" + Colors.END)
    print(f" Time               : {datetime.now()}")
    print(f" Device ID          : {vid_pid}")
    print(f" Name               : {device_info.get('name', 'Unknown')}")
    print(f" Event Handler      : {event_name}  (all: {device_info.get('handlers', [])})")
    print(f" Bus Type           : USB ({device_info.get('bus', '?')})")
    print(f" Keyboard Interface : "
          f"{'YES ← can inject keystrokes' if device_info.get('has_kbd_handler') else 'No'}")
    print("\n" + "-" * 60)
    print(f" Base Risk Score    : {risk_score}")

    # ── FAST-BLOCK: unknown keyboard interface ────────────────────────────────
    already_blocked = False
    if device_info.get("has_kbd_handler") and vid_pid not in HID_WHITELIST:
        print(Colors.RED + Colors.BOLD +
              "\n⚡ UNKNOWN KEYBOARD INTERFACE — BLOCKING NOW ⚡" + Colors.END)
        alert_hid_blocked(device_info.get('name', 'Unknown HID Device'))
        block_hid_device(device_info, event_name)
        already_blocked = True

    # ── Injection timing check ────────────────────────────────────────────────
    injection_risk = 0
    handlers = device_info.get("handlers", [])
    if handlers and not already_blocked:
        r = detect_keystroke_injection(f"/dev/input/{handlers[0]}", timeout=0.5)
        if r is True:
            injection_risk = 8
            print(f" Keystroke Pattern  : DETECTED (+8 risk)")
        elif r is None:
            print(f" Keystroke Pattern  : (requires root)")
        else:
            print(f" Keystroke Pattern  : None detected")
    else:
        print(f" Keystroke Pattern  : N/A (device blocked before check)")

    # ── Process correlation ───────────────────────────────────────────────────
    process_risk = 0
    sprocs = check_suspicious_processes(connection_time, timeout=2)
    if sprocs:
        process_risk = 5
        print(f" Suspicious Process : YES (+5 risk)")
        for p in sprocs[:3]:
            print(f"   - PID {p['pid']}: {p['cmdline'][:60]}")
    else:
        print(f" Suspicious Process : None")

    # ── Final score ───────────────────────────────────────────────────────────
    total_risk = risk_score + injection_risk + process_risk
    
    if vid_pid not in HID_RISK_CACHE:
        HID_RISK_CACHE[vid_pid] = {"risk": 0, "flags": []}
    HID_RISK_CACHE[vid_pid]["risk"] += total_risk
    HID_RISK_CACHE[vid_pid]["flags"].extend(flags)
    if injection_risk > 0:
        HID_RISK_CACHE[vid_pid]["flags"].append("Keystroke injection pattern detected")
    if process_risk > 0:
        HID_RISK_CACHE[vid_pid]["flags"].append("Suspicious process correlation detected")

    print(f" Total Risk Score   : {total_risk}")
    print(f" Threat Level       : {threat_level(total_risk)}")

    if flags:
        print("\n Hardware Flags:")
        for flag in flags:
            print(f"  • {flag}")

    if vid_pid in HID_WHITELIST:
        print(f"\n✓ Device is WHITELISTED: {HID_WHITELIST[vid_pid]}")
    else:
        print(f"\n⚠️  Device is NOT in whitelist")
    print("━" * 60 + "\n")

    # ── Score-based block for non-keyboard high-risk devices ──────────────────
    # The input-node monitor must not disable a mouse merely for generic
    # naming or multiple event nodes. USBGuard remains the authoritative
    # pre-driver barrier for unknown HID devices; keyboard interfaces still
    # use the score-based emergency block below.
    if not already_blocked and device_info.get("has_kbd_handler") and total_risk >= 8:
        label = ("⚠️  HIGH RISK HID DEVICE — BLOCKING ⚠️"
                 if total_risk >= 15 else
                 "⚠️  MEDIUM RISK HID DEVICE — BLOCKING ⚠️")
        print(Colors.RED + Colors.BOLD + label + Colors.END + "\n")
        block_hid_device(device_info, event_name)


def hid_monitor():
    """
    HID monitor driven by pyudev kernel uevents on the 'input' subsystem.
    Reacts the instant the kernel registers a new /dev/input/eventX node.
    """
    print(Colors.CYAN + Colors.BOLD + "\n[*] HID Attack Detection Engine Started" + Colors.END)
    print(Colors.GREEN + "[*] Monitoring for HID devices... (Press Ctrl+C to stop)\n" + Colors.END)

    seen_events = set()

    # Snapshot existing devices so we don't alert on pre-connected hardware
    existing = _parse_proc_input()
    seen_events.update(existing.keys())
    if existing:
        pre = ", ".join(f"{v['device_id']} ({k})" for k, v in existing.items())
        print(Colors.GREEN + f"[*] Pre-existing USB HID devices (ignored): {pre}" +
              Colors.END + "\n")

    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem="input")
    monitor.start()

    try:
        for udev_device in iter(monitor.poll, None):
            if udev_device.action != "add":
                continue
            dev_node = udev_device.device_node
            if not dev_node or not dev_node.startswith("/dev/input/event"):
                continue
            event_name = os.path.basename(dev_node)
            t = threading.Thread(
                target=_process_hid_event,
                args=(event_name, seen_events),
                daemon=True
            )
            t.start()

    except KeyboardInterrupt:
        print("\n" + Colors.YELLOW + "[!] Stopping HID Detection Engine..." + Colors.END)
    except Exception as e:
        print(Colors.RED + f"\n[!] HID monitor error: {e}" + Colors.END)


def auto_install_clamav():
    """Report ClamAV readiness; installation is completed by run.sh."""
    if _clamav_command() is not None:
        return
    print(Colors.RED +
          "[!] ClamAV is unavailable. Run sudo ./run.sh to install and initialize it before scanning." +
          Colors.END)


# ==========================================
# MAIN ENTRY POINT
# ==========================================
if __name__ == "__main__":
    import sys
    
    # ── CLI Arguments ─────────────────────────────────────────────────────
    if "--ui-mode" in sys.argv:
        UI_MODE = True
        sys.stdout = sys.stderr  # Redirect standard prints to stderr to keep stdout clean for JSON IPC
    if "--cli-auto" in sys.argv:
        CLI_AUTO = True
        
    if len(sys.argv) >= 2 and sys.argv[1] == "--history":
        show_history()
        sys.exit(0)
        
    # ── Quarantine Vault CLI ──────────────────────────────────────────────
    if len(sys.argv) >= 2 and sys.argv[1] == "--quarantine":
        action = sys.argv[2] if len(sys.argv) >= 3 else "list"
        
        if action == "list":
            list_quarantine()
        elif action == "restore":
            entries = list_quarantine()
            if entries:
                try:
                    idx = int(input(Colors.YELLOW + "Enter the number of the file to restore: " + Colors.END))
                    confirm = input("A clean rescan is required. Type RESTORE to continue: ").strip()
                    if confirm == "RESTORE":
                        restore_from_quarantine(idx)
                    else:
                        print("Cancelled.")
                except (ValueError, KeyboardInterrupt):
                    print("\nCancelled.")
        elif action == "delete":
            entries = list_quarantine()
            if entries:
                try:
                    idx = int(input("Enter the number of the file to permanently delete: "))
                    confirm = input("Type DELETE to confirm permanent deletion: ").strip()
                    if confirm == "DELETE":
                        delete_quarantine_entry(idx)
                    else:
                        print("Cancelled.")
                except (ValueError, KeyboardInterrupt):
                    print("\nCancelled.")
        elif action == "purge":
            entries = list_quarantine()
            if entries:
                confirm = input(Colors.RED + Colors.BOLD + 
                    f"Are you sure you want to PERMANENTLY DELETE all {len(entries)} quarantined file(s)? (yes/no): " + 
                    Colors.END).strip().lower()
                if confirm == "yes":
                    purge_quarantine()
                else:
                    print("Cancelled.")
        else:
            print("Usage: python3 changed.py --quarantine [list|restore|delete|purge]")
        sys.exit(0)
    
    # ── Normal USB monitoring mode ────────────────────────────────────────
    db_path = ensure_database()
    
    # Ensure required directories exist
    os.makedirs(QUARANTINE_DIR, exist_ok=True)
    _fix_file_ownership(QUARANTINE_DIR)
    
    # Initialize components
    load_whitelist()
    start_email_worker()
    get_ipc_server().start()
    
    print(Colors.GREEN + f"[*] Malware database: {db_path}" + Colors.END)
    print(Colors.GREEN + f"[*] HID whitelist: {len(HID_WHITELIST)} trusted device(s)" + Colors.END)
    
    # Ensure ClamAV is installed (Raspberry Pi auto-install)
    auto_install_clamav()
    if _clamav_command() is None:
        queue_operational_email("clamav-unavailable", "USB Scanner engine unavailable: ClamAV",
                                "ClamAV is unavailable. Storage cannot receive a clean verdict.")
    if load_yara_rules() is None:
        queue_operational_email("yara-unavailable", "USB Scanner engine unavailable: YARA",
                                "YARA rules did not compile. Review the service logs and preflight output.")
    
    # Show quarantine vault status
    if os.path.exists(QUARANTINE_LOG):
        try:
            with open(QUARANTINE_LOG, "r") as f:
                q_entries = json.load(f)
            if q_entries:
                print(Colors.YELLOW + f"[*] Quarantine vault: {len(q_entries)} file(s) stored" + Colors.END)
        except Exception:
            pass
    
    if not is_root_user():
        print(Colors.YELLOW +
              "[!] Not running as root. USB storage can be scanned, but accept/block enforcement requires: sudo ./run.sh" +
              Colors.END)
    if FPDF is None:
        print(Colors.YELLOW +
              "[!] fpdf2 not installed — PDF reports disabled. " 
              "Run: .venv/bin/pip install -r requirements.txt" +
              Colors.END)
    threading.Thread(target=device_worker, daemon=True).start()
    readiness = {
        "clamav": _clamav_command() is not None,
        "yara": load_yara_rules() is not None,
        "root": is_root_user(),
        "usbguard": shutil.which("usbguard") is not None,
    }
    emit_ui_event("backend_ready", readiness)
    if UI_MODE:
        threading.Thread(target=ui_command_reader, daemon=True).start()
    # USBGuard is the primary CLI HID barrier and blocks before driver binding.
    # The legacy event-node monitor remains available for future UI diagnostics.
    if not CLI_AUTO:
        hid_thread = threading.Thread(target=hid_monitor, daemon=True)
        hid_thread.start()
    monitor_usb()
