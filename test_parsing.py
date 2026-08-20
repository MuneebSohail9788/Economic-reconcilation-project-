from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.enums import DocumentType
from app.domain.schemas import DocumentRef
from app.parsing.docling_adapter import DoclingAdapter, DocumentParseError


def _document(tmp_path):
    path = tmp_path / "contract.pdf"
    path.write_bytes(b"pdf")
    return DocumentRef(
        id=uuid4(),
        filename="contract.pdf",
        sha256="a" * 64,
        document_type=DocumentType.CONTRACT,
        storage_path=str(path),
    )


def test_docling_adapter_preserves_real_page_numbers(monkeypatch, tmp_path):
    class FakeConverter:
        def convert(self, path):
            assert path.endswith("contract.pdf")
            pages = {
                1: SimpleNamespace(page_no=1),
                3: SimpleNamespace(page_no=3),
            }
            doc = SimpleNamespace(pages=pages)
            doc.export_to_text = lambda page_no=None, traverse_pictures=False: {
                1: "contract rate $150/hour",
                3: "billing terms",
            }.get(page_no, "")
            return SimpleNamespace(document=doc)

    import sys
    fake_module = SimpleNamespace(DocumentConverter=FakeConverter)
    monkeypatch.setitem(sys.modules, "docling.document_converter", fake_module)
    monkeypatch.setitem(sys.modules, "docling", SimpleNamespace(document_converter=fake_module))

    parsed = DoclingAdapter().parse(_document(tmp_path))
    assert list(parsed.pages) == [1, 3]
    assert "$150/hour" in parsed.pages[1]


def test_docling_adapter_rejects_empty_parse(monkeypatch, tmp_path):
    class FakeConverter:
        def convert(self, path):
            doc = SimpleNamespace(pages={}, export_to_text=lambda **kwargs: "")
            return SimpleNamespace(document=doc)

    import sys
    fake_module = SimpleNamespace(DocumentConverter=FakeConverter)
    monkeypatch.setitem(sys.modules, "docling.document_converter", fake_module)
    monkeypatch.setitem(sys.modules, "docling", SimpleNamespace(document_converter=fake_module))

    with pytest.raises(DocumentParseError, match="No textual content"):
        DoclingAdapter().parse(_document(tmp_path))
