"""
Pipeline — LangGraph StateGraph orchestration
----------------------------------------------
Graph nodes (in order):
  harvest_node   → parse feeds.yaml → populate state.candidates
  select_node    → Director (GPT) picks top claims → state.selected
  research_node  → Researcher (Claude) investigates each claim in parallel
  verdict_node   → Director synthesises one Verdict per ResearchResult
  publish_node   → Publisher writes docs/ HTML + outputs/ JSON

State is a Pydantic PipelineState model — every transition is validated.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph

from .director import Director
from .feeds import harvest_claims
from .models import DailyReport, PipelineState, ResearchResult
from .publisher import Publisher
from .researcher import Researcher
from .utils import setup_logging

logger = logging.getLogger(__name__)

# Singleton agent instances shared across node calls
_director   = Director()
_researcher = Researcher()


# ── Node functions ────────────────────────────────────────────────────────────

def harvest_node(state: PipelineState) -> dict[str, Any]:
    """Node 1 — ingest RSS/Atom feeds and populate candidate claims."""
    logger.info("[harvest] Parsing feeds from %s…", state.feeds_path)
    candidates = harvest_claims(state.feeds_path)
    logger.info("[harvest] %d candidate claims harvested.", len(candidates))
    return {"candidates": candidates}


def select_node(state: PipelineState) -> dict[str, Any]:
    """Node 2 — Director (GPT) scores and selects the day's best claims."""
    if not state.candidates:
        logger.warning("[select] No candidates to select from.")
        return {"selected": []}
    selected = _director.select_claims(state.candidates)
    logger.info("[select] Director chose %d claims.", len(selected))
    return {"selected": selected}


def research_node(state: PipelineState) -> dict[str, Any]:
    """
    Node 3 — Researcher (Claude) investigates each selected claim in parallel.
    Uses ThreadPoolExecutor for fan-out; results collected into research_results dict.
    """
    if not state.selected:
        logger.warning("[research] No claims to research.")
        return {"research_results": {}}

    results: dict[str, ResearchResult] = {}
    with ThreadPoolExecutor(max_workers=state.max_workers) as pool:
        futures = {pool.submit(_researcher.research, claim): claim for claim in state.selected}
        for future in as_completed(futures):
            claim = futures[future]
            try:
                results[claim.id] = future.result()
                logger.info("[research] Completed claim %s.", claim.id)
            except Exception as exc:
                logger.error("[research] Failed claim %s: %s", claim.id, exc)

    return {"research_results": results}


def verdict_node(state: PipelineState) -> dict[str, Any]:
    """Node 4 — Director (GPT) synthesises a structured Verdict per claim."""
    verdicts = []
    for claim in state.selected:
        research = state.research_results.get(claim.id)
        if not research:
            logger.warning("[verdict] No research for claim %s — skipping.", claim.id)
            continue
        try:
            verdict = _director.synthesize_verdict(claim, research)
            verdicts.append(verdict)
            logger.info("[verdict] %s → %s (%.0f%%)", claim.id, verdict.verdict, verdict.confidence * 100)
        except Exception as exc:
            logger.error("[verdict] Failed for claim %s: %s", claim.id, exc)
    return {"verdicts": verdicts}


def publish_node(state: PipelineState) -> dict[str, Any]:
    """Node 5 — Publisher renders HTML to docs/ and JSON to outputs/."""
    report = _director.build_report(state.verdicts, state.selected)
    Publisher(docs_dir=state.docs_dir, outputs_dir=state.outputs_dir).publish(report)
    logger.info("[publish] Report written → %s/%s.html", state.docs_dir, report.date_slug)
    return {"report": report}


# ── Conditional edges ─────────────────────────────────────────────────────────

def should_continue(state: PipelineState) -> str:
    return "end" if not state.candidates else "select"


def should_research(state: PipelineState) -> str:
    return "end" if not state.selected else "research"


# ── Graph construction ────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Construct and compile the ClaimCheck Daily LangGraph."""
    graph = StateGraph(PipelineState)

    graph.add_node("harvest",  harvest_node)
    graph.add_node("select",   select_node)
    graph.add_node("research", research_node)
    graph.add_node("verdict",  verdict_node)
    graph.add_node("publish",  publish_node)

    graph.add_edge(START, "harvest")
    graph.add_conditional_edges("harvest", should_continue,  {"select": "select",   "end": END})
    graph.add_conditional_edges("select",  should_research,  {"research": "research", "end": END})
    graph.add_edge("research", "verdict")
    graph.add_edge("verdict",  "publish")
    graph.add_edge("publish",  END)

    return graph.compile()


# ── Public entry point ────────────────────────────────────────────────────────

def run_pipeline(
    feeds_path:  str | Path = "feeds.yaml",
    docs_dir:    str | Path = "docs",
    outputs_dir: str | Path = "outputs",
    max_workers: int = 3,
    log_level:   str = "INFO",
) -> DailyReport:
    """Compile and invoke the LangGraph; return the final DailyReport."""
    setup_logging(log_level)
    logger.info("=== ClaimCheck Daily pipeline starting (LangGraph) ===")

    initial_state = PipelineState(
        feeds_path=str(feeds_path),
        docs_dir=str(docs_dir),
        outputs_dir=str(outputs_dir),
        max_workers=max_workers,
    )

    final_state = build_graph().invoke(initial_state)
    # LangGraph returns a dict; extract the report safely
    report = (final_state.get("report") if isinstance(final_state, dict) else final_state.report) or DailyReport()
    logger.info("=== Pipeline complete — %d verdicts ===", len(report.verdicts))
    return report
