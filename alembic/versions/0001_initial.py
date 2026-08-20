"""Initial Economic Truth Engine schema."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

UUID = sa.Uuid(as_uuid=True)

def upgrade() -> None:
    op.create_table("analyses",
        sa.Column("id", UUID, primary_key=True), sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(50), nullable=False), sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_analyses_status", "analyses", ["status"])
    op.create_table("documents",
        sa.Column("id", UUID, primary_key=True), sa.Column("analysis_id", UUID, sa.ForeignKey("analyses.id"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False), sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("document_type", sa.String(40), nullable=False), sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("analysis_id", "sha256", name="uq_documents_analysis_sha256"))
    op.create_index("ix_documents_analysis_id", "documents", ["analysis_id"])
    op.create_index("ix_documents_sha256", "documents", ["sha256"])
    op.create_table("parsed_documents",
        sa.Column("id", UUID, primary_key=True), sa.Column("document_id", UUID, sa.ForeignKey("documents.id"), nullable=False, unique=True),
        sa.Column("parser_name", sa.String(100), nullable=False), sa.Column("pages_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_parsed_documents_document_id", "parsed_documents", ["document_id"])
    op.create_table("economic_facts",
        sa.Column("id", UUID, primary_key=True), sa.Column("document_id", UUID, sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("field_name", sa.String(100), nullable=False), sa.Column("quantity", sa.Numeric(30,12)),
        sa.Column("rate", sa.Numeric(30,12)), sa.Column("amount", sa.Numeric(30,12)), sa.Column("currency", sa.String(3)),
        sa.Column("unit", sa.String(20)), sa.Column("page", sa.Integer(), nullable=False), sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("locator", sa.Text()), sa.Column("extraction_confidence", sa.Numeric(5,4)), sa.Column("event_id", sa.String(255)),
        sa.Column("external_reference", sa.String(255)), sa.Column("invoice_number", sa.String(255)), sa.Column("effective_date", sa.Date()),
        sa.Column("approved", sa.Boolean()), sa.Column("canceled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_economic_facts_document_id", "economic_facts", ["document_id"])
    op.create_table("economic_models",
        sa.Column("id", UUID, primary_key=True), sa.Column("analysis_id", UUID, sa.ForeignKey("analyses.id"), nullable=False, unique=True),
        sa.Column("base_entitlement", sa.Numeric(30,12), nullable=False), sa.Column("amendment_entitlement", sa.Numeric(30,12), nullable=False),
        sa.Column("delivered_entitlement", sa.Numeric(30,12), nullable=False), sa.Column("expected_entitlement", sa.Numeric(30,12), nullable=False),
        sa.Column("captured_amount", sa.Numeric(30,12), nullable=False), sa.Column("currency", sa.String(3)))
    op.create_index("ix_economic_models_analysis_id", "economic_models", ["analysis_id"])
    op.create_table("reconciliation_results",
        sa.Column("id", UUID, primary_key=True), sa.Column("analysis_id", UUID, sa.ForeignKey("analyses.id"), nullable=False),
        sa.Column("status", sa.String(80), nullable=False), sa.Column("expected", sa.Numeric(30,12), nullable=False),
        sa.Column("actual", sa.Numeric(30,12), nullable=False), sa.Column("difference", sa.Numeric(30,12), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False), sa.Column("evidence_sufficient", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_reconciliation_results_analysis_id", "reconciliation_results", ["analysis_id"])
    op.create_table("analysis_runs",
        sa.Column("id", UUID, primary_key=True), sa.Column("analysis_id", UUID, sa.ForeignKey("analyses.id"), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False), sa.Column("status", sa.String(50), nullable=False),
        sa.Column("error_code", sa.String(80)), sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("finished_at", sa.DateTime(timezone=True)))
    op.create_index("ix_analysis_runs_analysis_id", "analysis_runs", ["analysis_id"])
    op.create_table("findings",
        sa.Column("id", UUID, primary_key=True), sa.Column("analysis_id", UUID, sa.ForeignKey("analyses.id"), nullable=False),
        sa.Column("status", sa.String(40), nullable=False), sa.Column("rule_code", sa.String(80), nullable=False),
        sa.Column("expected", sa.Numeric(30,12), nullable=False), sa.Column("captured", sa.Numeric(30,12), nullable=False),
        sa.Column("difference", sa.Numeric(30,12), nullable=False), sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("extraction_confidence", sa.Numeric(5,4)), sa.Column("currency", sa.String(3)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_findings_analysis_id", "findings", ["analysis_id"])
    op.create_table("evidence_links",
        sa.Column("id", UUID, primary_key=True), sa.Column("finding_id", UUID, sa.ForeignKey("findings.id"), nullable=False),
        sa.Column("fact_id", UUID, sa.ForeignKey("economic_facts.id")), sa.Column("document_id", UUID, sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False), sa.Column("source_text", sa.Text(), nullable=False), sa.Column("locator", sa.Text()))
    op.create_index("ix_evidence_links_finding_id", "evidence_links", ["finding_id"])
    op.create_index("ix_evidence_links_document_id", "evidence_links", ["document_id"])

def downgrade() -> None:
    op.drop_table("evidence_links"); op.drop_table("findings"); op.drop_table("analysis_runs"); op.drop_table("reconciliation_results")
    op.drop_table("economic_models"); op.drop_table("economic_facts"); op.drop_table("parsed_documents"); op.drop_table("documents")
    op.drop_index("ix_analyses_status", table_name="analyses"); op.drop_table("analyses")
