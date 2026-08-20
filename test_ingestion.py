from uuid import uuid4

import pytest

from app.domain.enums import DocumentType
from app.ingestion.service import ingest_file


def test_ingestion_preserves_analysis_and_hash(monkeypatch, tmp_path):
    monkeypatch.setattr("app.ingestion.service.settings.storage_dir", str(tmp_path))
    analysis_id = uuid4()
    ref = ingest_file("contract.pdf", b"contract", DocumentType.CONTRACT, analysis_id=analysis_id)

    assert ref.analysis_id == analysis_id
    assert len(ref.sha256) == 64
    assert ref.storage_path.endswith(".pdf")


def test_ingestion_rejects_unsupported_extension(monkeypatch, tmp_path):
    monkeypatch.setattr("app.ingestion.service.settings.storage_dir", str(tmp_path))
    with pytest.raises(ValueError, match="Unsupported file type"):
        ingest_file("contract.exe", b"x", DocumentType.CONTRACT)
