from backend.scanner.composite_hid_policy import evaluate
from backend.scanner.workflow import DeviceState, FileSnapshot, Workflow, WorkflowContext, classify_device, manifest_changed

def test_storage_classification_and_manifest():
    assert classify_device({"capabilities": ["storage"]}) == "storage"
    one = FileSnapshot("a", 1, 2, "x")
    assert not manifest_changed([one], [one])
    assert manifest_changed([one], [FileSnapshot("a", 2, 2, "x")])

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
