from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.middleware import RequestContextMiddleware
from app.database.init import initialize_database


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Economic Truth Engine", version="0.4.0", lifespan=lifespan)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=_csv(settings.trusted_hosts) + (["testserver"] if settings.app_env == "development" else []))
app.add_middleware(
    CORSMiddleware,
    allow_origins=_csv(settings.allowed_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
