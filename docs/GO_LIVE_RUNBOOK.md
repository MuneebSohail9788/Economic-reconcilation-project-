# Economic Truth Engine — Go-Live Runbook

## Required external inputs

- Production PostgreSQL connection string
- Chosen structured-extraction provider endpoint/model
- Provider credential if required
- Customer-approved contract/amendment/invoice documents
- Deployment DNS/TLS and secret management

## Preflight

1. Set `APP_ENV=production`.
2. Set `API_AUTH_ENABLED=true` and a secret `API_KEY`.
3. Set `DATABASE_URL` to production PostgreSQL.
4. Set `EXTRACTION_MODE=ai`.
5. Set `AI_PROVIDER_URL` and `AI_MODEL`.
6. Set `TRUSTED_HOSTS` and `ALLOWED_ORIGINS` to production values.
7. Run the container; migrations execute automatically.
8. Check `GET /health`.

## Pilot acceptance

For every pilot analysis, preserve:

- original files and SHA-256 hashes
- parsed pages
- extracted facts and source locations
- normalized facts
- economic model
- reconciliation result
- finding evidence
- run history and errors

No production finding should be treated as verified unless the evidence chain is complete.

## Rollback

Stop the new API deployment, restore the previous container/image, and preserve the database plus object storage. Do not delete source documents during rollback.
