from decimal import Decimal
from uuid import UUID, uuid4
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import Currency, DocumentType, FindingStatus, ReconciliationStatus, Unit


class SourceLocation(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: UUID
    page: int = Field(ge=1)
    text: str = Field(min_length=1)
    locator: str | None = None


class EconomicFact(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    field_name: str
    quantity: Decimal | None = None
    unit: Unit | None = None
    rate: Decimal | None = None
    amount: Decimal | None = None
    currency: Currency | None = None
    source: SourceLocation
    extraction_confidence: Decimal | None = Field(default=None, ge=0, le=1)
    event_id: str | None = None
    external_reference: str | None = None
    invoice_number: str | None = None
    effective_date: date | None = None
    approved: bool | None = None
    canceled: bool = False


class NormalizedFact(EconomicFact):
    pass


class ParsedDocument(BaseModel):
    document_id: UUID
    document_type: DocumentType
    pages: dict[int, str]


class EconomicModel(BaseModel):
    base_entitlement: Decimal = Decimal("0")
    amendment_entitlement: Decimal = Decimal("0")
    delivered_entitlement: Decimal = Decimal("0")
    expected_entitlement: Decimal = Decimal("0")
    captured_amount: Decimal = Decimal("0")
    currency: Currency | None = None


class ReconciliationResult(BaseModel):
    status: ReconciliationStatus
    expected: Decimal
    actual: Decimal
    difference: Decimal
    reason: str
    evidence_sufficient: bool


class EvidenceLink(BaseModel):
    finding_id: UUID
    source: SourceLocation
    fact_id: UUID | None = None


class Finding(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    status: FindingStatus
    rule_code: ReconciliationStatus
    expected: Decimal
    captured: Decimal
    difference: Decimal
    reason: str
    evidence: list[SourceLocation]
    extraction_confidence: Decimal | None = None
    currency: Currency | None = None


class DocumentRef(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    analysis_id: UUID | None = None
    filename: str
    sha256: str
    document_type: DocumentType
    storage_path: str


class Analysis(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    status: str = "CREATED"
    retry_count: int = Field(default=0, ge=0)
