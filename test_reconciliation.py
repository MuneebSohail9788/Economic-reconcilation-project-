from decimal import Decimal
from uuid import uuid4

from app.domain.enums import Currency, ReconciliationStatus, Unit
from app.domain.schemas import EconomicModel, EconomicFact, EvidenceLink, SourceLocation
from app.evidence.engine import collect_evidence
from app.reconciliation.engine import reconcile


def _fact(document_id, page, text, amount):
    return EconomicFact(
        document_id=document_id,
        field_name="amount",
        amount=Decimal(amount),
        currency=Currency.USD,
        source=SourceLocation(document_id=document_id, page=page, text=text),
    )


def test_change_value_not_captured():
    c, a, i = uuid4(), uuid4(), uuid4()
    facts = [
        _fact(c, 7, "$15,000 base entitlement", "15000"),
        _fact(a, 2, "+$3,000 approved amendment", "3000"),
        _fact(i, 1, "$15,000 invoiced", "15000"),
    ]
    evidence = [EvidenceLink(finding_id=uuid4(), source=f.source, fact_id=f.id) for f in facts]
    model = EconomicModel(
        base_entitlement=Decimal("15000"),
        amendment_entitlement=Decimal("3000"),
        expected_entitlement=Decimal("18000"),
        captured_amount=Decimal("15000"),
        currency=Currency.USD,
    )
    result = reconcile(model, evidence, has_contract=True, has_invoice=True, has_amendment=True)
    assert result.status == ReconciliationStatus.CHANGE_VALUE_NOT_CAPTURED
    assert result.expected == Decimal("18000")
    assert result.actual == Decimal("15000")
    assert result.difference == Decimal("3000")


def test_missing_evidence_never_becomes_finding():
    model = EconomicModel(
        expected_entitlement=Decimal("18000"),
        captured_amount=Decimal("15000"),
        amendment_entitlement=Decimal("3000"),
        currency=Currency.USD,
    )
    result = reconcile(model, [], has_contract=True, has_invoice=True, has_amendment=True)
    assert result.status == ReconciliationStatus.INSUFFICIENT_EVIDENCE
    assert result.evidence_sufficient is False


def test_no_finding_when_captured_meets_entitlement():
    model = EconomicModel(expected_entitlement=Decimal("15000"), captured_amount=Decimal("15000"))
    source = SourceLocation(document_id=uuid4(), page=1, text="invoice")
    evidence = [EvidenceLink(finding_id=uuid4(), source=source)]
    result = reconcile(model, evidence, has_contract=True, has_invoice=True)
    assert result.status == ReconciliationStatus.NO_FINDING
    assert result.difference == Decimal("0")


def test_evidence_deduplicates_source_locations():
    doc = uuid4()
    facts = [_fact(doc, 1, "100 hours", "1"), _fact(doc, 1, "100 hours", "1")]
    evidence = collect_evidence(facts)
    assert len(evidence) == 1
