from decimal import Decimal
from collections.abc import Iterable

from app.domain.enums import Currency, ReconciliationStatus
from app.domain.schemas import EconomicModel, NormalizedFact, ReconciliationResult


def _currency_set(facts: Iterable[NormalizedFact]) -> set[Currency]:
    return {f.currency for f in facts if f.currency is not None}


def validate_currency_consistency(*fact_groups: list[NormalizedFact]) -> bool:
    currencies = set()
    for group in fact_groups:
        currencies |= _currency_set(group)
    return len(currencies) <= 1


def check_rate_mismatch(contract: list[NormalizedFact], invoice: list[NormalizedFact]) -> ReconciliationResult | None:
    rates_contract = [f.rate for f in contract if f.rate is not None]
    rates_invoice = [f.rate for f in invoice if f.rate is not None]
    if not rates_contract or not rates_invoice:
        return None
    expected_rate = rates_contract[0]
    actual_rate = rates_invoice[0]
    quantity = next((f.quantity for f in invoice if f.quantity is not None), Decimal("0"))
    if expected_rate == actual_rate:
        return None
    difference = (expected_rate - actual_rate) * quantity
    return ReconciliationResult(
        status=ReconciliationStatus.RATE_MISMATCH,
        expected=expected_rate * quantity,
        actual=actual_rate * quantity,
        difference=difference,
        reason="Invoice rate differs from contract rate for the evidenced quantity.",
        evidence_sufficient=True,
    )


def check_quantity_mismatch(contract: list[NormalizedFact], invoice: list[NormalizedFact]) -> ReconciliationResult | None:
    expected_qty = next((f.quantity for f in contract if f.quantity is not None), None)
    actual_qty = next((f.quantity for f in invoice if f.quantity is not None), None)
    rate = next((f.rate for f in contract if f.rate is not None), None)
    if expected_qty is None or actual_qty is None or rate is None or expected_qty <= actual_qty:
        return None
    difference = (expected_qty - actual_qty) * rate
    return ReconciliationResult(
        status=ReconciliationStatus.QUANTITY_MISMATCH,
        expected=expected_qty * rate,
        actual=actual_qty * rate,
        difference=difference,
        reason="Invoice quantity is lower than contract quantity; entitlement still requires evidence review.",
        evidence_sufficient=True,
    )
