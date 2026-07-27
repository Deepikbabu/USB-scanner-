import os
from importlib import import_module
os.chdir(os.getcwd())
changed = import_module('changed')
print('FPDF module/class:', changed.FPDF)
changed.generate_pdf_report(
    usb_info={
        'vendor': 'TestVendor',
        'model': 'TestModel',
        'vid': 'abcd',
        'pid': '1234',
        'serial': '123456',
        'usb_class': 'Mass Storage',
        'usb_driver': 'usb-storage',
    },
    base_risk=1,
    storage_risk=2,
    total_risk=3,
    malware_detected=False,
    flags=['flag'],
)
print('Completed')
