from uuid import uuid4
from decimal import Decimal

from app.domain.enums import Currency, ReconciliationStatus, Unit, FindingStatus
from app.domain.schemas import EconomicFact, EconomicModel, SourceLocation
from app.evidence.engine import collect_evidence, collect_evidence_links, required_document_evidence, verify_source_locations
from app.reporting.finding import build_finding


def fact(doc, text="$150 per hour", page=1, confidence="0.99"):
    return EconomicFact(
        document_id=doc,
        field_name="rate",
        rate=Decimal("150"),
        currency=Currency.USD,
        unit=Unit.HOUR,
        source=SourceLocation(document_id=doc, page=page, text=text),
        extraction_confidence=Decimal(confidence),
    )


def test_duplicate_evidence_is_collapsed():
    doc = uuid4()
    a = fact(doc)
    b = a.model_copy(update={"id": uuid4()})
    assert len(collect_evidence([a, b])) == 1
    assert len(collect_evidence_links([a, b], finding_id=uuid4())) == 2


def test_parsed_page_text_must_match_source():
    doc = uuid4()
    f = fact(doc, text="$150 per hour")
    ok = verify_source_locations([f], {doc: {1: "Rate is $150 per hour."}})
    bad = verify_source_locations([f], {doc: {1: "Rate is $175 per hour."}})
    assert ok.complete
    assert not bad.complete


def test_required_documents_are_enforced():
    c = fact(uuid4(), text="100 hours at $150/hour")
    i = fact(uuid4(), text="100 hours at $125/hour")
    complete = required_document_evidence(contract_facts=[c], amendment_facts=[], invoice_facts=[i], delivery_facts=[])
    incomplete = required_document_evidence(contract_facts=[c], amendment_facts=[], invoice_facts=[], delivery_facts=[])
    assert complete.complete
    assert not incomplete.complete


def test_finding_is_verified_only_for_evidence_supported_rule():
    result = __import__('app.domain.schemas', fromlist=['ReconciliationResult']).ReconciliationResult(
        status=ReconciliationStatus.RATE_MISMATCH,
        expected=Decimal("15000"),
        actual=Decimal("12500"),
        difference=Decimal("2500"),
        reason="Rate differs.",
        evidence_sufficient=True,
    )
    f = fact(uuid4())
    finding = build_finding(result, [f.source], [f])
    assert finding is not None
    assert finding.status == FindingStatus.VERIFIED


def test_review_result_never_becomes_verified():
    result = __import__('app.domain.schemas', fromlist=['ReconciliationResult']).ReconciliationResult(
        status=ReconciliationStatus.REVIEW_REQUIRED,
        expected=Decimal("15000"),
        actual=Decimal("12500"),
        difference=Decimal("2500"),
        reason="Conflict.",
        evidence_sufficient=False,
    )
    f = fact(uuid4())
    finding = build_finding(result, [f.source], [f])
    assert finding is not None
    assert finding.status == FindingStatus.REVIEW_REQUIRED
