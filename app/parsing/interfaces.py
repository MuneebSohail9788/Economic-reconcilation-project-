from typing import Protocol

from app.domain.schemas import DocumentRef, ParsedDocument


class DocumentParser(Protocol):
    def parse(self, document: DocumentRef) -> ParsedDocument: ...
