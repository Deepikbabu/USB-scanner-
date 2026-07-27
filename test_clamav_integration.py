import sys
import tempfile
import os
from unittest.mock import MagicMock

# Mock linux-only and missing modules to allow import on Windows
sys.modules['pyudev'] = MagicMock()
sys.modules['fpdf'] = MagicMock()
sys.modules['fcntl'] = MagicMock()

from changed import clamav_scan_file, _clamav_command

def test_clamav():
    print("Testing ClamAV Integration...")
    cmd = _clamav_command()
    print("ClamAV Command found:", cmd)
    
    if not cmd:
        print("ClamAV is not installed or not in PATH. Please install ClamAV and add it to your system PATH to enable scanning.")
        return

    # Create EICAR test file
    eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    path = os.path.join(tempfile.gettempdir(), "eicar_clamav_test.com")
    with open(path, "wb") as f:
        f.write(eicar)

    print(f"\nScanning EICAR test file at {path}...")
    result = clamav_scan_file(path)
    print("Scan Result:", result)

    if os.path.exists(path):
        os.remove(path)

if __name__ == "__main__":
    test_clamav()
