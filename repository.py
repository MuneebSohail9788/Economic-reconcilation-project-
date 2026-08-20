from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import (
    AnalysisDB,
    AnalysisRunDB,
    DocumentDB,
    EconomicFactDB,
    EconomicModelDB,
    EvidenceLinkDB,
    FindingDB,
    ParsedDocumentDB,
    ReconciliationResultDB,
)
from app.domain.enums import AnalysisStatus, Currency, DocumentType, FindingStatus, ReconciliationStatus, Unit
from app.domain.schemas import (
    Analysis,
    DocumentRef,
    EconomicFact,
    EconomicModel,
    EvidenceLink,
    Finding,
    ParsedDocument,
    ReconciliationResult,
    SourceLocation,
)


class AnalysisRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, name: str) -> Analysis:
        row = AnalysisDB(name=name, status=AnalysisStatus.CREATED.value, retry_count=0)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self.to_domain(row)

    def get(self, analysis_id: UUID) -> Analysis | None:
        row = self.db.get(AnalysisDB, analysis_id)
        return self.to_domain(row) if row else None

    def set_status(self, analysis_id: UUID, status: AnalysisStatus) -> Analysis | None:
        row = self.db.get(AnalysisDB, analysis_id)
        if row is None:
            return None
        row.status = status.value
        row.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(row)
        return self.to_domain(row)

    def increment_retry(self, analysis_id: UUID) -> int:
        row = self.db.get(AnalysisDB, analysis_id)
        if row is None:
            raise ValueError("Analysis not found")
        row.retry_count += 1
        self.db.commit()
        self.db.refresh(row)
        return row.retry_count

    @staticmethod
    def to_domain(row: AnalysisDB) -> Analysis:
        return Analysis(id=row.id, name=row.name, status=row.status, retry_count=row.retry_count)


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, ref: DocumentRef) -> DocumentRef:
        self.db.add(DocumentDB(
            id=ref.id, analysis_id=ref.analysis_id, filename=ref.filename,
            sha256=ref.sha256, document_type=ref.document_type.value,
            storage_path=ref.storage_path,
        ))
        self.db.commit()
        return ref

    def list_for_analysis(self, analysis_id: UUID) -> Sequence[DocumentDB]:
        return self.db.scalars(
            select(DocumentDB).where(DocumentDB.analysis_id == analysis_id).order_by(DocumentDB.created_at)
        ).all()

    def duplicate_exists(self, analysis_id: UUID, sha256: str) -> bool:
        return self.db.scalar(select(DocumentDB.id).where(
            DocumentDB.analysis_id == analysis_id,
            DocumentDB.sha256 == sha256,
        )) is not None

    @staticmethod
    def to_ref(row: DocumentDB) -> DocumentRef:
        return DocumentRef(
            id=row.id,
            analysis_id=row.analysis_id,
            filename=row.filename,
            sha256=row.sha256,
            document_type=DocumentType(row.document_type),
            storage_path=row.storage_path,
        )


class RunRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, analysis_id: UUID, attempt: int) -> AnalysisRunDB:
        row = AnalysisRunDB(analysis_id=analysis_id, attempt=attempt, status=AnalysisStatus.CREATED.value)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def finish(self, run_id: UUID, status: AnalysisStatus, error_code: str | None = None, error_message: str | None = None) -> None:
        row = self.db.get(AnalysisRunDB, run_id)
        if row is None:
            return
        row.status = status.value
        row.error_code = error_code
        row.error_message = error_message
        row.finished_at = datetime.now(timezone.utc)
        self.db.commit()

    def list_for_analysis(self, analysis_id: UUID) -> Sequence[AnalysisRunDB]:
        return self.db.scalars(
            select(AnalysisRunDB).where(AnalysisRunDB.analysis_id == analysis_id).order_by(AnalysisRunDB.attempt)
        ).all()


def save_parsed_document(db: Session, parsed: ParsedDocument, parser_name: str) -> None:
    row = db.scalar(select(ParsedDocumentDB).where(ParsedDocumentDB.document_id == parsed.document_id))
    payload = json.dumps({str(k): v for k, v in parsed.pages.items()}, ensure_ascii=False)
    if row is None:
        db.add(ParsedDocumentDB(document_id=parsed.document_id, parser_name=parser_name, pages_json=payload))
    else:
        row.parser_name = parser_name
        row.pages_json = payload
    db.commit()


def save_facts(db: Session, facts: list[EconomicFact]) -> None:
    for f in facts:
        db.merge(EconomicFactDB(
            id=f.id, document_id=f.document_id, field_name=f.field_name,
            quantity=f.quantity, rate=f.rate, amount=f.amount,
            currency=f.currency.value if f.currency else None,
            unit=f.unit.value if f.unit else None,
            page=f.source.page, source_text=f.source.text, locator=f.source.locator,
            extraction_confidence=f.extraction_confidence, event_id=f.event_id,
            external_reference=f.external_reference, invoice_number=f.invoice_number,
            effective_date=f.effective_date, approved=f.approved, canceled=f.canceled,
        ))
    db.commit()


def save_model(db: Session, analysis_id: UUID, model: EconomicModel) -> None:
    row = db.scalar(select(EconomicModelDB).where(EconomicModelDB.analysis_id == analysis_id))
    values = dict(
        base_entitlement=model.base_entitlement,
        amendment_entitlement=model.amendment_entitlement,
        delivered_entitlement=model.delivered_entitlement,
        expected_entitlement=model.expected_entitlement,
        captured_amount=model.captured_amount,
        currency=model.currency.value if model.currency else None,
    )
    if row is None:
        db.add(EconomicModelDB(analysis_id=analysis_id, **values))
    else:
        for key, value in values.items():
            setattr(row, key, value)
    db.commit()


def save_reconciliation(db: Session, analysis_id: UUID, result: ReconciliationResult) -> UUID:
    row = ReconciliationResultDB(
        analysis_id=analysis_id, status=result.status.value, expected=result.expected,
        actual=result.actual, difference=result.difference, reason=result.reason,
        evidence_sufficient=result.evidence_sufficient,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row.id


def save_finding(db: Session, analysis_id: UUID, finding: Finding, facts: list[EconomicFact] | None = None) -> None:
    db.add(FindingDB(
        id=finding.id, analysis_id=analysis_id, status=finding.status.value,
        rule_code=finding.rule_code.value, expected=finding.expected,
        captured=finding.captured, difference=finding.difference,
        reason=finding.reason, extraction_confidence=finding.extraction_confidence,
        currency=finding.currency.value if finding.currency else None,
    ))
    facts = facts or []
    for source in finding.evidence:
        matching = next((f for f in facts if f.source == source), None)
        db.add(EvidenceLinkDB(
            finding_id=finding.id, fact_id=matching.id if matching else None, document_id=source.document_id,
            page=source.page, source_text=source.text, locator=source.locator,
        ))
    db.commit()


def get_finding(db: Session, finding_id: UUID) -> Finding | None:
    row = db.get(FindingDB, finding_id)
    if row is None:
        return None
    links = db.scalars(select(EvidenceLinkDB).where(EvidenceLinkDB.finding_id == finding_id)).all()
    evidence = [SourceLocation(document_id=x.document_id, page=x.page, text=x.source_text, locator=x.locator) for x in links]
    return Finding(
        id=row.id,
        status=FindingStatus(row.status),
        rule_code=ReconciliationStatus(row.rule_code),
        expected=row.expected,
        captured=row.captured,
        difference=row.difference,
        reason=row.reason,
        evidence=evidence,
        extraction_confidence=row.extraction_confidence,
        currency=Currency(row.currency) if row.currency else None,
    )
