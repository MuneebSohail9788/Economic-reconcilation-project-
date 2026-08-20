from typing import Any, Protocol

from app.domain.schemas import EconomicFact, ParsedDocument


class FactExtractor(Protocol):
    def extract(self, document: ParsedDocument) -> list[EconomicFact]: ...


class StructuredAIProvider(Protocol):
    """Provider boundary: returns structured JSON-compatible extraction proposals."""

    def extract_economic_facts(self, document: ParsedDocument) -> list[dict[str, Any]]: ...
