# MISSION 007 — Controlled Pilot

## Purpose

Mission 007 validates the complete MVP against real file formats using a deterministic, non-customer pilot fixture set before a remote AI provider and customer data are introduced.

## Controlled pipeline

```text
PDF / DOCX
  ↓
Ingestion + SHA-256
  ↓
Docling parsing
  ↓
Page provenance
  ↓
Controlled structured extraction
  ↓
Pydantic validation
  ↓
Normalization
  ↓
Economic model
  ↓
Deterministic reconciliation
  ↓
Evidence verification
  ↓
Finding persistence
```

The controlled extractor is not a production AI model. It is a deterministic fixture provider whose only purpose is to establish that the real parser and downstream economic verification path work before provider credentials or customer documents are introduced.

## Locked pilot expectation

Contract: `100 hours × USD 150/hour`

Approved amendment: `+20 hours × USD 150/hour`

Invoice: `100 hours × USD 150/hour`

Expected entitlement: `USD 18,000`

Captured: `USD 15,000`

Difference: `USD 3,000`

Expected reconciliation: `CHANGE_VALUE_NOT_CAPTURED`

## Operator command

```bash
python scripts/run_pilot.py
```

The command must print `CONTROLLED PILOT: PASS` and the expected values above.

## Promotion gate for a real customer pilot

A real-customer run is not promoted merely because the controlled pilot passes. The following must be completed by the operator:

1. Select and document an AI provider endpoint.
2. Store credentials only in environment/secret management, never in source control.
3. Confirm customer authorization and data-handling terms.
4. Run one customer analysis in a sandbox/test account first.
5. Review every generated finding and its evidence chain manually.
6. Record extraction accuracy, false positives, false negatives and review outcomes.
7. Keep the economic engine unchanged during the observation window unless a separately reviewed defect is found.
8. Do not treat technical pilot success as proof of PMF, recoverable revenue or customer ROI.
