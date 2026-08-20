from decimal import Decimal
from uuid import UUID

from app.domain.schemas import EconomicFact, ParsedDocument, SourceLocation
from app.domain.enums import Unit, Currency


class DeterministicFixtureExtractor:
    """Test/fixture extractor. Production AI adapters implement the same boundary."""

    def __init__(self, fixtures: dict[UUID, list[EconomicFact]] | None = None):
        self.fixtures = fixtures or {}

    def extract(self, document: ParsedDocument) -> list[EconomicFact]:
        return self.fixtures.get(document.document_id, [])


def fact(document_id: UUID, page: int, text: str, **kwargs) -> EconomicFact:
    return EconomicFact(
        document_id=document_id,
        source=SourceLocation(document_id=document_id, page=page, text=text),
        **kwargs,
    )
