from typing import Any

from app.domain.schemas import EconomicFact, ParsedDocument
from app.extraction.interfaces import StructuredAIProvider


class FactExtractionError(ValueError):
    """Raised when AI output cannot be safely admitted into the economic pipeline."""


class StructuredFactExtractor:
    """Provider-agnostic AI extraction adapter.

    The provider may propose facts, but this adapter is responsible for validating
    the schema and proving that every cited source belongs to the parsed document.
    """

    def __init__(self, provider: StructuredAIProvider):
        self.provider = provider

    def extract(self, document: ParsedDocument) -> list[EconomicFact]:
        proposals = self.provider.extract_economic_facts(document)
        if not isinstance(proposals, list):
            raise FactExtractionError("AI provider must return a list of fact objects")

        facts: list[EconomicFact] = []
        for index, proposal in enumerate(proposals):
            try:
                fact = EconomicFact.model_validate(proposal)
            except Exception as exc:
                raise FactExtractionError(f"Invalid economic fact at index {index}") from exc

            if fact.document_id != document.document_id:
                raise FactExtractionError(f"Fact {fact.id} cites a different document")

            source_text = document.pages.get(fact.source.page)
            if source_text is None:
                raise FactExtractionError(
                    f"Fact {fact.id} cites page {fact.source.page}, which is not in the parsed document"
                )

            if fact.source.text not in source_text:
                raise FactExtractionError(
                    f"Fact {fact.id} source text is not present on page {fact.source.page}"
                )

            facts.append(fact)

        return facts
