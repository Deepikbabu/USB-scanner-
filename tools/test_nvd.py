"""Check NVD API connectivity without displaying the API key."""
from __future__ import annotations
import json, sys, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.security.intelligence import NVDClient

client = NVDClient()
url = "https://services.nvd.nist.gov/rest/json/cves/2.0?" + urllib.parse.urlencode({"cveId": "CVE-2021-44228"})
headers = {"User-Agent": "usb-scanner/1.0"}
if client.api_key:
    headers["apiKey"] = client.api_key
with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=10) as response:
    payload = json.load(response)
print(f"NVD READY - key={'configured' if client.api_key else 'anonymous public access'} - results={payload.get('totalResults', 0)}")
