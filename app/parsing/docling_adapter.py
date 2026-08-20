from app.domain.schemas import DocumentRef, ParsedDocument


class DocumentParseError(RuntimeError):
    """Raised when a document cannot be converted into a trustworthy parse."""


class DoclingAdapter:
    """Docling-backed parser adapter.

    The core application only depends on ``DocumentParser`` and ``ParsedDocument``.
    This adapter is the only place that knows Docling's concrete API.
    """

    def parse(self, document: DocumentRef) -> ParsedDocument:
        try:
            from docling.document_converter import DocumentConverter
        except ImportError as exc:
            raise DocumentParseError(
                "Docling dependency is not installed; install the optional 'docling' extra."
            ) from exc

        try:
            result = DocumentConverter().convert(document.storage_path)
            doc = result.document
        except Exception as exc:  # parser boundary: convert vendor errors to domain error
            raise DocumentParseError(f"Docling conversion failed for {document.filename}") from exc

        pages = self._extract_pages(doc)
        if not pages:
            raise DocumentParseError(f"No textual content could be parsed from {document.filename}")

        return ParsedDocument(
            document_id=document.id,
            document_type=document.document_type,
            pages=pages,
        )

    @staticmethod
    def _extract_pages(doc) -> dict[int, str]:
        """Extract page-scoped text without inventing page numbers.

        Docling's ``export_to_text`` accepts ``page_no`` and its document model
        carries page provenance. We use the actual page numbers exposed by the
        parsed document instead of assuming a contiguous ``1..N`` sequence.
        """
        raw_pages = getattr(doc, "pages", None)
        page_numbers: list[int] = []

        if isinstance(raw_pages, dict):
            for key, page in raw_pages.items():
                page_no = getattr(page, "page_no", key)
                if isinstance(page_no, int) and page_no >= 1:
                    page_numbers.append(page_no)
        elif raw_pages is not None:
            try:
                for page in raw_pages:
                    page_no = getattr(page, "page_no", None)
                    if isinstance(page_no, int) and page_no >= 1:
                        page_numbers.append(page_no)
            except TypeError:
                pass

        page_numbers = sorted(set(page_numbers))
        pages: dict[int, str] = {}

        for page_no in page_numbers:
            text = doc.export_to_text(page_no=page_no, traverse_pictures=True)
            if isinstance(text, str) and text.strip():
                pages[page_no] = text.strip()

        # Some Docling backends may not expose page objects. A whole-document
        # export is allowed only as a deterministic fallback to page 1; callers
        # still know that the exact page provenance is unavailable.
        if not pages:
            text = doc.export_to_text(traverse_pictures=True)
            if isinstance(text, str) and text.strip():
                pages[1] = text.strip()

        return pages
