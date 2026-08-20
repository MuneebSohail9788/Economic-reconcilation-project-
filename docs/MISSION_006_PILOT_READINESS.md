# Mission 006 - Pilot Readiness

## Objective
Move from a tested synthetic MVP to a controlled pilot-ready implementation without expanding into enterprise integrations.

## Scope
- Real PDF/DOCX source fixtures for parser smoke tests.
- Provider-neutral HTTP structured-extraction adapter.
- Explicit provider configuration via environment variables.
- No secret values committed to the repository.
- Parser and extraction failure remain explicit failures; no fallback to invented facts.
- Pilot checklist and operator runbook.

## Required pilot controls
1. Use synthetic or customer-approved documents only.
2. Configure a dedicated AI provider endpoint and API key outside source control.
3. Keep analysis documents isolated by analysis ID.
4. Review every `VERIFIED` finding before customer action.
5. Preserve source evidence for every finding.
6. Record run history and failures.
7. Do not interpret extraction confidence as financial-loss probability.

## Out of scope
ERP integrations, payments, automatic invoice issuance, customer messaging, queues, Kubernetes, blockchain, and multi-tenant enterprise controls.
