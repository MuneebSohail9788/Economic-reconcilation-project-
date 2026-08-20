from __future__ import annotations

from fastapi import Header, HTTPException

from app.core.config import settings


def require_api_key(authorization: str | None = Header(default=None)) -> None:
    """Optional API-key gate. Disabled by default for local development/tests."""
    if not settings.api_auth_enabled:
        return
    if not settings.api_key:
        raise HTTPException(status_code=503, detail="API authentication is enabled but no API key is configured")
    expected = f"Bearer {settings.api_key}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid API credentials")
