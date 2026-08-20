from decimal import Decimal
from uuid import uuid4

from app.domain.enums import Currency, ReconciliationStatus, Unit
from app.domain.schemas import EconomicFact, SourceLocation
from app.economic_model.rules import check_quantity_mismatch, check_rate_mismatch, validate_currency_consistency


def f(doc, *, quantity, rate, currency=Currency.USD):
    return EconomicFact(
        document_id=doc, field_name="line", quantity=quantity, rate=rate,
        currency=currency, unit=Unit.HOUR,
        source=SourceLocation(document_id=doc, page=1, text="source"),
    )


def test_rate_mismatch():
    c, i = uuid4(), uuid4()
    r = check_rate_mismatch([f(c, quantity=Decimal("100"), rate=Decimal("150"))], [f(i, quantity=Decimal("100"), rate=Decimal("125"))])
    assert r and r.status == ReconciliationStatus.RATE_MISMATCH
    assert r.difference == Decimal("2500")


def test_quantity_mismatch_is_not_silently_zero():
    c, i = uuid4(), uuid4()
    r = check_quantity_mismatch([f(c, quantity=Decimal("100"), rate=Decimal("150"))], [f(i, quantity=Decimal("80"), rate=Decimal("150"))])
    assert r and r.status == ReconciliationStatus.QUANTITY_MISMATCH
    assert r.difference == Decimal("3000")


def test_currency_conflict():
    c, i = uuid4(), uuid4()
    assert validate_currency_consistency(
        [f(c, quantity=Decimal("1"), rate=Decimal("1"), currency=Currency.USD)],
        [f(i, quantity=Decimal("1"), rate=Decimal("1"), currency=Currency.EUR)],
    ) is False
