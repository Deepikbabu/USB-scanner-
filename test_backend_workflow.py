from backend.scanner.composite_hid_policy import evaluate
from backend.scanner.workflow import DeviceState, FileSnapshot, Workflow, WorkflowContext, classify_device, manifest_changed
from backend.scanner.linux_adapters import classify_udev_properties
from backend.security.intelligence import device_identity_fingerprint, hardware_fingerprint, interface_fingerprint, manifest_fingerprint
from backend.scanner.advanced_detection import detect_mime, analyze_content
from backend.scanner.remediation import validate_action

def test_storage_classification_and_manifest():
    assert classify_device({"capabilities": ["storage"]}) == "storage"
    one = FileSnapshot("a", 1, 2, "x")
    assert not manifest_changed([one], [one])
    assert manifest_changed([one], [FileSnapshot("a", 2, 2, "x")])

def test_phase1_classifies_hid_composite_and_unknown():
    assert classify_device({"capabilities": ["hid"]}) == "hid"
    assert classify_device({"capabilities": ["hid", "storage"]}) == "composite_hid_storage"
    assert classify_device({"capabilities": []}) == "unknown"
    assert classify_udev_properties({"ID_INPUT_KEYBOARD": "1", "ID_INPUT": "1"})["category"] == "hid"

def test_phase1_fingerprints_are_stable_and_identity_sensitive():
    info = {"vid": "1234", "pid": "5678", "serial": "ABC123", "usbguard_hash": "desc"}
    interfaces = ["08:06:50", "03:01:01"]
    assert hardware_fingerprint(info, interfaces) == hardware_fingerprint(dict(info), list(reversed(interfaces)))
    assert interface_fingerprint(interfaces) == interface_fingerprint(list(reversed(interfaces)))
    assert device_identity_fingerprint(info, interfaces) != device_identity_fingerprint({**info, "serial": "OTHER"}, interfaces)

def test_phase2_content_mime_and_pdf_evidence():
    pdf = b"%PDF-1.7\n1 0 obj << /JavaScript /EmbeddedFile >> endobj"
    assert detect_mime(pdf, "renamed.bin") == "application/pdf"
    result = analyze_content(pdf, "renamed.bin")
    assert "PDF JavaScript present" in result["evidence"]
    assert "PDF embedded object present" in result["evidence"]

def test_phase3_manifest_fingerprint_detects_content_drift():
    baseline = [{"relative_path": "docs/a.txt", "size": 3, "mtime_ns": 10, "sha256": "aaa"}]
    assert manifest_fingerprint(baseline) == manifest_fingerprint(list(reversed(baseline)))
    changed = [{**baseline[0], "sha256": "bbb"}]
    assert manifest_fingerprint(baseline) != manifest_fingerprint(changed)

def test_phase4_delete_requires_typed_confirmation():
    assert not validate_action("delete", typed_confirmation="delete")[0]
    assert validate_action("delete", typed_confirmation="DELETE")[0]
    assert not validate_action("unknown")[0]

def test_composite_requires_typed_confirmation():
    result = evaluate({"hid", "storage"}, challenge="APPROVE 123")
    assert result["minimum_verdict"] == "SUSPICIOUS"
    assert result["hid_allowed"] is False
    assert evaluate({"hid", "storage"}, typed_confirmation="APPROVE 123", challenge="APPROVE 123")["hid_allowed"]

def test_workflow_fails_closed_on_isolation():
    workflow = Workflow(isolate=lambda _: False, scan=lambda *_: ([], [], True),
                        reverify=lambda *_: True, release=lambda _: True)
    result = workflow.run(WorkflowContext({"capabilities": ["storage"]}))
    assert result.state == DeviceState.BLOCKED
