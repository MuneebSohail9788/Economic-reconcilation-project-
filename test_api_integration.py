from pathlib import Path

from fastapi.testclient import TestClient

from app.api.routes import get_service
from app.application.service import AnalysisService
from app.database.session import SessionLocal
from app.domain.enums import Currency, Unit
from app.domain.schemas import EconomicFact, ParsedDocument, SourceLocation
from app.main import app

DB_PATH = Path("economic_truth_engine.db")


class FakeParser:
    def parse(self, document):
        text = Path(document.storage_path).read_text(encoding="utf-8")
        return ParsedDocument(document_id=document.id, document_type=document.document_type, pages={1: text})


class FakeExtractor:
    def extract(self, document):
        doc = document.document_id
        text = document.pages[1]
        if document.document_type.value == "CONTRACT":
            return [EconomicFact(document_id=doc, field_name="line", quantity=100, unit=Unit.HOUR, rate=150, currency=Currency.USD, source=SourceLocation(document_id=doc, page=1, text=text), event_id=f"CONTRACT-{doc}")]
        if document.document_type.value == "AMENDMENT":
            return [EconomicFact(document_id=doc, field_name="line", quantity=20, unit=Unit.HOUR, rate=150, amount=3000, currency=Currency.USD, approved=True, source=SourceLocation(document_id=doc, page=1, text=text), event_id=f"AMENDMENT-{doc}")]
        return [EconomicFact(document_id=doc, field_name="line", quantity=100, unit=Unit.HOUR, rate=150, amount=15000, currency=Currency.USD, invoice_number=f"INV-{doc}", source=SourceLocation(document_id=doc, page=1, text=text))]


def test_full_api_upload_run_and_finding_persistence():
    if DB_PATH.exists():
        DB_PATH.unlink()
    session = SessionLocal()
    service = AnalysisService(session, FakeParser(), FakeExtractor())
    app.dependency_overrides[get_service] = lambda: service
    try:
        with TestClient(app) as client:
            created = client.post("/analyses", json={"name": "Acceptance test"})
            assert created.status_code == 200
            analysis_id = created.json()["id"]

            for filename, doc_type, content in [
                ("contract.pdf", "CONTRACT", b"100 hours at $150/hour"),
                ("amendment.pdf", "AMENDMENT", b"20 additional hours approved"),
                ("invoice.pdf", "INVOICE", b"100 hours billed at $150/hour"),
            ]:
                response = client.post(
                    "/documents",
                    params={"analysis_id": analysis_id, "document_type": doc_type},
                    files={"file": (filename, content, "application/pdf")},
                )
                assert response.status_code == 200, response.text

            run = client.post(f"/analyses/{analysis_id}/run")
            assert run.status_code == 200, run.text
            payload = run.json()
            assert payload["reconciliation_status"] == "CHANGE_VALUE_NOT_CAPTURED"
            assert payload["finding_id"]

            finding = client.get(f"/findings/{payload['finding_id']}")
            assert finding.status_code == 200
            from decimal import Decimal
            assert Decimal(finding.json()["difference"]) == Decimal("3000")
            assert finding.json()["evidence_count"] == 3

            analysis = client.get(f"/analyses/{analysis_id}")
            assert analysis.status_code == 200
            assert analysis.json()["status"] == "FINDINGS_GENERATED"
    finally:
        app.dependency_overrides.clear()
        session.close()
        if DB_PATH.exists():
            DB_PATH.unlink()
