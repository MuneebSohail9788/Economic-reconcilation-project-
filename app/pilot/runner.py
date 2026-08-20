from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.application.service import AnalysisService
from app.database.base import Base
from app.database.repository import AnalysisRepository, DocumentRepository, get_finding
from app.domain.enums import Currency, DocumentType, ReconciliationStatus, Unit
from app.domain.schemas import EconomicFact, ParsedDocument, SourceLocation
from app.extraction.interfaces import FactExtractor
from app.pilot.parser import PilotFileParser


@dataclass(frozen=True)
class PilotExpectation:
    expected: Decimal
    captured: Decimal
    difference: Decimal
    status: ReconciliationStatus


@dataclass(frozen=True)
class PilotRunReport:
    analysis_id: UUID
    finding_id: UUID | None
    status: str
    reconciliation_status: ReconciliationStatus
    expected: Decimal
    captured: Decimal
    difference: Decimal
    documents_parsed: int
    facts_extracted: int


class ControlledPilotExtractor(FactExtractor):
    """Deterministic extractor for the synthetic pilot documents.

    It is intentionally not a production AI substitute. Its role is to validate
    the real parser, provenance checks, economic model and persistence path with
    known source facts before connecting a paid/remote AI provider.
    """

    def extract(self, document: ParsedDocument) -> list[EconomicFact]:
        page = document.pages[1]
        doc_id = document.document_id
        if document.document_type == DocumentType.CONTRACT:
            return [EconomicFact(
                document_id=doc_id,
                field_name="base_line",
                quantity=Decimal("100"),
                unit=Unit.HOUR,
                rate=Decimal("150"),
                currency=Currency.USD,
                source=SourceLocation(document_id=doc_id, page=1, text="100 hours at USD 150 per hour"),
                extraction_confidence=Decimal("1.0"),
                event_id="PILOT-CONTRACT-001",
            )]
        if document.document_type == DocumentType.AMENDMENT:
            return [EconomicFact(
                document_id=doc_id,
                field_name="approved_change",
                quantity=Decimal("20"),
                unit=Unit.HOUR,
                rate=Decimal("150"),
                amount=Decimal("3000"),
                currency=Currency.USD,
                source=SourceLocation(document_id=doc_id, page=1, text="20 hours at USD 150 per hour"),
                extraction_confidence=Decimal("1.0"),
                event_id="PILOT-AMENDMENT-001",
                approved=True,
            )]
        if document.document_type == DocumentType.INVOICE:
            return [EconomicFact(
                document_id=doc_id,
                field_name="invoice_line",
                quantity=Decimal("100"),
                unit=Unit.HOUR,
                rate=Decimal("150"),
                amount=Decimal("15000"),
                currency=Currency.USD,
                source=SourceLocation(document_id=doc_id, page=1, text="Rate: USD 150 per hour"),
                extraction_confidence=Decimal("1.0"),
                invoice_number="PILOT-INV-001",
                external_reference="PILOT-INVOICE-001",
            )]
        raise ValueError(f"Unsupported pilot document type: {document.document_type}")


def run_controlled_pilot(
    fixture_dir: Path,
    expected: PilotExpectation | None = None,
) -> PilotRunReport:
    expected = expected or PilotExpectation(
        expected=Decimal("18000"),
        captured=Decimal("15000"),
        difference=Decimal("3000"),
        status=ReconciliationStatus.CHANGE_VALUE_NOT_CAPTURED,
    )
    with TemporaryDirectory(prefix="ete-pilot-") as temp_dir:
        db_path = Path(temp_dir) / "pilot.db"
        storage_dir = Path(temp_dir) / "storage"
        storage_dir.mkdir()
        engine = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            service = AnalysisService(db, PilotFileParser(), ControlledPilotExtractor())
            analysis = service.create_analysis("Mission 007 Controlled Pilot")
            fixtures = [
                (fixture_dir / "pilot_contract.pdf", DocumentType.CONTRACT),
                (fixture_dir / "pilot_amendment.pdf", DocumentType.AMENDMENT),
                (fixture_dir / "pilot_invoice.docx", DocumentType.INVOICE),
            ]
            documents = []
            for path, doc_type in fixtures:
                documents.append(service.upload_document(analysis.id, path.name, path.read_bytes(), doc_type))
            execution = service.run(analysis.id)
            finding = get_finding(db, execution.pipeline.finding.id) if execution.pipeline.finding else None
            if execution.pipeline.reconciliation.status != expected.status:
                raise AssertionError(f"Unexpected reconciliation status: {execution.pipeline.reconciliation.status}")
            if execution.pipeline.reconciliation.expected != expected.expected:
                raise AssertionError("Unexpected expected entitlement")
            if execution.pipeline.reconciliation.actual != expected.captured:
                raise AssertionError("Unexpected captured amount")
            if execution.pipeline.reconciliation.difference != expected.difference:
                raise AssertionError("Unexpected financial difference")
            if finding is None:
                raise AssertionError("Expected finding was not persisted")
            return PilotRunReport(
                analysis_id=analysis.id,
                finding_id=finding.id,
                status=execution.pipeline.status.value,
                reconciliation_status=execution.pipeline.reconciliation.status,
                expected=execution.pipeline.reconciliation.expected,
                captured=execution.pipeline.reconciliation.actual,
                difference=execution.pipeline.reconciliation.difference,
                documents_parsed=len(documents),
                facts_extracted=len(execution.pipeline.normalized_facts),
            )
