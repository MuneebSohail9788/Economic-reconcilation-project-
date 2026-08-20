from decimal import Decimal
from uuid import uuid4
import pytest

from app.domain.enums import Currency, Unit
from app.domain.schemas import NormalizedFact
from app.economic_model.builder import EconomicModelError, build_model


def f(doc, *, amount=None, quantity=None, rate=None, unit=Unit.HOUR, currency=Currency.USD):
    return NormalizedFact.model_validate({
        "document_id": doc, "field_name": "line", "amount": amount,
        "quantity": quantity, "rate": rate, "currency": currency, "unit": unit,
        "source": {"document_id": doc, "page": 1, "text": "source"},
    })


def test_conflicting_amount_and_rate_is_rejected():
    d = uuid4()
    with pytest.raises(EconomicModelError):
        build_model([f(d, quantity=Decimal("10"), rate=Decimal("10"), amount=Decimal("90"))], [], [])


def test_mixed_currency_is_rejected():
    c, i = uuid4(), uuid4()
    with pytest.raises(EconomicModelError):
        build_model([f(c, quantity=Decimal("1"), rate=Decimal("10"))],
                    [], [f(i, quantity=Decimal("1"), rate=Decimal("10"), currency=Currency.EUR)])


def test_mixed_units_in_group_are_rejected():
    c1, c2 = uuid4(), uuid4()
    with pytest.raises(EconomicModelError):
        build_model([
            f(c1, quantity=Decimal("1"), rate=Decimal("10"), unit=Unit.HOUR),
            f(c2, quantity=Decimal("1"), rate=Decimal("10"), unit=Unit.DAY),
        ], [], [])
