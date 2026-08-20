import json
from pathlib import Path


def test_golden_dataset_has_60_locked_cases():
    data = json.loads(Path("tests/fixtures/golden_dataset.json").read_text())
    assert len(data["cases"]) == 60
    assert data["cases"][0]["id"] == "TC-001"
    assert data["cases"][-1]["id"] == "TC-060"


def test_adversarial_dataset_has_10_locked_cases():
    data = json.loads(Path("tests/fixtures/adversarial_cases.json").read_text())
    assert len(data) == 10
    assert data[0]["id"] == "ADV-001"
    assert data[-1]["id"] == "ADV-010"
