import hashlib
from pathlib import Path
from uuid import UUID, uuid4

from app.core.config import settings
from app.domain.enums import DocumentType
from app.domain.schemas import DocumentRef

ALLOWED_SUFFIXES = {".pdf", ".docx", ".xlsx", ".csv"}


def ingest_file(
    filename: str,
    content: bytes,
    document_type: DocumentType,
    *,
    analysis_id: UUID | None = None,
) -> DocumentRef:
    filename = Path(filename).name
    if not filename or filename in {".", ".."}:
        raise ValueError("Invalid filename")
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError(f"Unsupported file type: {suffix}")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise ValueError("File exceeds configured size limit")

    digest = hashlib.sha256(content).hexdigest()
    storage = Path(settings.storage_dir)
    storage.mkdir(parents=True, exist_ok=True)
    path = storage / f"{uuid4().hex}{suffix}"
    path.write_bytes(content)
    return DocumentRef(
        id=uuid4(),
        analysis_id=analysis_id,
        filename=filename,
        sha256=digest,
        document_type=document_type,
        storage_path=str(path),
    )
