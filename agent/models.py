"""
Shared data models for ClaimCheck Daily.
Uses Pydantic BaseModel for validation, serialization, and schema generation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


def _new_id() -> str:
    return str(uuid.uuid4())[:8]


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ── Verdict enum ──────────────────────────────────────────────────────────────

class VerdictLabel(str, Enum):
    TRUE         = "TRUE"
    MOSTLY_TRUE  = "MOSTLY_TRUE"
    MIXED        = "MIXED"
    MOSTLY_FALSE = "MOSTLY_FALSE"
    FALSE        = "FALSE"
    UNVERIFIABLE = "UNVERIFIABLE"


# ── Core models ───────────────────────────────────────────────────────────────

class Claim(BaseModel):
    """A single checkable claim harvested from a feed."""
    id:           str           = Field(default_factory=_new_id)
    text:         str
    source:       str
    published_at: Optional[str] = None
    feed_name:    Optional[str] = None
    url:          Optional[str] = None

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Claim text must not be empty.")
        return v.strip()


class ResearchResult(BaseModel):
    """Raw findings returned by the Claude Researcher."""
    claim_id: str
    findings: str
    sources:  list[dict] = Field(default_factory=list)


class Verdict(BaseModel):
    """Structured verdict produced by the GPT Director."""
    claim_id:     str
    verdict:      VerdictLabel
    confidence:   float      = Field(..., ge=0.0, le=1.0)
    summary:      str
    key_evidence: list[str]  = Field(default_factory=list)


class DailyReport(BaseModel):
    """Complete report for one publishing cycle."""
    claims:       list[Claim]         = Field(default_factory=list)
    verdicts:     list[Verdict]       = Field(default_factory=list)
    generated_at: str                 = Field(default_factory=_utcnow)
    date_slug:    str                 = Field(default_factory=_today_slug)

    def get_verdict(self, claim_id: str) -> Optional[Verdict]:
        return next((v for v in self.verdicts if v.claim_id == claim_id), None)


# ── LangGraph pipeline state ──────────────────────────────────────────────────

class PipelineState(BaseModel):
    """
    Typed state object passed between every LangGraph node.
    Each node receives the full state, updates its own fields, and returns it.
    Pydantic ensures every mutation is validated at runtime.
    """
    # Runtime config (injected once at graph invocation)
    feeds_path:  str = "feeds.yaml"
    docs_dir:    str = "docs"
    outputs_dir: str = "outputs"
    max_workers: int = 3

    # Data fields populated progressively by each node
    candidates:       list[Claim]               = Field(default_factory=list)
    selected:         list[Claim]               = Field(default_factory=list)
    research_results: dict[str, ResearchResult] = Field(default_factory=dict)
    verdicts:         list[Verdict]             = Field(default_factory=list)
    report:           Optional[DailyReport]     = None
