from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import Currency, DocumentType, ReconciliationStatus


class CreateAnalysisRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class CreateAnalysisResponse(BaseModel):
    id: UUID
    name: str
    status: str
    retry_count: int = 0


class DocumentResponse(BaseModel):
    id: UUID
    analysis_id: UUID | None
    filename: str
    sha256: str
    document_type: DocumentType
    storage_path: str


class RunResponse(BaseModel):
    run_id: UUID
    analysis_id: UUID
    attempt: int
    analysis_status: str
    reconciliation_status: ReconciliationStatus
    finding_id: UUID | None = None
    message: str


class FindingResponse(BaseModel):
    id: UUID
    status: str
    rule_code: ReconciliationStatus
    expected: Decimal
    captured: Decimal
    difference: Decimal
    reason: str
    evidence_count: int
    currency: Currency | None = None


class RunHistoryItem(BaseModel):
    id: UUID
    attempt: int
    status: str
    error_code: str | None = None
    error_message: str | None = None
