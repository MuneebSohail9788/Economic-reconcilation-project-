from decimal import Decimal
from pathlib import Path

from app.domain.enums import ReconciliationStatus
from app.pilot.runner import PilotExpectation, run_controlled_pilot


FIXTURE_DIR = Path(__file__).parent / "pilot_fixtures"


def test_controlled_pilot_runs_real_pdf_docx_through_persistent_pipeline():
    report = run_controlled_pilot(FIXTURE_DIR)
    assert report.status == "FINDINGS_GENERATED"
    assert report.reconciliation_status == ReconciliationStatus.CHANGE_VALUE_NOT_CAPTURED
    assert report.expected == Decimal("18000")
    assert report.captured == Decimal("15000")
    assert report.difference == Decimal("3000")
    assert report.documents_parsed == 3
    assert report.facts_extracted == 3
    assert report.finding_id is not None


def test_controlled_pilot_expectation_is_locked():
    report = run_controlled_pilot(
        FIXTURE_DIR,
        expected=PilotExpectation(
            expected=Decimal("18000"),
            captured=Decimal("15000"),
            difference=Decimal("3000"),
            status=ReconciliationStatus.CHANGE_VALUE_NOT_CAPTURED,
        ),
    )
    assert report.reconciliation_status == ReconciliationStatus.CHANGE_VALUE_NOT_CAPTURED
