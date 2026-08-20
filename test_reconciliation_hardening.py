from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.domain.enums import Currency, ReconciliationStatus, Unit
from app.domain.schemas import EconomicFact, EconomicModel, EvidenceLink, SourceLocation
from app.reconciliation.engine import (
    has_canceled_amendment,
    has_future_or_unapproved_amendment,
    reconcile,
)


def f(doc, *, amount=None, quantity=None, rate=None, approved=None, effective_date=None, canceled=False, event_id=None, invoice_number=None):
    return EconomicFact(
        document_id=doc,
        field_name="line",
        amount=Decimal(amount) if amount is not None else None,
        quantity=Decimal(quantity) if quantity is not None else None,
        rate=Decimal(rate) if rate is not None else None,
        currency=Currency.USD,
        unit=Unit.HOUR if quantity is not None else None,
        approved=approved,
        effective_date=effective_date,
        canceled=canceled,
        event_id=event_id,
        invoice_number=invoice_number,
        source=SourceLocation(document_id=doc, page=1, text="source"),
    )


def evidence(facts):
    return [EvidenceLink(finding_id=uuid4(), source=x.source, fact_id=x.id) for x in facts]


def model(expected, captured, amendment=0, delivered=0):
    return EconomicModel(
        expected_entitlement=Decimal(expected),
        captured_amount=Decimal(captured),
        amendment_entitlement=Decimal(amendment),
        delivered_entitlement=Decimal(delivered),
        currency=Currency.USD,
    )


def test_duplicate_invoice_is_hard_stop():
    i = f(uuid4(), amount="15000", event_id="INV-001")
    result = reconcile(model("15000", "30000"), evidence([i]), has_contract=True, has_invoice=True, invoice_facts=[i, i])
    assert result.status == ReconciliationStatus.DUPLICATE
    assert not result.evidence_sufficient


def test_conflicting_rates_require_review():
    c = f(uuid4(), quantity="100", rate="150")
    i = f(uuid4(), quantity="100", rate="125")
    result = reconcile(model("15000", "12500"), evidence([c, i]), has_contract=True, has_invoice=True, contract_facts=[c], invoice_facts=[i])
    assert result.status == ReconciliationStatus.REVIEW_REQUIRED


def test_future_amendment_requires_review():
    a = f(uuid4(), amount="3000", approved=True, effective_date=date(2026, 9, 1))
    result = reconcile(model("18000", "15000", amendment=3000), evidence([a]), has_contract=True, has_invoice=True, has_amendment=True, amendment_facts=[a], as_of=date(2026, 8, 20))
    assert result.status == ReconciliationStatus.REVIEW_REQUIRED


def test_unapproved_amendment_requires_review():
    a = f(uuid4(), amount="3000", approved=False)
    result = reconcile(model("18000", "15000", amendment=3000), evidence([a]), has_contract=True, has_invoice=True, has_amendment=True, amendment_facts=[a])
    assert result.status == ReconciliationStatus.REVIEW_REQUIRED


def test_canceled_amendment_requires_review():
    a = f(uuid4(), amount="3000", approved=True, canceled=True)
    assert has_canceled_amendment([a])
    result = reconcile(model("18000", "15000", amendment=3000), evidence([a]), has_contract=True, has_invoice=True, has_amendment=True, amendment_facts=[a])
    assert result.status == ReconciliationStatus.REVIEW_REQUIRED


def test_invoice_inconsistency_requires_review():
    i = f(uuid4(), amount="14900", quantity="100", rate="150")
    result = reconcile(model("15000", "14900"), evidence([i]), has_contract=True, has_invoice=True, invoice_facts=[i])
    assert result.status == ReconciliationStatus.REVIEW_REQUIRED


def test_delivery_rule_has_precedence_when_delivery_exceeds_contract_entitlement():
    d = f(uuid4(), quantity="150", rate="100", event_id="DEL-1")
    c = f(uuid4(), quantity="100", rate="100", event_id="CTR-1")
    i = f(uuid4(), quantity="100", rate="100", event_id="INV-1")
    result = reconcile(model("15000", "10000", delivered=15000), evidence([c, i, d]), has_contract=True, has_invoice=True, contract_facts=[c], invoice_facts=[i], delivery_facts=[d])
    assert result.status == ReconciliationStatus.DELIVERED_VALUE_NOT_CAPTURED
    assert result.difference == Decimal("5000")
