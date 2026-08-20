from __future__ import annotations

import json
from urllib import error, request

from app.domain.schemas import ParsedDocument
from app.extraction.ai import FactExtractionError
from app.extraction.interfaces import StructuredAIProvider


class HTTPStructuredAIProvider(StructuredAIProvider):
    """Provider-neutral HTTP adapter for structured fact extraction.

    Request contract:
      POST <endpoint>
      Authorization: Bearer <api-key> (when configured)
      JSON body: {"model": ..., "document": {"document_id": ..., "pages": {...}}}

    Response contract:
      {"facts": [<EconomicFact-compatible objects>]}

    The adapter deliberately knows nothing about reconciliation or financial truth.
    """

    def __init__(self, endpoint: str, api_key: str | None = None, model: str | None = None, timeout: float = 60.0):
        if not endpoint:
            raise ValueError("AI provider endpoint is required")
        self.endpoint = endpoint
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def extract_economic_facts(self, document: ParsedDocument) -> list[dict]:
        payload = {
            "model": self.model,
            "document": {
                "document_id": str(document.document_id),
                "document_type": document.document_type.value,
                "pages": {str(k): v for k, v in document.pages.items()},
            },
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = request.Request(self.endpoint, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                if response.status < 200 or response.status >= 300:
                    raise FactExtractionError(f"AI provider returned HTTP {response.status}")
                raw = response.read()
        except error.HTTPError as exc:
            raise FactExtractionError(f"AI provider HTTP error {exc.code}") from exc
        except error.URLError as exc:
            raise FactExtractionError("AI provider could not be reached") from exc
        except TimeoutError as exc:
            raise FactExtractionError("AI provider request timed out") from exc

        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise FactExtractionError("AI provider returned invalid JSON") from exc
        facts = parsed.get("facts") if isinstance(parsed, dict) else None
        if not isinstance(facts, list):
            raise FactExtractionError("AI provider response must contain a 'facts' list")
        return facts
