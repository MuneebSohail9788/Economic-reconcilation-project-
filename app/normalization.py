from decimal import Decimal, InvalidOperation
import re

from app.domain.enums import Currency, Unit
from app.domain.errors import DomainError
from app.domain.schemas import EconomicFact, NormalizedFact


class NormalizationError(DomainError):
    """Raised when an extracted fact cannot be normalized safely."""


_UNIT_ALIASES = {
    "hour": Unit.HOUR, "hours": Unit.HOUR, "hr": Unit.HOUR, "hrs": Unit.HOUR,
    "h": Unit.HOUR,
    "unit": Unit.UNIT, "units": Unit.UNIT, "each": Unit.UNIT, "ea": Unit.UNIT,
    "day": Unit.DAY, "days": Unit.DAY, "day(s)": Unit.DAY,
    "fixed": Unit.FIXED, "fixed fee": Unit.FIXED, "lump sum": Unit.FIXED,
}
_CURRENCY_ALIASES = {
    "usd": Currency.USD, "us dollar": Currency.USD, "us dollars": Currency.USD,
    "$": Currency.USD,
    "eur": Currency.EUR, "euro": Currency.EUR, "euros": Currency.EUR, "€": Currency.EUR,
    "gbp": Currency.GBP, "pound": Currency.GBP, "pounds": Currency.GBP, "£": Currency.GBP,
    "pkr": Currency.PKR, "rupee": Currency.PKR, "rupees": Currency.PKR, "₨": Currency.PKR,
}


def _decimal(value: object, field: str) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        # Remove presentation commas but never coerce through float.
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError) as exc:
        raise NormalizationError(f"Invalid decimal for {field}: {value!r}") from exc


def normalize_unit(value: object) -> Unit | None:
    if value is None or value == "":
        return None
    if isinstance(value, Unit):
        return value
    key = re.sub(r"\s+", " ", str(value).strip().lower())
    try:
        return _UNIT_ALIASES[key]
    except KeyError as exc:
        raise NormalizationError(f"Unsupported unit: {value!r}") from exc


def normalize_currency(value: object) -> Currency | None:
    if value is None or value == "":
        return None
    if isinstance(value, Currency):
        return value
    key = str(value).strip().lower()
    try:
        return _CURRENCY_ALIASES[key]
    except KeyError as exc:
        raise NormalizationError(f"Unsupported currency: {value!r}") from exc


def normalize_fact(fact: EconomicFact | dict) -> NormalizedFact:
    """Convert provider-shaped values into the canonical financial representation."""
    values = fact.model_dump() if isinstance(fact, EconomicFact) else dict(fact)
    values["quantity"] = _decimal(values.get("quantity"), "quantity")
    values["rate"] = _decimal(values.get("rate"), "rate")
    values["amount"] = _decimal(values.get("amount"), "amount")
    values["extraction_confidence"] = _decimal(values.get("extraction_confidence"), "extraction_confidence")
    values["unit"] = normalize_unit(values.get("unit"))
    values["currency"] = normalize_currency(values.get("currency"))

    # Negative quantity/rate/amount values are not silently accepted as ordinary facts.
    for field in ("quantity", "rate", "amount"):
        value = values[field]
        if value is not None and value < 0:
            raise NormalizationError(f"{field} cannot be negative in a normalized economic fact")

    # A rate-based line must have a unit; fixed amounts may omit quantity/rate.
    if values["rate"] is not None and values["unit"] is None:
        raise NormalizationError("A rate-based fact requires a normalized unit")

    return NormalizedFact.model_validate(values)
