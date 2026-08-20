from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.domain.enums import AnalysisStatus, ReconciliationStatus
from app.domain.schemas import EconomicFact, EvidenceLink, Finding, NormalizedFact
from app.domain.state_machine import transition
from app.economic_model.builder import build_model
from app.economic_model.rules import check_quantity_mismatch, check_rate_mismatch, validate_currency_consistency
from app.evidence.engine import collect_evidence_links, required_document_evidence
from app.normalization import normalize_fact
from app.reconciliation.engine import reconcile
from app.reporting.finding import build_finding


@dataclass
class PipelineResult:
    status: AnalysisStatus
    finding: Finding | None
    reconciliation: object
    normalized_facts: list[NormalizedFact]
    model: object
    evidence_links: list[EvidenceLink]


def run_pipeline(
    *,
    contract_facts: list[EconomicFact],
    amendment_facts: list[EconomicFact],
    invoice_facts: list[EconomicFact],
    delivery_facts: list[EconomicFact] | None = None,
) -> PipelineResult:
    delivery_facts = delivery_facts or []
    status = AnalysisStatus.CREATED
    status = transition(status, AnalysisStatus.INGESTED)
    status = transition(status, AnalysisStatus.PARSED)

    all_facts = contract_facts + amendment_facts + invoice_facts + delivery_facts
    normalized: list[NormalizedFact] = [normalize_fact(f) for f in all_facts]
    status = transition(status, AnalysisStatus.EXTRACTED)
    status = transition(status, AnalysisStatus.NORMALIZED)

    currency_conflict = not validate_currency_consistency(contract_facts, amendment_facts, invoice_facts, delivery_facts)

    contract_ids = {f.document_id for f in contract_facts}
    amendment_ids = {f.document_id for f in amendment_facts}
    invoice_ids = {f.document_id for f in invoice_facts}
    delivery_ids = {f.document_id for f in delivery_facts}
    c = [f for f in normalized if f.document_id in contract_ids]
    a = [f for f in normalized if f.document_id in amendment_ids]
    i = [f for f in normalized if f.document_id in invoice_ids]
    d = [f for f in normalized if f.document_id in delivery_ids]

    if currency_conflict:
        from app.domain.schemas import EconomicModel, ReconciliationResult
        model = EconomicModel()
        status = transition(status, AnalysisStatus.MODELED)
        evidence_links = collect_evidence_links(c + a + i + d, finding_id=UUID(int=0))
        result = ReconciliationResult(
            status=ReconciliationStatus.CURRENCY_CONFLICT,
            expected=Decimal("0"), actual=Decimal("0"), difference=Decimal("0"),
            reason="Source documents use conflicting currencies; no silent conversion is permitted.",
            evidence_sufficient=bool(evidence_links),
        )
        evidence_sources = [link.source for link in evidence_links]
        finding = build_finding(result, evidence_sources, normalized)
        if finding is not None:
            evidence_links = collect_evidence_links(c + a + i + d, finding_id=finding.id)
        status = transition(status, AnalysisStatus.RECONCILED)
        status = transition(status, AnalysisStatus.FINDINGS_GENERATED)
        return PipelineResult(status, finding, result, normalized, model, evidence_links)

    model = build_model(c, a, i, d)
    status = transition(status, AnalysisStatus.MODELED)

    require_amendment = model.amendment_entitlement > 0
    require_delivery = model.delivered_entitlement > model.base_entitlement + model.amendment_entitlement
    coverage = required_document_evidence(
        contract_facts=c,
        amendment_facts=a,
        invoice_facts=i,
        delivery_facts=d,
        require_amendment=require_amendment,
        require_delivery=require_delivery,
    )
    evidence_links: list[EvidenceLink] = []
    if coverage.complete:
        finding_id = UUID(int=0)
        evidence_links = collect_evidence_links(c + a + i + d, finding_id=finding_id)

    result = reconcile(
        model,
        evidence_links,
        has_contract=bool(c),
        has_invoice=bool(i),
        has_amendment=bool(a),
        contract_facts=c,
        amendment_facts=a,
        invoice_facts=i,
        delivery_facts=d,
        allow_document_role_rate_mismatch=True,
    )
    rate_result = check_rate_mismatch(c, i) if coverage.complete else None
    qty_result = check_quantity_mismatch(c, i) if coverage.complete else None
    if result.status not in {
        ReconciliationStatus.REVIEW_REQUIRED,
        ReconciliationStatus.DUPLICATE,
        ReconciliationStatus.INSUFFICIENT_EVIDENCE,
    }:
        if rate_result is not None:
            result = rate_result
        elif qty_result is not None:
            result = qty_result

    status = transition(status, AnalysisStatus.RECONCILED)

    evidence_sources = coverage.sources if coverage.complete else []
    finding = build_finding(result, evidence_sources, normalized)
    status = transition(status, AnalysisStatus.FINDINGS_GENERATED)
    if finding is not None:
        evidence_links = collect_evidence_links(c + a + i + d, finding_id=finding.id)
    return PipelineResult(status, finding, result, normalized, model, evidence_links)
