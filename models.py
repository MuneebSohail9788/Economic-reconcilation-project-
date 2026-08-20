from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AnalysisDB(Base):
    __tablename__ = "analyses"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(50), default="CREATED", index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DocumentDB(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("analysis_id", "sha256", name="uq_documents_analysis_sha256"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    analysis_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("analyses.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    document_type: Mapped[str] = mapped_column(String(40))
    storage_path: Mapped[str] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ParsedDocumentDB(Base):
    __tablename__ = "parsed_documents"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("documents.id"), unique=True, index=True)
    parser_name: Mapped[str] = mapped_column(String(100))
    pages_json: Mapped[str] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EconomicFactDB(Base):
    __tablename__ = "economic_facts"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("documents.id"), index=True)
    field_name: Mapped[str] = mapped_column(String(100))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(30, 12), nullable=True)
    rate: Mapped[Decimal | None] = mapped_column(Numeric(30, 12), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(30, 12), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    page: Mapped[int] = mapped_column(Integer)
    source_text: Mapped[str] = mapped_column(Text())
    locator: Mapped[str | None] = mapped_column(Text(), nullable=True)
    extraction_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    effective_date: Mapped[object | None] = mapped_column(Date, nullable=True)
    approved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    canceled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EconomicModelDB(Base):
    __tablename__ = "economic_models"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    analysis_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("analyses.id"), unique=True, index=True)
    base_entitlement: Mapped[Decimal] = mapped_column(Numeric(30, 12))
    amendment_entitlement: Mapped[Decimal] = mapped_column(Numeric(30, 12))
    delivered_entitlement: Mapped[Decimal] = mapped_column(Numeric(30, 12))
    expected_entitlement: Mapped[Decimal] = mapped_column(Numeric(30, 12))
    captured_amount: Mapped[Decimal] = mapped_column(Numeric(30, 12))
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)


class ReconciliationResultDB(Base):
    __tablename__ = "reconciliation_results"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    analysis_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("analyses.id"), index=True)
    status: Mapped[str] = mapped_column(String(80))
    expected: Mapped[Decimal] = mapped_column(Numeric(30, 12))
    actual: Mapped[Decimal] = mapped_column(Numeric(30, 12))
    difference: Mapped[Decimal] = mapped_column(Numeric(30, 12))
    reason: Mapped[str] = mapped_column(Text())
    evidence_sufficient: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AnalysisRunDB(Base):
    __tablename__ = "analysis_runs"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    analysis_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("analyses.id"), index=True)
    attempt: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50))
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EvidenceLinkDB(Base):
    __tablename__ = "evidence_links"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    finding_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("findings.id"), index=True)
    fact_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("economic_facts.id"), nullable=True)
    document_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("documents.id"), index=True)
    page: Mapped[int] = mapped_column(Integer)
    source_text: Mapped[str] = mapped_column(Text())
    locator: Mapped[str | None] = mapped_column(Text(), nullable=True)


class FindingDB(Base):
    __tablename__ = "findings"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    analysis_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("analyses.id"), index=True)
    status: Mapped[str] = mapped_column(String(40))
    rule_code: Mapped[str] = mapped_column(String(80))
    expected: Mapped[Decimal] = mapped_column(Numeric(30, 12))
    captured: Mapped[Decimal] = mapped_column(Numeric(30, 12))
    difference: Mapped[Decimal] = mapped_column(Numeric(30, 12))
    reason: Mapped[str] = mapped_column(Text())
    extraction_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
