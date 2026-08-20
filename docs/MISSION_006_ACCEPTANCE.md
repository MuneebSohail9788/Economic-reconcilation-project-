# Mission 006 Acceptance

## Scope
Pilot-readiness hardening after Mission 005 MVP completion.

## Completed
- Provider-neutral HTTP structured extraction adapter.
- Explicit AI provider configuration with environment variables.
- Safe provider failure when endpoint is missing/unreachable/invalid.
- Real PDF and DOCX pilot fixtures.
- Render verification of all pilot fixture documents.
- Pilot source readability tests.
- Pilot operator checklist.
- Security and operations guidance carried forward from Mission 005.

## Automated gates
- Unit/integration/acceptance suite: PASS.
- Python compileall: PASS.
- Pilot fixture readability: PASS.
- Pilot fixture render existence: PASS.

## Explicit external gates not claimed
- Real customer documents: not available in the repository.
- Concrete vendor account/API credentials: not available and not committed.
- Docker build: depends on a Docker-enabled environment.
- Production network connectivity: depends on customer infrastructure.

## Success definition
A pilot is technically ready when a customer-approved contract, amendment and invoice can be ingested, parsed, extracted by a configured provider, validated against source evidence, reconciled deterministically, and persisted with a traceable finding.
