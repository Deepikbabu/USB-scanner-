import pyudev
import os
import time
import sqlite3
import hashlib
from datetime import datetime
import threading

# ==========================================
# TERMINAL COLORS
# ==========================================
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"

# ==========================================
# DATABASE CONFIG
# ==========================================
DB_NAME = os.path.join(os.path.dirname(__file__), "test_malware.db")

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
        if result:
            return {"signature": result[0], "severity": result[1]}
        return None
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
    except:
        return None

# ==========================================
# DESCRIPTOR ANALYZER
# ==========================================
def analyze_descriptors(device):
    return {
        "vendor": device.get("ID_VENDOR", "Unknown"),
        "model": device.get("ID_MODEL", "Unknown"),
        "serial": device.get("ID_SERIAL_SHORT", "Unknown"),
        "vid": device.get("ID_VENDOR_ID", "Unknown"),
        "pid": device.get("ID_MODEL_ID", "Unknown"),
        "subsystem": device.properties.get("SUBSYSTEM"),
        "usb_class": device.get("ID_USB_CLASS_FROM_DATABASE", "Unknown"),
        "usb_driver": device.get("ID_USB_DRIVER", "Unknown")
    }

# ==========================================
# STRUCTURAL RULE ENGINE
# ==========================================
def structural_rules(descriptor):
    risk = 0
    flags = []

    if descriptor["serial"] == "Unknown":
        risk += 1
        flags.append("Missing serial number")

    return risk, flags

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
    except:
        pass
    return None

def wait_for_mount(device_node, timeout=15):
    for _ in range(timeout):
        time.sleep(1)
        mount = find_mount_point(device_node)
        if mount and os.path.exists(mount):
            return mount
    return None

def scan_storage(mount_path):
    print(Colors.CYAN + Colors.BOLD +
          "\n[ SCANNING ] Analyzing file system...\n" +
          Colors.END)

    suspicious_extensions = [".exe", ".bat", ".ps1", ".vbs", ".scr"]
    risk_score = 0
    malware_detected = False

    try:
        for root, dirs, files in os.walk(mount_path):
            for file in files:
                path = os.path.join(root, file)
                lower = file.lower()

                print(f"Scanning: {path}", end="\r")

                if any(lower.endswith(ext) for ext in suspicious_extensions):
                    risk_score += 3

                if lower == "autorun.inf":
                    risk_score += 5

                if file.startswith("."):
                    risk_score += 1

                sha = calculate_sha256(path)
                if sha:
                    result = check_hash(sha)
                    if result:
                        malware_detected = True
                        print("\n" + Colors.RED + Colors.BOLD +
                              f"[ MALWARE DETECTED ] {result['signature']} -> {path}" +
                              Colors.END)
                        risk_score += 10
    except Exception as e:
        print(f"\nError during scan: {e}")
    
    # Clear the scanning line
    print(" " * 80, end="\r")
    
    return risk_score, malware_detected

# ==========================================
# THREAT LEVEL
# ==========================================
def threat_level(score):
    if score >= 15:
        return Colors.RED + Colors.BOLD + "HIGH" + Colors.END
    elif score >= 7:
        return Colors.YELLOW + Colors.BOLD + "MEDIUM" + Colors.END
    elif score > 0:
        return Colors.GREEN + Colors.BOLD + "LOW" + Colors.END
    else:
        return Colors.BLUE + Colors.BOLD + "CLEAN" + Colors.END

