from app.domain.enums import AnalysisStatus

_ALLOWED = {
    AnalysisStatus.CREATED: {AnalysisStatus.INGESTED, AnalysisStatus.FAILED},
    AnalysisStatus.INGESTED: {AnalysisStatus.PARSED, AnalysisStatus.FAILED},
    AnalysisStatus.PARSED: {AnalysisStatus.EXTRACTED, AnalysisStatus.FAILED},
    AnalysisStatus.EXTRACTED: {AnalysisStatus.NORMALIZED, AnalysisStatus.FAILED},
    AnalysisStatus.NORMALIZED: {AnalysisStatus.MODELED, AnalysisStatus.FAILED},
    AnalysisStatus.MODELED: {AnalysisStatus.RECONCILED, AnalysisStatus.FAILED},
    AnalysisStatus.RECONCILED: {AnalysisStatus.FINDINGS_GENERATED, AnalysisStatus.FAILED},
    AnalysisStatus.FINDINGS_GENERATED: set(),
    AnalysisStatus.FAILED: {AnalysisStatus.RETRY, AnalysisStatus.DEAD},
    AnalysisStatus.RETRY: {AnalysisStatus.CREATED},
    AnalysisStatus.DEAD: set(),
}


def transition(current: AnalysisStatus, target: AnalysisStatus) -> AnalysisStatus:
    if target not in _ALLOWED[current]:
        raise ValueError(f"Invalid analysis transition: {current} -> {target}")
    return target
