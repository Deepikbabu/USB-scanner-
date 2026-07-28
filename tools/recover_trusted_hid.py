"""Emergency recovery: allow only configured trusted HID VID:PIDs."""
import json
from pathlib import Path
from backend.scanner.hid_policy import recover_trusted_hid

root = Path(__file__).resolve().parents[1]
records = root / 'config' / 'hid_trusted.json'
trusted = set()
try:
    data = json.loads(records.read_text(encoding='utf-8'))
    trusted = {str(x.get('vid_pid', x) if isinstance(x, dict) else x) for x in data}
except (FileNotFoundError, json.JSONDecodeError, OSError):
    pass
print('Recovered trusted HID devices:', ', '.join(recover_trusted_hid(trusted)) or 'none')
