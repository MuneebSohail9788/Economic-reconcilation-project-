from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.schemas import CreateAnalysisRequest, CreateAnalysisResponse, DocumentResponse, FindingResponse, RunHistoryItem, RunResponse
from app.application.service import AnalysisService
from app.core.config import settings
from app.core.security import require_api_key
from app.database.models import FindingDB
from app.database.repository import AnalysisRepository, DocumentRepository, RunRepository, get_finding
from app.database.session import get_db
from app.domain.enums import DocumentType
from app.extraction.runtime import build_extractor
from app.parsing.docling_adapter import DoclingAdapter

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> AnalysisService:
    return AnalysisService(db, DoclingAdapter(), build_extractor())


@router.post("/analyses", response_model=CreateAnalysisResponse, dependencies=[Depends(require_api_key)])
def create_analysis(request: CreateAnalysisRequest, db: Session = Depends(get_db)):
    return AnalysisRepository(db).create(request.name)


@router.post("/documents", response_model=DocumentResponse, dependencies=[Depends(require_api_key)])
async def upload_document(
    file: UploadFile = File(...),
    analysis_id: UUID = Query(...),
    document_type: DocumentType = DocumentType.OTHER,
    service: AnalysisService = Depends(get_service),
):
    content = await file.read()
    try:
        return service.upload_document(analysis_id, file.filename or "uploaded-file", content, document_type)
    except ValueError as exc:
        message = str(exc)
        status = 409 if "Duplicate" in message else 404 if "not found" in message.lower() else 400
        raise HTTPException(status, message) from exc


@router.get("/analyses/{analysis_id}", response_model=CreateAnalysisResponse)
def get_analysis(analysis_id: UUID, db: Session = Depends(get_db)):
    record = AnalysisRepository(db).get(analysis_id)
    if record is None:
        raise HTTPException(404, "Analysis not found")
    return record


@router.get("/analyses/{analysis_id}/documents", response_model=list[DocumentResponse])
def list_documents(analysis_id: UUID, db: Session = Depends(get_db)):
    if AnalysisRepository(db).get(analysis_id) is None:
        raise HTTPException(404, "Analysis not found")
    return [DocumentRepository.to_ref(x) for x in DocumentRepository(db).list_for_analysis(analysis_id)]


@router.post("/analyses/{analysis_id}/run", response_model=RunResponse, dependencies=[Depends(require_api_key)])
def run_analysis(analysis_id: UUID, service: AnalysisService = Depends(get_service)):
    try:
        execution = service.run(analysis_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        # Do not leak provider/parser internals in production responses.
        if settings.app_env == "development":
            raise HTTPException(500, str(exc)) from exc
        raise HTTPException(500, "Analysis run failed; inspect run history for details.") from exc

    finding_id = execution.pipeline.finding.id if execution.pipeline.finding else None
    message = execution.pipeline.reconciliation.reason
    return RunResponse(
        run_id=execution.run_id,
        analysis_id=analysis_id,
        attempt=execution.attempt,
        analysis_status=execution.pipeline.status.value,
        reconciliation_status=execution.pipeline.reconciliation.status,
        finding_id=finding_id,
        message=message,
    )


@router.post("/analyses/{analysis_id}/retry", response_model=CreateAnalysisResponse, dependencies=[Depends(require_api_key)])
def retry_analysis(analysis_id: UUID, service: AnalysisService = Depends(get_service)):
    try:
        return service.retry(analysis_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc




@router.get("/analyses/{analysis_id}/runs", response_model=list[RunHistoryItem])
def list_runs(analysis_id: UUID, db: Session = Depends(get_db)):
    if AnalysisRepository(db).get(analysis_id) is None:
        raise HTTPException(404, "Analysis not found")
    return [
        RunHistoryItem(
            id=row.id, attempt=row.attempt, status=row.status,
            error_code=row.error_code, error_message=row.error_message,
        )
        for row in RunRepository(db).list_for_analysis(analysis_id)
    ]

@router.get("/findings/{finding_id}", response_model=FindingResponse)
def get_finding_route(finding_id: UUID, db: Session = Depends(get_db)):
    finding = get_finding(db, finding_id)
    if finding is None:
        raise HTTPException(404, "Finding not found")
    return FindingResponse(
        id=finding.id,
        status=finding.status.value,
        rule_code=finding.rule_code,
        expected=finding.expected,
        captured=finding.captured,
        difference=finding.difference,
        reason=finding.reason,
        evidence_count=len(finding.evidence),
        currency=finding.currency,
    )


@router.get("/findings/{finding_id}/evidence", dependencies=[Depends(require_api_key)])
def get_finding_evidence(finding_id: UUID, db: Session = Depends(get_db)):
    finding = get_finding(db, finding_id)
    if finding is None:
        raise HTTPException(404, "Finding not found")
    return [
        {
            "document_id": str(link.document_id),
            "page": link.page,
            "text": link.source_text,
            "locator": link.locator,
            "fact_id": str(link.fact_id) if link.fact_id else None,
        }
        for link in finding.evidence
    ]


@router.get("/analyses/{analysis_id}/report", dependencies=[Depends(require_api_key)])
def get_analysis_report(analysis_id: UUID, db: Session = Depends(get_db)):
    analysis = AnalysisRepository(db).get(analysis_id)
    if analysis is None:
        raise HTTPException(404, "Analysis not found")
    findings = db.query(FindingDB).filter_by(analysis_id=analysis_id).all()
    return {
        "analysis": {"id": str(analysis.id), "name": analysis.name, "status": analysis.status, "retry_count": analysis.retry_count},
        "findings": [
            {"id": str(f.id), "status": f.status, "rule_code": f.rule_code, "expected": str(f.expected), "captured": str(f.captured), "difference": str(f.difference), "reason": f.reason, "currency": f.currency}
            for f in findings
        ],
    }
