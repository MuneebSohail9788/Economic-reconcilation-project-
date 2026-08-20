import json
from uuid import uuid4

import pytest

from app.domain.enums import DocumentType
from app.domain.schemas import ParsedDocument
from app.extraction.ai import FactExtractionError
from app.extraction.http_provider import HTTPStructuredAIProvider


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps({"facts": [{"field_name": "rate"}]}).encode()


def test_http_provider_sends_structured_payload(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode())
        captured["auth"] = req.headers.get("Authorization")
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("app.extraction.http_provider.request.urlopen", fake_urlopen)
    doc = ParsedDocument(document_id=uuid4(), document_type=DocumentType.CONTRACT, pages={1: "100 hours at $150/hour"})
    provider = HTTPStructuredAIProvider("https://example.test/extract", "secret", "test-model", 12)
    result = provider.extract_economic_facts(doc)
    assert result == [{"field_name": "rate"}]
    assert captured["url"] == "https://example.test/extract"
    assert captured["auth"] == "Bearer secret"
    assert captured["timeout"] == 12
    assert captured["body"]["model"] == "test-model"
    assert captured["body"]["document"]["pages"]["1"] == "100 hours at $150/hour"


def test_http_provider_rejects_invalid_response(monkeypatch):
    class BadResponse(FakeResponse):
        def read(self):
            return b'{"oops": []}'

    monkeypatch.setattr("app.extraction.http_provider.request.urlopen", lambda req, timeout: BadResponse())
    doc = ParsedDocument(document_id=uuid4(), document_type=DocumentType.CONTRACT, pages={1: "text"})
    with pytest.raises(FactExtractionError):
        HTTPStructuredAIProvider("https://example.test/extract").extract_economic_facts(doc)
