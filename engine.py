from collections.abc import Iterable
from datetime import date
from decimal import Decimal

from app.domain.enums import ReconciliationStatus
from app.domain.errors import DomainError
from app.domain.schemas import EconomicFact, EconomicModel, EvidenceLink, ReconciliationResult


class ReconciliationConflict(DomainError):
    """Raised when reconciliation cannot safely produce a deterministic financial result."""


def _empty_result(status: ReconciliationStatus, model: EconomicModel, reason: str) -> ReconciliationResult:
    return ReconciliationResult(
        status=status,
        expected=model.expected_entitlement,
        actual=model.captured_amount,
        difference=max(model.expected_entitlement - model.captured_amount, Decimal("0")),
        reason=reason,
        evidence_sufficient=False,
    )


def find_duplicate_economic_events(*groups: list[EconomicFact]) -> bool:
    """Detect duplicate events *within the same source role*, not across contract/invoice roles."""
    for group in groups:
        seen: set[tuple] = set()
        for f in group:
            identity = f.event_id or f.invoice_number or f.external_reference
            if identity:
                key = (f.field_name, identity)
            else:
                key = (
                    f.field_name, f.quantity, f.unit, f.rate, f.amount,
                    f.currency, f.effective_date, f.canceled, f.source.document_id,
                )
            if key in seen:
                return True
            seen.add(key)
    return False


def has_conflicting_rates(contract: list[EconomicFact], amendment: list[EconomicFact], invoice: list[EconomicFact]) -> bool:
    """Detect ambiguity inside a single source role; cross-document rate differences are valid evidence for RATE_MISMATCH."""
    for group in (contract, amendment, invoice):
        rates = {f.rate for f in group if f.rate is not None}
        if len(rates) > 1:
            return True
    return False

def has_inconsistent_invoice(invoice: list[EconomicFact]) -> bool:
    for f in invoice:
        if f.amount is not None and f.quantity is not None and f.rate is not None:
            if f.quantity * f.rate != f.amount:
                return True
    return False


def has_future_or_unapproved_amendment(amendment: list[EconomicFact], *, as_of: date | None = None) -> bool:
    today = as_of or date.today()
    for f in amendment:
        if f.canceled:
            continue
        if f.approved is False:
            return True
        if f.effective_date is not None and f.effective_date > today:
            return True
    return False


def has_canceled_amendment(amendment: list[EconomicFact]) -> bool:
    return bool(amendment) and all(f.canceled for f in amendment)


def reconcile(
    model: EconomicModel,
    evidence: list[EvidenceLink],
    *,
    has_contract: bool,
    has_invoice: bool,
    has_amendment: bool = False,
    contract_facts: list[EconomicFact] | None = None,
    amendment_facts: list[EconomicFact] | None = None,
    invoice_facts: list[EconomicFact] | None = None,
    delivery_facts: list[EconomicFact] | None = None,
    as_of: date | None = None,
    allow_document_role_rate_mismatch: bool = False,
) -> ReconciliationResult:
    contract_facts = contract_facts or []
    amendment_facts = amendment_facts or []
    invoice_facts = invoice_facts or []
    delivery_facts = delivery_facts or []

    if has_canceled_amendment(amendment_facts):
        return _empty_result(
            ReconciliationStatus.REVIEW_REQUIRED,
            model,
            "All supplied amendment evidence is marked canceled; entitlement cannot be increased from it.",
        )

    if has_future_or_unapproved_amendment(amendment_facts, as_of=as_of):
        return _empty_result(
            ReconciliationStatus.REVIEW_REQUIRED,
            model,
            "Amendment is future-dated or not approved; it cannot be treated as current entitlement.",
        )

    if find_duplicate_economic_events(contract_facts, amendment_facts, invoice_facts, delivery_facts):
        return _empty_result(
            ReconciliationStatus.DUPLICATE,
            model,
            "The same economic event appears more than once in the reconciliation inputs.",
        )

    if has_conflicting_rates(contract_facts, amendment_facts, invoice_facts):
        return _empty_result(
            ReconciliationStatus.REVIEW_REQUIRED,
            model,
            "Multiple rates are present within a single source role; the engine will not choose one implicitly.",
        )

    if not allow_document_role_rate_mismatch:
        rates = {f.rate for g in (contract_facts, amendment_facts, invoice_facts) for f in g if f.rate is not None}
        if len(rates) > 1:
            return _empty_result(
                ReconciliationStatus.REVIEW_REQUIRED,
                model,
                "Rates differ across source roles; use the explicit RATE_MISMATCH rule with its source evidence.",
            )

    if has_inconsistent_invoice(invoice_facts):
        return _empty_result(
            ReconciliationStatus.REVIEW_REQUIRED,
            model,
            "Invoice amount is inconsistent with quantity multiplied by rate.",
        )

    expected = model.expected_entitlement
    actual = model.captured_amount
    difference = expected - actual

    required = has_contract and has_invoice and (not model.amendment_entitlement or has_amendment)
    evidence_sufficient = required and bool(evidence)

    if not evidence_sufficient:
        return ReconciliationResult(
            status=ReconciliationStatus.INSUFFICIENT_EVIDENCE,
            expected=expected,
            actual=actual,
            difference=max(difference, Decimal("0")),
            reason="Required source/evidence is missing; no financial finding is established.",
            evidence_sufficient=False,
        )

    if difference <= Decimal("0"):
        return ReconciliationResult(
            status=ReconciliationStatus.NO_FINDING,
            expected=expected,
            actual=actual,
            difference=Decimal("0"),
            reason="Captured amount meets or exceeds modeled entitlement.",
            evidence_sufficient=True,
        )

    status = (
        ReconciliationStatus.CHANGE_VALUE_NOT_CAPTURED
        if model.amendment_entitlement > 0 and actual < expected
        else ReconciliationStatus.POTENTIAL_BREAK
    )
    if model.delivered_entitlement > actual and model.delivered_entitlement >= expected:
        status = ReconciliationStatus.DELIVERED_VALUE_NOT_CAPTURED

    return ReconciliationResult(
        status=status,
        expected=expected,
        actual=actual,
        difference=difference,
        reason="Modeled economic entitlement exceeds evidenced captured amount.",
        evidence_sufficient=True,
    )
