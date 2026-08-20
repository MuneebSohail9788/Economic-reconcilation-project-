from decimal import Decimal
from uuid import uuid4

from app.domain.enums import Currency, Unit
from app.domain.schemas import EconomicFact, SourceLocation
from app.pipeline import run_pipeline


def make_fact(doc_id, page, text, quantity=None, rate=None, amount=None):
    return EconomicFact(
        document_id=doc_id,
        field_name="economic_line",
        quantity=quantity,
        rate=rate,
        amount=amount,
        unit=Unit.HOUR,
        currency=Currency.USD,
        source=SourceLocation(document_id=doc_id, page=page, text=text),
        extraction_confidence=Decimal("0.99"),
    )


contract_id, amendment_id, invoice_id = uuid4(), uuid4(), uuid4()
result = run_pipeline(
    contract_facts=[make_fact(contract_id, 7, "100 hours at $150/hour", Decimal("100"), Decimal("150"))],
    amendment_facts=[make_fact(amendment_id, 2, "Approved additional 20 hours at $150/hour", Decimal("20"), Decimal("150"))],
    invoice_facts=[make_fact(invoice_id, 1, "Invoice: 100 hours at $150/hour", Decimal("100"), Decimal("150"))],
)

print("STATUS:", result.status)
print("RECONCILIATION:", result.reconciliation.model_dump(mode="json"))
print("FINDING:", result.finding.model_dump(mode="json") if result.finding else None)
