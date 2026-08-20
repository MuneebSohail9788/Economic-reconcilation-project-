from pathlib import Path

from app.core.config import settings
from app.extraction.ai import FactExtractionError, StructuredFactExtractor
from app.extraction.http_provider import HTTPStructuredAIProvider
from app.extraction.interfaces import FactExtractor


class UnconfiguredProvider:
    def extract_economic_facts(self, document):
        raise FactExtractionError(
            "No AI provider is configured. Configure AI_PROVIDER_URL before running production extraction."
        )


class FixtureProvider:
    """Development-only deterministic provider loaded from fixture JSON."""

    def __init__(self, payload_by_document):
        self.payload_by_document = payload_by_document

    def extract_economic_facts(self, document):
        return self.payload_by_document.get(str(document.document_id), [])


def build_extractor() -> FactExtractor:
    mode = settings.extraction_mode.lower()
    if mode == "fixture":
        import json
        fixture_path = Path(settings.fixture_path)
        if not fixture_path.exists():
            raise RuntimeError(f"Fixture extraction file not found: {fixture_path}")
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        return StructuredFactExtractor(FixtureProvider(payload))
    if mode == "ai":
        if not settings.ai_provider_url:
            return StructuredFactExtractor(UnconfiguredProvider())
        provider = HTTPStructuredAIProvider(
            endpoint=settings.ai_provider_url,
            api_key=settings.ai_api_key,
            model=settings.ai_model,
            timeout=settings.ai_timeout_seconds,
        )
        return StructuredFactExtractor(provider)
    raise RuntimeError(f"Unsupported EXTRACTION_MODE: {settings.extraction_mode}")
