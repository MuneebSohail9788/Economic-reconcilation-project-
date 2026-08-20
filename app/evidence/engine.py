from dataclasses import dataclass
from uuid import UUID

from app.domain.enums import DocumentType
from app.domain.schemas import EconomicFact, EvidenceLink, SourceLocation


@dataclass(frozen=True)
class EvidenceCoverage:
    sources: list[SourceLocation]
    fact_ids: set[UUID]
    documents: set[UUID]
    complete: bool
    reason: str


def collect_evidence(facts: list[EconomicFact]) -> list[SourceLocation]:
    """Deduplicate evidence while preserving first-seen order."""
    seen: set[tuple] = set()
    result: list[SourceLocation] = []
    for fact in facts:
        source = fact.source
        key = (source.document_id, source.page, source.text, source.locator)
        if key not in seen:
            seen.add(key)
            result.append(source)
    return result


def collect_evidence_links(facts: list[EconomicFact], *, finding_id: UUID) -> list[EvidenceLink]:
    """Create traceable evidence links with the originating fact id."""
    links: list[EvidenceLink] = []
    seen: set[tuple] = set()
    for fact in facts:
        source = fact.source
        key = (fact.id, source.document_id, source.page, source.text, source.locator)
        if key in seen:
            continue
        seen.add(key)
        links.append(EvidenceLink(finding_id=finding_id, source=source, fact_id=fact.id))
    return links


def verify_source_locations(facts: list[EconomicFact], parsed_pages: dict[UUID, dict[int, str]] | None = None) -> EvidenceCoverage:
    """Verify that each cited location is internally valid and, when parsed pages exist, text is present on that page."""
    sources = collect_evidence(facts)
    if not sources:
        return EvidenceCoverage([], set(), set(), False, "No source evidence was supplied.")

    for source in sources:
        if source.page < 1 or not source.text.strip():
            return EvidenceCoverage(sources, {f.id for f in facts}, {s.document_id for s in sources}, False, "Evidence contains an invalid page or empty source text.")
        if parsed_pages is not None:
            pages = parsed_pages.get(source.document_id)
            if pages is None:
                return EvidenceCoverage(sources, {f.id for f in facts}, {s.document_id for s in sources}, False, "Evidence references a document that has not been parsed.")
            page_text = pages.get(source.page)
            if page_text is None or source.text not in page_text:
                return EvidenceCoverage(sources, {f.id for f in facts}, {s.document_id for s in sources}, False, "Evidence text does not match the referenced parsed page.")

    return EvidenceCoverage(sources, {f.id for f in facts}, {s.document_id for s in sources}, True, "All supplied evidence locations are valid.")


def required_document_evidence(
    *,
    contract_facts: list[EconomicFact],
    amendment_facts: list[EconomicFact],
    invoice_facts: list[EconomicFact],
    delivery_facts: list[EconomicFact],
    require_amendment: bool = False,
    require_delivery: bool = False,
) -> EvidenceCoverage:
    """Check the minimum source set needed to support a finding."""
    groups = [contract_facts, invoice_facts]
    labels = [(DocumentType.CONTRACT, contract_facts), (DocumentType.INVOICE, invoice_facts)]
    if require_amendment:
        groups.append(amendment_facts)
        labels.append((DocumentType.AMENDMENT, amendment_facts))
    if require_delivery:
        groups.append(delivery_facts)
        labels.append((DocumentType.DELIVERY_RECORD, delivery_facts))

    combined = [fact for group in groups for fact in group]
    coverage = verify_source_locations(combined)
    if not coverage.complete:
        return coverage

    missing = [name.value for name, facts in labels if not facts]
    if missing:
        return EvidenceCoverage(coverage.sources, coverage.fact_ids, coverage.documents, False, f"Required evidence missing: {', '.join(missing)}.")

    return coverage
