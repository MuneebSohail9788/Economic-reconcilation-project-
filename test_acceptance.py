from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from app.domain.enums import Currency, DocumentType, ReconciliationStatus, Unit
from app.domain.schemas import EconomicFact, ParsedDocument, SourceLocation
from app.economic_model.rules import check_quantity_mismatch
from app.extraction.ai import FactExtractionError, StructuredFactExtractor
from app.pipeline import run_pipeline
from app.reconciliation.engine import reconcile
from app.domain.schemas import EconomicModel, EvidenceLink


def make_fact(doc, *, amount=None, quantity=None, rate=None, text="source", currency=Currency.USD, **kwargs):
    return EconomicFact(
        document_id=doc,
        field_name="line",
        amount=Decimal(str(amount)) if amount is not None else None,
        quantity=Decimal(str(quantity)) if quantity is not None else None,
        rate=Decimal(str(rate)) if rate is not None else None,
        currency=currency,
        unit=Unit.HOUR if quantity is not None else None,
        source=SourceLocation(document_id=doc, page=1, text=text),
        **kwargs,
    )


def facts_for_category(category: str):
    c, a, i = uuid4(), uuid4(), uuid4()
    contract = [make_fact(c, quantity=100, rate=150, text="100 hours at $150/hour", event_id=f"C-{c}")]
    amendment, invoice = [], [make_fact(i, quantity=100, rate=150, amount=15000, text="100 hours billed at $150/hour", invoice_number=f"I-{i}")]
    if category == "rate_mismatch":
        invoice = [make_fact(i, quantity=100, rate=125, amount=12500, text="100 hours billed at $125/hour", invoice_number=f"I-{i}")]
    elif category == "quantity_mismatch":
        invoice = [make_fact(i, quantity=80, rate=150, amount=12000, text="80 hours billed at $150/hour", invoice_number=f"I-{i}")]
    elif category == "change_value":
        amendment = [make_fact(a, quantity=20, rate=150, amount=3000, text="20 additional hours approved", approved=True, event_id=f"A-{a}")]
    elif category == "insufficient_evidence":
        invoice = []
    elif category == "currency_conflict":
        invoice = [make_fact(i, quantity=100, rate=150, amount=15000, text="100 hours billed", currency=Currency.EUR, invoice_number=f"I-{i}")]
    elif category == "clean":
        pass
    return contract, amendment, invoice


def test_all_60_golden_cases_execute():
    dataset = json.loads(Path("tests/fixtures/golden_dataset.json").read_text())
    assert len(dataset["cases"]) == 60
    for case in dataset["cases"]:
        c, a, i = facts_for_category(case["category"])
        result = run_pipeline(contract_facts=c, amendment_facts=a, invoice_facts=i)
        assert result.reconciliation.status.value == case["expected_status"], case["id"]


def test_adv_001_duplicate_invoice():
    i = make_fact(uuid4(), amount=15000, event_id="INV-001")
    evidence = [EvidenceLink(finding_id=uuid4(), source=i.source, fact_id=i.id)]
    result = reconcile(EconomicModel(expected_entitlement=Decimal("15000"), captured_amount=Decimal("30000")), evidence, has_contract=True, has_invoice=True, invoice_facts=[i, i])
    assert result.status == ReconciliationStatus.DUPLICATE


def test_adv_002_conflicting_rates_review():
    c = make_fact(uuid4(), quantity=100, rate=150)
    i = make_fact(uuid4(), quantity=100, rate=125)
    evidence = [EvidenceLink(finding_id=uuid4(), source=c.source), EvidenceLink(finding_id=uuid4(), source=i.source)]
    result = reconcile(EconomicModel(expected_entitlement=Decimal("15000"), captured_amount=Decimal("12500")), evidence, has_contract=True, has_invoice=True, contract_facts=[c], invoice_facts=[i])
    assert result.status == ReconciliationStatus.REVIEW_REQUIRED


