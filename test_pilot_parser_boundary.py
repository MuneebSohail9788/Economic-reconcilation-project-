from pathlib import Path

import pytest

from app.domain.enums import DocumentType
from app.domain.schemas import DocumentRef
from app.parsing.docling_adapter import DocumentParseError, DoclingAdapter
from app.pilot.parser import PilotFileParser

FIXTURE_DIR = Path(__file__).parent / "pilot_fixtures"


def test_pilot_parser_preserves_page_provenance_for_pdf_and_docx(tmp_path):
    parser = PilotFileParser()
    for filename, doc_type in (("pilot_contract.pdf", DocumentType.CONTRACT), ("pilot_invoice.docx", DocumentType.INVOICE)):
        source = FIXTURE_DIR / filename
        target = tmp_path / filename
        target.write_bytes(source.read_bytes())
        ref = DocumentRef(filename=filename, sha256="0" * 64, document_type=doc_type, storage_path=str(target))
        parsed = parser.parse(ref)
        assert parsed.document_id == ref.id
        assert parsed.pages
        assert all(page > 0 and text.strip() for page, text in parsed.pages.items())


def test_docling_missing_dependency_fails_safe_when_unavailable():
    parser = DoclingAdapter()
    ref = DocumentRef(
        filename="pilot_contract.pdf",
        sha256="0" * 64,
        document_type=DocumentType.CONTRACT,
        storage_path=str(FIXTURE_DIR / "pilot_contract.pdf"),
    )
    try:
        import docling  # type: ignore
    except ImportError:
        with pytest.raises(DocumentParseError, match="Docling dependency is not installed"):
            parser.parse(ref)
