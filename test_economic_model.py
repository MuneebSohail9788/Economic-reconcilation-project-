from decimal import Decimal
from uuid import uuid4

from app.domain.enums import Currency, Unit
from app.domain.schemas import EconomicFact
from app.economic_model.builder import build_model


def fact(doc, amount=None, quantity=None, rate=None):
    return EconomicFact.model_validate({
        "document_id": doc,
        "field_name": "line",
        "amount": amount,
        "quantity": quantity,
        "rate": rate,
        "currency": Currency.USD,
        "unit": Unit.HOUR,
        "source": {"document_id": doc, "page": 1, "text": "source"},
    })


def test_model_builds_expected_entitlement():
    c, a, i = uuid4(), uuid4(), uuid4()
    model = build_model(
        contract_facts=[fact(c, quantity=Decimal("100"), rate=Decimal("150"))],
        amendment_facts=[fact(a, quantity=Decimal("20"), rate=Decimal("150"))],
        invoice_facts=[fact(i, quantity=Decimal("100"), rate=Decimal("150"))],
    )
    assert model.base_entitlement == Decimal("15000")
    assert model.amendment_entitlement == Decimal("3000")
    assert model.expected_entitlement == Decimal("18000")
    assert model.captured_amount == Decimal("15000")
