from app.domain.enums import FindingStatus, ReconciliationStatus
from app.domain.schemas import EconomicFact, Finding, ReconciliationResult, SourceLocation


def _finding_status(result: ReconciliationResult) -> FindingStatus:
    if result.status in {
        ReconciliationStatus.REVIEW_REQUIRED,
        ReconciliationStatus.CURRENCY_CONFLICT,
        ReconciliationStatus.DUPLICATE,
    }:
        return FindingStatus.REVIEW_REQUIRED
    if result.status == ReconciliationStatus.INSUFFICIENT_EVIDENCE:
        return FindingStatus.REVIEW_REQUIRED
    if result.evidence_sufficient and result.status in {
        ReconciliationStatus.RATE_MISMATCH,
        ReconciliationStatus.QUANTITY_MISMATCH,
        ReconciliationStatus.CHANGE_VALUE_NOT_CAPTURED,
        ReconciliationStatus.DELIVERED_VALUE_NOT_CAPTURED,
    }:
        return FindingStatus.VERIFIED
    return FindingStatus.POTENTIAL


def build_finding(
    result: ReconciliationResult,
    evidence: list[SourceLocation],
    facts: list[EconomicFact],
) -> Finding | None:
    if result.status in {ReconciliationStatus.NO_FINDING, ReconciliationStatus.INSUFFICIENT_EVIDENCE}:
        return None
    confidence_values = [f.extraction_confidence for f in facts if f.extraction_confidence is not None]
    confidence = min(confidence_values) if confidence_values else None
    return Finding(
        status=_finding_status(result),
        rule_code=result.status,
        expected=result.expected,
        captured=result.actual,
        difference=result.difference,
        reason=result.reason,
        evidence=evidence,
        extraction_confidence=confidence,
    )
