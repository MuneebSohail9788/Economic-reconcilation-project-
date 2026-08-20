# Economic Truth Engine

## Economic Break Detector — Mission 005 MVP + Mission 006 Pilot Readiness + Mission 007 Controlled Pilot

This repository is the executable MVP for the locked Economic Break Detector specification.

```text
Document
  ↓
Ingestion
  ↓
Parsing
  ↓
Structured Fact Extraction
  ↓
Pydantic Validation
  ↓
Normalization
  ↓
Economic Model
  ↓
Deterministic Reconciliation
  ↓
Evidence Verification
  ↓
Finding
  ↓
Persistent API
```

### Non-negotiable invariants

1. No source → no fact.
2. No sufficient evidence → no verified finding.
3. Money uses `Decimal`, never float.
4. AI proposes/extracts facts; deterministic code calculates economic results.
5. Source document, page and original text remain traceable.
6. Parser and AI provider are adapter boundaries.
7. Cross-document rate differences use the explicit `RATE_MISMATCH` rule; ambiguous multiple rates inside one source role require `REVIEW_REQUIRED`.
8. Duplicate economic events are hard-stopped.
9. Currency conflicts are never silently converted.
10. Reconciliation is deterministic and reproducible.

## Stack

- Python 3.11–3.13
- FastAPI
- Pydantic / pydantic-settings
- SQLAlchemy 2.x
- PostgreSQL in Docker; SQLite is supported for local smoke tests
- Docling adapter for PDF/DOCX parsing
- Provider-neutral structured AI extraction boundary
- pytest
- Docker / Docker Compose

## API

```text
POST /analyses
POST /documents?analysis_id=<id>&document_type=<type>
POST /analyses/{id}/run
POST /analyses/{id}/retry
GET  /analyses/{id}
GET  /analyses/{id}/documents
GET  /analyses/{id}/runs
GET  /findings/{id}
GET  /findings/{id}/evidence
GET  /analyses/{id}/report
GET  /health
```

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
pytest -q
uvicorn app.main:app --reload
```

For PostgreSQL:

```bash
docker compose up --build
```

## Extraction configuration

The repository deliberately does **not** hard-code an AI vendor because the implementation contract only specifies an adapter boundary, not a vendor. The production default therefore fails safely with an explicit "provider not configured" error instead of fabricating facts.

For deterministic local tests, the test suite uses in-process fixture providers. A concrete provider adapter can implement `StructuredAIProvider` without changing the economic or reconciliation layers.

## Acceptance gates

The test suite contains:

- 60 locked golden cases (`TC-001` → `TC-060`)
- 10 adversarial cases (`ADV-001` → `ADV-010`)
- unit tests for normalization, economic modeling, extraction, evidence, reconciliation and API behavior
- an end-to-end API test covering create analysis → upload documents → run → persist finding → retrieve finding

Run everything:

```bash
pytest -q
```

Run only acceptance:

```bash
python scripts/run_acceptance.py
```

The implementation must keep expected answers fixed. Tests are the contract; implementation changes to make tests pass are acceptable, changing expected answers to match incorrect implementation is not.

## Mission 006 pilot readiness

Mission 006 adds a provider-neutral HTTP structured-extraction adapter, real PDF/DOCX pilot fixtures, pilot validation tests, and operator/security checklists. The adapter accepts a strict `{ "facts": [...] }` response contract and never performs reconciliation.

See `docs/MISSION_006_PILOT_READINESS.md` and `docs/PILOT_CHECKLIST.md`.

## Production boundary

The MVP is intentionally a modular monolith. It does not require SAP/Oracle/CRM integrations, background queues, Redis, RabbitMQ, Kubernetes, microservices, automated invoicing, payment collection, or a complex frontend.

The final external dependency before a real customer run is the customer's chosen AI provider adapter and real source documents. Everything behind that adapter—validation, normalization, economic modeling, deterministic reconciliation, evidence checks, state transitions, persistence and findings—is provider-independent.

## Mission 007 controlled pilot

Run the complete local PDF/DOCX pilot without external AI credentials:

```bash
python scripts/run_pilot.py
```

This uses the same `DocumentParser` boundary and full persistence/reconciliation/finding path, with a deterministic fixture extractor. It is a controlled technical proof, not a customer or production AI run. See `docs/MISSION_007_CONTROLLED_PILOT.md`.

## Production startup

Production containers run migrations before Uvicorn starts. The entrypoint refuses to start when API authentication is enabled without `API_KEY`, or when AI extraction mode is selected without `AI_PROVIDER_URL`.

```bash
docker compose up --build
```

For a real customer deployment, supply secrets through the deployment platform rather than committing `.env` or API keys to source control.

## Operational completion boundary

The codebase is feature-complete for the locked MVP and controlled pilot. The only steps that cannot be fabricated inside this development environment are external: a real AI-provider credential, a real production PostgreSQL instance, and customer-approved source documents. Once supplied, the same pipeline is configured through environment variables; reconciliation/evidence logic does not change.
