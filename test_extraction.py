from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.enums import Currency, DocumentType, Unit
from app.domain.schemas import ParsedDocument
from app.extraction.ai import FactExtractionError, StructuredFactExtractor


class Provider:
    def __init__(self, payload):
        self.payload = payload

    def extract_economic_facts(self, document):
        return self.payload


def document():
    doc_id = uuid4()
    return ParsedDocument(
        document_id=doc_id,
        document_type=DocumentType.CONTRACT,
        pages={1: "100 hours at $150 per hour"},
    )


def test_valid_ai_fact_requires_source_and_is_admitted():
    doc = document()
    payload = [{
        "document_id": str(doc.document_id),
        "field_name": "service_rate",
        "quantity": "100",
        "unit": "HOUR",
        "rate": "150",
        "currency": "USD",
        "source": {
            "document_id": str(doc.document_id),
            "page": 1,
            "text": "100 hours at $150 per hour",
        },
        "extraction_confidence": "0.97",
    }]

    facts = StructuredFactExtractor(Provider(payload)).extract(doc)
    assert facts[0].quantity == Decimal("100")
    assert facts[0].rate == Decimal("150")
    assert facts[0].currency == Currency.USD
    assert facts[0].unit == Unit.HOUR


def test_hallucinated_source_text_is_rejected():
    doc = document()
    payload = [{
        "document_id": str(doc.document_id),
        "field_name": "service_rate",
        "rate": "175",
        "currency": "USD",
        "source": {
            "document_id": str(doc.document_id),
            "page": 1,
            "text": "$175 per hour",
        },
    }]
    with pytest.raises(FactExtractionError, match="source text"):
        StructuredFactExtractor(Provider(payload)).extract(doc)


def test_missing_source_page_is_rejected():
    doc = document()
    payload = [{
        "document_id": str(doc.document_id),
        "field_name": "service_rate",
        "rate": "150",
        "currency": "USD",
        "source": {
            "document_id": str(doc.document_id),
            "page": 2,
            "text": "$150 per hour",
        },
    }]
    with pytest.raises(FactExtractionError, match="page 2"):
        StructuredFactExtractor(Provider(payload)).extract(doc)


def test_wrong_document_source_is_rejected():
    doc = document()
    other = uuid4()
    payload = [{
        "document_id": str(other),
        "field_name": "service_rate",
        "rate": "150",
        "currency": "USD",
        "source": {
            "document_id": str(other),
            "page": 1,
            "text": "$150 per hour",
        },
    }]
    with pytest.raises(FactExtractionError, match="different document"):
        StructuredFactExtractor(Provider(payload)).extract(doc)


def test_invalid_schema_is_rejected():
    doc = document()
    payload = [{
        "document_id": str(doc.document_id),
        "field_name": "service_rate",
        "rate": "not-a-number",
        "currency": "USD",
        "source": {
            "document_id": str(doc.document_id),
            "page": 1,
            "text": "$150 per hour",
        },
    }]
    with pytest.raises(FactExtractionError, match="Invalid economic fact"):
        StructuredFactExtractor(Provider(payload)).extract(doc)
