"""USB device monitoring entrypoint for the backend scanner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TextIO
import sys

from backend.models.scan import DeviceInfo
from backend.services.scan_service import ScanService

try:
    import pyudev
except ImportError:  # pragma: no cover - pyudev is platform dependent
    pyudev = None


@dataclass(slots=True)
class USBMonitor:
    """Watch for USB storage insertions and trigger scans."""

    scan_service: ScanService
    output: TextIO = sys.stdout

    def monitor(self) -> None:
        if pyudev is None:
            raise RuntimeError("pyudev is required to monitor USB devices")

        print("[*] Waiting for USB storage device...", file=self.output)
        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by(subsystem="block")

        try:
            for device in iter(monitor.poll, None):
                if device.action != "add" or device.device_type != "partition":
                    continue
                if device.get("ID_BUS") != "usb":
                    continue

                parent = device.parent
                vendor = parent.get("ID_VENDOR", "Unknown") if parent is not None else "Unknown"
                model = parent.get("ID_MODEL", "Unknown") if parent is not None else "Unknown"
                serial = parent.get("ID_SERIAL_SHORT", "Unknown") if parent is not None else "Unknown"
                node = device.device_node or ""

                print("", file=self.output)
                print("[+] USB Storage Partition Detected", file=self.output)
                print("--- Device Information ---", file=self.output)
                print(f"Vendor : {vendor}", file=self.output)
                print(f"Model  : {model}", file=self.output)
                print(f"Serial : {serial}", file=self.output)
                print(f"Node   : {node}", file=self.output)

                mount_path = self.scan_service.wait_for_mount(node)
                if not mount_path:
                    print("[!] Could not detect mount path automatically.", file=self.output)
                    continue

                print(f"[+] Mounted at: {mount_path}", file=self.output)
                print("[*] Starting full scan... please wait.", file=self.output)

                report = self.scan_service.scan_mount_path(
                    mount_path,
                    device=DeviceInfo(vendor=vendor, model=model, serial=serial, node=node),
                )
                print(self.scan_service.format_text_report(report), file=self.output)
                print("=" * 60, file=self.output)
        except KeyboardInterrupt:
            print("[!] Scan interrupted by user. Exiting gracefully...", file=self.output)


def monitor_usb(scan_service: ScanService) -> None:
    USBMonitor(scan_service).monitor()


def main(scan_service: ScanService) -> int:
    monitor_usb(scan_service)
    return 0