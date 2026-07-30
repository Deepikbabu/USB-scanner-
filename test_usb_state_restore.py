import json
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.scanner import usb_state_restore as restore

ARTIFACT = Path(__file__).resolve().parent / ".artifacts" / "usb-restore-test.json"


def device(device_id="7", port="1-2", digest="trusted-hash"):
    return {
        "usbguard_id": device_id, "state": "block", "vid": "046d", "pid": "c077",
        "vid_pid": "046d:c077", "serial": "mouse-1", "name": "USB Mouse",
        "port": port, "hash": digest, "interfaces": ["03"],
    }


class USBStateRestoreTests(unittest.TestCase):
    def setUp(self):
        ARTIFACT.parent.mkdir(exist_ok=True)
        ARTIFACT.write_text(json.dumps({
            "schema": 1, "clean_shutdown": False,
            "hid_devices": [{**device(), "state": "allow",
                             "sysfs_authorized": True, "was_working": True}],
        }), encoding="utf-8")

    def tearDown(self):
        ARTIFACT.unlink(missing_ok=True)

    def test_exact_preexisting_mouse_is_restored(self):
        with patch.object(restore, "state_path", return_value=ARTIFACT), \
                patch.object(restore, "_list_devices", return_value=[device()]), \
                patch.object(restore, "usbguard_set_state", return_value=True) as guard, \
                patch.object(restore, "authorize_sysfs", return_value=True) as sysfs:
            result = restore.restore_startup_state()
        self.assertEqual(result["restored"], ["046d:c077"])
        guard.assert_called_once_with("7", True)
        sysfs.assert_called_once_with("1-2", True)

    def test_changed_fingerprint_is_not_restored(self):
        changed = device(digest="attacker-hash")
        with patch.object(restore, "state_path", return_value=ARTIFACT), \
                patch.object(restore, "_list_devices", return_value=[changed]), \
                patch.object(restore, "_signed_trust_verified", return_value=False), \
                patch.object(restore, "usbguard_set_state") as guard:
            result = restore.restore_startup_state()
        self.assertEqual(result["restored"], [])
        self.assertEqual(result["preserved_blocked"], ["046d:c077"])
        guard.assert_not_called()

    def test_dangerous_port_is_never_restored(self):
        with patch.object(restore, "state_path", return_value=ARTIFACT), \
                patch.object(restore, "_list_devices", return_value=[device()]), \
                patch.object(restore, "usbguard_set_state") as guard:
            result = restore.restore_startup_state({"1-2"})
        self.assertEqual(result["restored"], [])
        self.assertEqual(result["preserved_blocked"], ["046d:c077"])
        guard.assert_not_called()

    def test_exact_startup_hid_is_protected_for_runtime_continuity(self):
        with patch.object(restore, "state_path", return_value=ARTIFACT):
            self.assertTrue(restore.is_preexisting_working_hid(device()))

    def test_changed_runtime_hid_is_not_protected(self):
        with patch.object(restore, "state_path", return_value=ARTIFACT):
            self.assertFalse(
                restore.is_preexisting_working_hid(device(digest="attacker-hash"))
            )


if __name__ == "__main__":
    unittest.main()
