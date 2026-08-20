from decimal import Decimal

from app.domain.errors import DomainError
from app.domain.schemas import EconomicModel, NormalizedFact


class EconomicModelError(DomainError):
    """Raised when facts cannot safely form one economic model."""


def _line_amount(f: NormalizedFact) -> Decimal:
    if f.amount is not None and f.quantity is not None and f.rate is not None:
        calculated = f.quantity * f.rate
        if calculated != f.amount:
            raise EconomicModelError(
                f"Fact {f.id} has conflicting amount and quantity×rate values"
            )
    if f.amount is not None:
        return f.amount
    if f.quantity is not None and f.rate is not None:
        return f.quantity * f.rate
    raise EconomicModelError(f"Fact {f.id} has insufficient monetary fields")


def _validate_group(facts: list[NormalizedFact], group_name: str) -> None:
    currencies = {f.currency for f in facts if f.currency is not None}
    if len(currencies) > 1:
        raise EconomicModelError(f"{group_name} contains multiple currencies")

    units = {f.unit for f in facts if f.quantity is not None and f.unit is not None}
    if len(units) > 1:
        raise EconomicModelError(f"{group_name} contains incompatible units")


def build_model(
    contract_facts: list[NormalizedFact],
    amendment_facts: list[NormalizedFact],
    invoice_facts: list[NormalizedFact],
    delivery_facts: list[NormalizedFact] | None = None,
) -> EconomicModel:
    delivery_facts = delivery_facts or []
    groups = (
        (contract_facts, "contract"),
        (amendment_facts, "amendment"),
        (invoice_facts, "invoice"),
        (delivery_facts, "delivery"),
    )
    for facts, name in groups:
        _validate_group(facts, name)

    all_facts = [f for facts, _ in groups for f in facts]
    currencies = {f.currency for f in all_facts if f.currency is not None}
    if len(currencies) > 1:
        raise EconomicModelError("Economic model contains conflicting currencies")

    base = sum((_line_amount(f) for f in contract_facts), Decimal("0"))
    amendment = sum((_line_amount(f) for f in amendment_facts), Decimal("0"))
    delivered = sum((_line_amount(f) for f in delivery_facts), Decimal("0"))
    captured = sum((_line_amount(f) for f in invoice_facts), Decimal("0"))

    # Delivery evidence may establish an entitlement only when it is greater than
    # the contractual/amendment entitlement. It never silently creates entitlement
    # without a monetary value on the delivery fact itself.
    expected = max(base + amendment, delivered)
    currency = next((f.currency for f in all_facts if f.currency is not None), None)

    return EconomicModel(
        base_entitlement=base,
        amendment_entitlement=amendment,
        delivered_entitlement=delivered,
        expected_entitlement=expected,
        captured_amount=captured,
        currency=currency,
    )
