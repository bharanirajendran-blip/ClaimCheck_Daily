"""
Director — GPT-4o orchestration layer
--------------------------------------
Responsibilities:
  1. Score & rank candidate claims by newsworthiness / checkability
  2. Dispatch selected claims to the Claude Researcher
  3. Synthesise research results into validated Pydantic Verdict objects
  4. Assemble the final DailyReport
"""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI

from .models import Claim, DailyReport, ResearchResult, Verdict, VerdictLabel
from .utils import retry

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are the Director of ClaimCheck Daily, a rigorous automated fact-checking service.
Your job is to:
1. Select the most impactful, verifiable claims from the candidate list.
2. After a researcher provides evidence, produce a clear verdict with a confidence score.

Always respond with valid JSON matching the schema provided in each user message."""

SELECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "selected": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of claim IDs chosen for fact-checking (max 5)",
        },
        "reasoning": {"type": "string"},
    },
    "required": ["selected", "reasoning"],
}

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": [v.value for v in VerdictLabel],
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "summary": {"type": "string"},
        "key_evidence": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["verdict", "confidence", "summary", "key_evidence"],
}


class Director:
    """GPT-4o powered Director agent."""

    def __init__(self, model: str = "gpt-4o", max_claims_per_day: int = 5):
        self.model = model
        self.max_claims_per_day = max_claims_per_day
        self._client = OpenAI()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def select_claims(self, candidates: list[Claim]) -> list[Claim]:
        """Ask GPT to rank and pick the best claims for today."""
        logger.info("Director selecting from %d candidates…", len(candidates))
        payload = [{"id": c.id, "text": c.text, "source": c.source} for c in candidates]

        response = self._chat(
            f"Select up to {self.max_claims_per_day} claims worth fact-checking today.\n\n"
            f"Candidates:\n{json.dumps(payload, indent=2)}\n\n"
            f"Respond with JSON matching schema:\n{json.dumps(SELECTION_SCHEMA)}"
        )

        selected_ids = set(response.get("selected", []))
        chosen = [c for c in candidates if c.id in selected_ids]
        logger.info("Director selected %d claims.", len(chosen))
        return chosen

    def synthesize_verdict(self, claim: Claim, research: ResearchResult) -> Verdict:
        """Turn raw research into a Pydantic-validated Verdict."""
        logger.info("Director synthesising verdict for claim %s…", claim.id)

        response = self._chat(
            f"Claim: {claim.text}\n\n"
            f"Research findings:\n{research.findings}\n\n"
            f"Sources consulted:\n{json.dumps(research.sources, indent=2)}\n\n"
            f"Respond with JSON matching schema:\n{json.dumps(VERDICT_SCHEMA)}"
        )

        # Pydantic validates verdict enum + confidence range here
        return Verdict(
            claim_id=claim.id,
            verdict=VerdictLabel(response["verdict"]),
            confidence=float(response["confidence"]),
            summary=response["summary"],
            key_evidence=response.get("key_evidence", []),
        )

    def build_report(self, verdicts: list[Verdict], claims: list[Claim]) -> DailyReport:
        """Assemble the final DailyReport Pydantic model."""
        claim_map = {c.id: c for c in claims}
        return DailyReport(
            verdicts=verdicts,
            claims=[claim_map[v.claim_id] for v in verdicts if v.claim_id in claim_map],
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @retry(times=3, delay=2)
    def _chat(self, user_content: str) -> dict[str, Any]:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        return json.loads(response.choices[0].message.content)