def test_adv_003_future_amendment():
    a = make_fact(uuid4(), amount=3000, approved=True, effective_date=date(2026, 9, 1))
    result = reconcile(EconomicModel(expected_entitlement=Decimal("18000"), captured_amount=Decimal("15000"), amendment_entitlement=Decimal("3000")), [EvidenceLink(finding_id=uuid4(), source=a.source)], has_contract=True, has_invoice=True, has_amendment=True, amendment_facts=[a], as_of=date(2026, 8, 20))
    assert result.status == ReconciliationStatus.REVIEW_REQUIRED


def test_adv_004_currency_conflict():
    c, a, i = facts_for_category("currency_conflict")
    result = run_pipeline(contract_facts=c, amendment_facts=a, invoice_facts=i)
    assert result.reconciliation.status == ReconciliationStatus.CURRENCY_CONFLICT


def test_adv_005_hallucinated_fact_rejected():
    doc_id = uuid4()
    doc = ParsedDocument(document_id=doc_id, document_type=DocumentType.CONTRACT, pages={1: "Contract says $150/hour"})
    class Provider:
        def extract_economic_facts(self, document):
            return [{"document_id": str(doc_id), "field_name": "rate", "rate": "175", "currency": "USD", "source": {"document_id": str(doc_id), "page": 1, "text": "$175/hour"}}]
    with pytest.raises(FactExtractionError):
        StructuredFactExtractor(Provider()).extract(doc)


def test_adv_006_missing_source_is_insufficient():
    c = make_fact(uuid4(), quantity=100, rate=150)
    result = run_pipeline(contract_facts=c and [c], amendment_facts=[], invoice_facts=[])
    assert result.reconciliation.status == ReconciliationStatus.INSUFFICIENT_EVIDENCE


def test_adv_007_invoice_inconsistency_review():
    i = make_fact(uuid4(), quantity=100, rate=150, amount=14900)
    c = make_fact(uuid4(), quantity=100, rate=150)
    evidence = [EvidenceLink(finding_id=uuid4(), source=c.source), EvidenceLink(finding_id=uuid4(), source=i.source)]
    result = reconcile(EconomicModel(expected_entitlement=Decimal("15000"), captured_amount=Decimal("14900")), evidence, has_contract=True, has_invoice=True, contract_facts=[c], invoice_facts=[i])
    assert result.status == ReconciliationStatus.REVIEW_REQUIRED


def test_adv_008_canceled_amendment_review():
    c = make_fact(uuid4(), quantity=100, rate=150)
    a = make_fact(uuid4(), amount=3000, approved=True, canceled=True)
    result = reconcile(EconomicModel(expected_entitlement=Decimal("18000"), captured_amount=Decimal("15000"), amendment_entitlement=Decimal("3000")), [EvidenceLink(finding_id=uuid4(), source=a.source)], has_contract=True, has_invoice=True, has_amendment=True, contract_facts=[c], amendment_facts=[a])
    assert result.status == ReconciliationStatus.REVIEW_REQUIRED


def test_adv_009_ocr_corruption_rejected():
    doc_id = uuid4()
    doc = ParsedDocument(document_id=doc_id, document_type=DocumentType.INVOICE, pages={1: "100 hours billed at $125/hour"})
    class Provider:
        def extract_economic_facts(self, document):
            return [{"document_id": str(doc_id), "field_name": "rate", "rate": "125", "currency": "USD", "source": {"document_id": str(doc_id), "page": 1, "text": "100 hours billed at $175/hour"}}]
    with pytest.raises(FactExtractionError):
        StructuredFactExtractor(Provider()).extract(doc)


def test_adv_010_duplicate_economic_event():
    i = make_fact(uuid4(), amount=15000, external_reference="EVENT-1")
    evidence = [EvidenceLink(finding_id=uuid4(), source=i.source)]
    result = reconcile(EconomicModel(expected_entitlement=Decimal("15000"), captured_amount=Decimal("30000")), evidence, has_contract=True, has_invoice=True, invoice_facts=[i, i])
    assert result.status == ReconciliationStatus.DUPLICATE
