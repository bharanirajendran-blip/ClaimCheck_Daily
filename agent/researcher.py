"""
Researcher — Claude-powered deep research agent
-------------------------------------------------
Responsibilities:
  1. Accept a single Claim from the Director
  2. Use Claude (claude-opus-4-5 / sonnet) with extended thinking to:
       - Decompose the claim into verifiable sub-questions
       - Evaluate each piece of evidence
       - Identify primary sources, statistics, expert consensus
  3. Return a ResearchResult (raw findings + structured sources list)

Claude is chosen for research because of its nuanced reading of long documents,
careful citation behaviour, and support for extended thinking.
"""

from __future__ import annotations

import logging
import textwrap
from dataclasses import dataclass, field

import anthropic

from .models import Claim, ResearchResult
from .utils import retry

logger = logging.getLogger(__name__)

RESEARCH_SYSTEM_PROMPT = textwrap.dedent("""\
    You are a meticulous research analyst for ClaimCheck Daily.
    Your task is to rigorously evaluate a claim by:

    1. Breaking it into verifiable sub-questions.
    2. Assessing what the evidence would need to show for the claim to be true.
    3. Identifying the strongest supporting AND contradicting evidence you know of.
    4. Noting important caveats, missing context, or ambiguities.
    5. Listing the key sources (with URLs where possible).

    Be precise. Avoid speculation. If you are uncertain, say so explicitly.
    Structure your response as follows:

    ## Sub-questions
    [numbered list]

    ## Evidence Assessment
    [detailed prose, balanced]

    ## Supporting evidence
    [bullet points with sources]

    ## Contradicting evidence
    [bullet points with sources]

    ## Caveats & Missing Context
    [prose]

    ## Key Sources
    [list of {"title": "...", "url": "...", "reliability": "high|medium|low"}]
""")


@dataclass
class Researcher:
    model: str = "claude-opus-4-5-20251101"
    max_tokens: int = 16000       # must be greater than thinking_budget
    use_extended_thinking: bool = True
    thinking_budget: int = 10000  # tokens allocated to <thinking>
    _client: anthropic.Anthropic = field(
        default_factory=anthropic.Anthropic, init=False, repr=False
    )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def research(self, claim: Claim) -> ResearchResult:
        """Deep-research a single claim and return structured findings."""
        logger.info("Researcher investigating claim %s: %s", claim.id, claim.text[:80])

        raw_text = self._call_claude(claim)
        sources = self._extract_sources(raw_text)

        return ResearchResult(
            claim_id=claim.id,
            findings=raw_text,
            sources=sources,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @retry(times=3, delay=3)
    def _call_claude(self, claim: Claim) -> str:
        user_message = (
            f"Claim to investigate:\n\n\"{claim.text}\"\n\n"
            f"Original source: {claim.source}\n"
            f"Published: {claim.published_at or 'unknown'}\n\n"
            "Please research this claim thoroughly."
        )

        kwargs: dict = dict(
            model=self.model,
            max_tokens=self.max_tokens,
            system=RESEARCH_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        if self.use_extended_thinking:
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": self.thinking_budget,
            }
            # Extended thinking requires temperature=1
            kwargs["temperature"] = 1

        response = self._client.messages.create(**kwargs)

        # Collect text blocks (ignore thinking blocks)
        parts = [
            block.text
            for block in response.content
            if hasattr(block, "text")
        ]
        return "\n".join(parts).strip()

    @staticmethod
    def _extract_sources(raw: str) -> list[dict]:
        """
        Naïve extraction of the Key Sources section.
        The Director doesn't need full JSON here — it reads the findings prose.
        This is a best-effort helper for the publisher.
        """
        import json, re

        sources = []
        # Look for JSON-ish objects inside the Key Sources section
        pattern = r'\{[^{}]*"title"[^{}]*\}'
        for match in re.finditer(pattern, raw, re.DOTALL):
            try:
                sources.append(json.loads(match.group()))
            except json.JSONDecodeError:
                pass
        return sources
