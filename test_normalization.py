from decimal import Decimal
from uuid import uuid4
import pytest

from app.domain.enums import Currency, Unit
from app.domain.errors import DomainError
from app.domain.schemas import EconomicFact, SourceLocation
from app.normalization import NormalizationError, normalize_currency, normalize_fact, normalize_unit


def test_aliases_normalize():
    assert normalize_unit("hrs") == Unit.HOUR
    assert normalize_unit("units") == Unit.UNIT
    assert normalize_currency("USD") == Currency.USD
    assert normalize_currency("$") == Currency.USD


def test_money_stays_decimal():
    doc = uuid4()
    fact = EconomicFact(
        document_id=doc, field_name="rate", quantity=Decimal("100"),
        rate=Decimal("150.00"), currency=Currency.USD, unit=Unit.HOUR,
        source=SourceLocation(document_id=doc, page=1, text="$150/hour"),
    )
    normalized = normalize_fact(fact)
    assert isinstance(normalized.rate, Decimal)
    assert normalized.rate == Decimal("150.00")


def test_dict_provider_values_are_normalized():
    doc = uuid4()
    normalized = normalize_fact({
        "document_id": doc, "field_name": "rate", "quantity": "1,000",
        "rate": "150.00", "currency": "USD", "unit": "hours",
        "source": {"document_id": doc, "page": 1, "text": "$150/hour"},
    })
    assert normalized.quantity == Decimal("1000")
    assert normalized.unit == Unit.HOUR


def test_negative_financial_value_rejected():
    doc = uuid4()
    with pytest.raises(NormalizationError):
        normalize_fact({
            "document_id": doc, "field_name": "rate", "rate": "-10", "unit": "hour",
            "currency": "USD", "source": {"document_id": doc, "page": 1, "text": "-10/hour"},
        })


def test_rate_requires_unit():
    doc = uuid4()
    with pytest.raises(NormalizationError):
        normalize_fact({
            "document_id": doc, "field_name": "rate", "rate": "150", "currency": "USD",
            "source": {"document_id": doc, "page": 1, "text": "$150"},
        })