# ==========================================
# USB DEVICE HANDLER
# ==========================================
def handle_usb_device(device):
    """Handle USB device insertion in a separate thread"""
    try:
        print(Colors.CYAN + "\n[ EVENT ] USB Device Detected - Analyzing..." + Colors.END)
        
        # Small delay to let the system register all partitions
        time.sleep(3)
        
        # Get USB device info
        usb_info = analyze_descriptors(device)
        
        # Calculate base risk
        base_risk, flags = structural_rules(usb_info)
        
        # Find and scan storage
        storage_risk = 0
        malware_detected = False
        
        context = pyudev.Context()
        
        # Find all partitions belonging to this USB device
        for block_device in context.list_devices(subsystem='block'):
            if block_device.device_type == 'partition':
                # Check if this partition belongs to our USB device
                parent = block_device.find_parent('usb', 'usb_device')
                if parent and parent.device_path == device.device_path:
                    print(Colors.CYAN + f"[*] Found partition: {block_device.device_node}" + Colors.END)
                    
                    mount = wait_for_mount(block_device.device_node)
                    
                    if mount:
                        print(f"[+] Mounted at {mount}")
                        part_risk, part_malware = scan_storage(mount)
                        storage_risk += part_risk
                        if part_malware:
                            malware_detected = True
                    else:
                        print(Colors.YELLOW + f"[!] Mount not found for {block_device.device_node}" + Colors.END)
        
        # Calculate total risk
        total_risk = base_risk + storage_risk
        
        # Generate the complete report
        print("\n" + "━" * 60)
        print(Colors.BOLD + Colors.CYAN +
              "        COMPLETE USB DEVICE SECURITY REPORT        " +
              Colors.END)
        print("━" * 60)
        
        print(f" Time           : {datetime.now()}")
        print(f" Vendor         : {usb_info['vendor']}")
        print(f" Model          : {usb_info['model']}")
        print(f" VID:PID        : {usb_info['vid']}:{usb_info['pid']}")
        print(f" Serial         : {usb_info['serial']}")
        print(f" USB Class      : {usb_info['usb_class']}")
        print(f" USB Driver     : {usb_info['usb_driver']}")
        
        print("\n" + "-" * 60)
        print(f" Hardware Risk  : {base_risk}")
        print(f" Storage Risk   : {storage_risk}")
        print(f" Total Risk     : {total_risk}")
        print(f" Threat Level   : {threat_level(total_risk)}")
        
        if malware_detected:
            print("\n" + Colors.RED + Colors.BOLD +
                  "⚠️  MALWARE DETECTED ON DEVICE ⚠️" +
                  Colors.END)
        
        if flags:
            print("\n Hardware Flags:")
            for f in flags:
                print(f"  • {f}")
        
        print("━" * 60 + "\n")
        print(Colors.GREEN + "[✓] Device analysis complete. Ready for next device..." + Colors.END)
        
    except Exception as e:
        print(Colors.RED + f"\n[!] Error handling USB device: {e}" + Colors.END)

# ==========================================
# MAIN MONITOR
# ==========================================
def monitor_usb():
    print(Colors.CYAN + Colors.BOLD +
          "\n[*] Intelligent USB Security Engine Started" +
          Colors.END)
    print(Colors.GREEN + "[*] Monitoring for USB devices... (Press Ctrl+C to stop)\n" + Colors.END)

    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem='usb')
    
    # Start monitoring
    monitor.start()
    
    processed_devices = set()
    
    try:
        for device in iter(monitor.poll, None):
            if device.action == "add" and device.get("DEVTYPE") == "usb_device":
                
                # Create a unique identifier for this device
                device_id = f"{device.get('ID_VENDOR_ID')}:{device.get('ID_MODEL_ID')}:{device.get('ID_SERIAL_SHORT', '')}"
                
                # Check if we've already processed this device
                if device_id in processed_devices:
                    continue
                
                # Add to processed set
                processed_devices.add(device_id)
                
                # Handle the device in a separate thread so the monitor keeps running
                thread = threading.Thread(target=handle_usb_device, args=(device,))
                thread.daemon = True
                thread.start()
                
                # Clean up old entries from processed_devices periodically
                if len(processed_devices) > 100:
                    processed_devices.clear()
                    
    except KeyboardInterrupt:
        print("\n" + Colors.YELLOW +
              "[!] Stopping USB Security Engine..." +
              Colors.END)
        print(Colors.GREEN +
              "[✓] Shutdown complete. Goodbye.\n" +
              Colors.END)

if __name__ == "__main__":
    monitor_usb()