from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.database.repository import (
    AnalysisRepository,
    DocumentRepository,
    RunRepository,
    save_facts,
    save_finding,
    save_model,
    save_parsed_document,
    save_reconciliation,
)
from app.domain.enums import AnalysisStatus, DocumentType
from app.domain.schemas import EconomicFact, ParsedDocument
from app.evidence.engine import verify_source_locations
from app.extraction.interfaces import FactExtractor
from app.ingestion.service import ingest_file
from app.parsing.interfaces import DocumentParser
from app.pipeline import PipelineResult, run_pipeline


@dataclass
class AnalysisExecution:
    pipeline: PipelineResult
    document_ids: list[UUID]
    run_id: UUID
    attempt: int


class AnalysisService:
    MAX_RETRIES = 3

    def __init__(self, db: Session, parser: DocumentParser, extractor: FactExtractor):
        self.db = db
        self.parser = parser
        self.extractor = extractor
        self.analyses = AnalysisRepository(db)
        self.documents = DocumentRepository(db)
        self.runs = RunRepository(db)

    def create_analysis(self, name: str):
        return self.analyses.create(name)

    def upload_document(self, analysis_id: UUID, filename: str, content: bytes, document_type: DocumentType):
        analysis = self.analyses.get(analysis_id)
        if analysis is None:
            raise ValueError("Analysis not found")
        if analysis.status in {AnalysisStatus.DEAD.value, AnalysisStatus.FINDINGS_GENERATED.value}:
            raise ValueError(f"Documents cannot be added in state {analysis.status}")
        ref = ingest_file(filename, content, document_type, analysis_id=analysis_id)
        if self.documents.duplicate_exists(analysis_id, ref.sha256):
            Path(ref.storage_path).unlink(missing_ok=True)
            raise ValueError("Duplicate document content for this analysis")
        self.documents.create(ref)
        if analysis.status == AnalysisStatus.CREATED.value:
            self.analyses.set_status(analysis_id, AnalysisStatus.INGESTED)
        return ref

    def retry(self, analysis_id: UUID):
        analysis = self.analyses.get(analysis_id)
        if analysis is None:
            raise ValueError("Analysis not found")
        if analysis.status != AnalysisStatus.FAILED.value:
            raise ValueError(f"Retry is only valid from FAILED, current state is {analysis.status}")
        count = self.analyses.increment_retry(analysis_id)
        if count > self.MAX_RETRIES:
            self.analyses.set_status(analysis_id, AnalysisStatus.DEAD)
            return self.analyses.get(analysis_id)
        self.analyses.set_status(analysis_id, AnalysisStatus.RETRY)
        self.analyses.set_status(analysis_id, AnalysisStatus.CREATED)
        return self.analyses.get(analysis_id)

    def run(self, analysis_id: UUID) -> AnalysisExecution:
        analysis = self.analyses.get(analysis_id)
        if analysis is None:
            raise ValueError("Analysis not found")
        if analysis.status not in {
            AnalysisStatus.CREATED.value,
            AnalysisStatus.INGESTED.value,
        }:
            raise ValueError(f"Analysis cannot run from state {analysis.status}")

        rows = self.documents.list_for_analysis(analysis_id)
        if not rows:
            raise ValueError("No documents uploaded for analysis")

        attempt = analysis.retry_count + 1
        run_row = self.runs.create(analysis_id, attempt)
        contract_facts: list[EconomicFact] = []
        amendment_facts: list[EconomicFact] = []
        invoice_facts: list[EconomicFact] = []
        delivery_facts: list[EconomicFact] = []
        parsed_by_document: dict[UUID, ParsedDocument] = {}

        try:
            self.analyses.set_status(analysis_id, AnalysisStatus.PARSED)
            for row in rows:
                parsed = self.parser.parse(self.documents.to_ref(row))
                parsed_by_document[row.id] = parsed
                save_parsed_document(self.db, parsed, self.parser.__class__.__name__)

            self.analyses.set_status(analysis_id, AnalysisStatus.EXTRACTED)
            for row in rows:
                facts = self.extractor.extract(parsed_by_document[row.id])
                coverage = verify_source_locations(facts, {row.id: parsed_by_document[row.id].pages})
                if not coverage.complete:
                    raise ValueError(coverage.reason)
                save_facts(self.db, facts)
                if row.document_type == DocumentType.CONTRACT.value:
                    contract_facts.extend(facts)
                elif row.document_type == DocumentType.AMENDMENT.value:
                    amendment_facts.extend(facts)
                elif row.document_type == DocumentType.INVOICE.value:
                    invoice_facts.extend(facts)
                elif row.document_type == DocumentType.DELIVERY_RECORD.value:
                    delivery_facts.extend(facts)

            result = run_pipeline(
                contract_facts=contract_facts,
                amendment_facts=amendment_facts,
                invoice_facts=invoice_facts,
                delivery_facts=delivery_facts,
            )
            save_model(self.db, analysis_id, result.model)
            save_reconciliation(self.db, analysis_id, result.reconciliation)
            if result.finding is not None:
                save_finding(self.db, analysis_id, result.finding, result.normalized_facts)

            self.analyses.set_status(analysis_id, result.status)
            self.runs.finish(run_row.id, result.status)
            return AnalysisExecution(result, [r.id for r in rows], run_row.id, attempt)
        except Exception as exc:
            self.analyses.set_status(analysis_id, AnalysisStatus.FAILED)
            self.runs.finish(run_row.id, AnalysisStatus.FAILED, "RUN_FAILED", str(exc))
            raise
