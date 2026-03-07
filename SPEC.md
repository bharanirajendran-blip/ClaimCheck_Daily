# ClaimCheck Daily — Project Specification

**Course:** Grad5900 — Agentic AI
**Author:** Bharani Rajendran
**Date:** 2026-03-02
**Repo:** https://github.com/bharanirajendran-blip/ClaimCheck_Daily
**Live site:** https://bharanirajendran-blip.github.io/ClaimCheck_Daily/

---

## 1. Project Overview

ClaimCheck Daily is an automated fact-checking pipeline that runs every day, pulls claims from real news and fact-checking RSS feeds, researches each one using AI with live web access, produces verdicts, and publishes the results as a GitHub Pages website.

The core idea is a two-agent architecture where each agent does what it is best at: GPT-4o acts as a high-level Director that selects and evaluates claims, and Claude acts as a deep Researcher that fetches and reads live articles then investigates the evidence. LangGraph wires the agents together into a stateful, validated pipeline. Pydantic enforces data integrity at every step.

---

## 2. Architecture

### 2.1 Agent Roles

**Director (GPT-4o)**
- Reads all harvested claim candidates and selects the top 3 most impactful and verifiable ones for the day
- Enforces source diversity — no two claims from the same outlet, covering at least 2 different topics (political, science, technology)
- Prefers disputed claims from PolitiFact/FactCheck.org, avoids press releases and paywalled sources
- After research is complete, synthesises a structured verdict for each claim including a label, confidence score, summary, and key evidence
- Uses OpenAI's JSON mode to guarantee parseable structured output

**Researcher (Claude Opus)**
- Receives one claim at a time from the pipeline
- Runs an agentic tool-use loop: calls `fetch_url` to read live article content, then reasons over it
- Uses extended thinking (3,000 budget tokens, 10,000 max tokens) to deeply reason through the claim
- Fetches the source URL first, then at most one corroborating source — writes findings immediately after
- Produces a structured research report covering sub-questions, supporting evidence, contradicting evidence, caveats, and key sources
- Claims are researched sequentially (max_workers=1) to stay within API rate limits

**fetch_url tool**
- Defined in `agent/tools.py` using the Anthropic tool-use API schema
- Fetches a URL using `httpx`, strips HTML with BeautifulSoup, returns clean plain text
- Truncates to 4,000 characters to stay within context window limits
- Claude decides autonomously when and what to fetch — it is not hardcoded
- Max 5 tool-use rounds per claim to prevent infinite loops

### 2.2 Researcher Agentic Tool-Use Loop

```
User message (claim + source URL)
        │
        ▼
  Claude reasons → calls fetch_url(url)
        │
        ▼
  tools.py fetches URL → returns plain text
        │
        ▼
  Claude reads article → may call fetch_url again for more sources
        │
        ▼
  Claude produces final structured research report
        │  (max 5 rounds to prevent infinite loops)
        ▼
  ResearchResult returned to pipeline
```

### 2.3 Pipeline Flow (LangGraph StateGraph)

```
START
  │
  ▼
harvest_node       ← parse RSS/Atom feeds → candidate Claims
  │
  ▼ (conditional: abort if no candidates)
select_node        ← Director (GPT-4o) picks top 3 claims (diverse sources/topics)
  │
  ▼ (conditional: abort if nothing selected)
research_node      ← Researcher (Claude + fetch_url) investigates sequentially
  │
  ▼
verdict_node       ← Director synthesises one Verdict per ResearchResult
  │
  ▼
publish_node       ← Publisher writes HTML to docs/ and JSON to outputs/
  │
  ▼
END
```

The graph has two conditional edges that short-circuit the pipeline early with a clean exit if no usable claims are found at either the harvest or selection stage.

### 2.4 State Management

All state is carried in a single `PipelineState` Pydantic model that flows through every LangGraph node. Each node receives the full state, updates only its own fields, and returns a partial dict that LangGraph merges back. This means the whole pipeline state is inspectable and validated at every transition.

---

## 3. Data Models (Pydantic)

All models are defined in `agent/models.py` and use `pydantic.BaseModel`.

| Model | Purpose | Key Fields |
|---|---|---|
| `Claim` | One harvested claim | `id`, `text`, `source`, `url`, `published_at` |
| `ResearchResult` | Claude's research output | `claim_id`, `findings`, `sources` |
| `Verdict` | GPT's final judgement | `claim_id`, `verdict` (enum), `confidence` (0–1), `summary`, `key_evidence` |
| `DailyReport` | Full day's output | `claims`, `verdicts`, `date_slug`, `generated_at` |
| `PipelineState` | LangGraph shared state | all of the above + config fields |

`VerdictLabel` is a `str, Enum` with six possible values: `TRUE`, `MOSTLY_TRUE`, `MIXED`, `MOSTLY_FALSE`, `FALSE`, `UNVERIFIABLE`. Pydantic validates that GPT's output matches one of these values and that `confidence` is between 0.0 and 1.0.

---

## 4. Repository Structure

```
ClaimCheck_Daily/
├── agent/
│   ├── __init__.py        package exports
│   ├── models.py          Pydantic data models + PipelineState
│   ├── director.py        GPT-4o Director agent
│   ├── researcher.py      Claude Opus Researcher agent (tool-use loop)
│   ├── tools.py           fetch_url tool — live web article fetcher
│   ├── feeds.py           RSS/Atom feed parser
│   ├── pipeline.py        LangGraph StateGraph orchestration
│   ├── publisher.py       HTML + JSON output renderer
│   └── utils.py           retry decorator, logging, env helpers
│
├── docs/                  GitHub Pages output (auto-generated)
│   ├── _config.yml        Jekyll config
│   ├── index.html         landing page (regenerated each run)
│   └── YYYY-MM-DD.html    one page per daily report
│
├── outputs/               JSON archive (auto-generated)
│   └── YYYY-MM-DD.json    machine-readable verdicts per day
│
├── .github/workflows/
│   └── daily.yml          GitHub Actions cron job (08:00 UTC daily)
│
├── feeds.yaml             RSS feed configuration
├── .env.example           environment variable template
├── requirements.txt       Python dependencies
├── run.py                 CLI entry point
├── SPEC.md                this file
└── .gitignore
```

---

## 5. Feed Sources

Configured in `feeds.yaml`. Seven sources across four categories:

| Source | Category |
|---|---|
| AP News — Top Headlines | news |
| Reuters — Top News | news |
| PolitiFact — Latest | politics |
| FactCheck.org | politics |
| Science Daily — Top Science | science |
| WHO — News | health |
| MIT Technology Review | technology |

Each run harvests up to 10 entries per feed (70 candidates max), which the Director narrows to 3.

---

## 6. Output Format

### HTML Report (`docs/YYYY-MM-DD.html`)
A dark-themed GitHub Pages page with one card per claim. Each card shows the verdict badge (colour-coded), the claim text, source link, confidence percentage, summary, and a collapsible key evidence section.

### JSON Archive (`outputs/YYYY-MM-DD.json`)

```json
{
  "date": "2026-03-02",
  "generated_at": "2026-03-02T17:30:30Z",
  "results": [
    {
      "claim": "...",
      "source": "...",
      "verdict": "MIXED",
      "confidence": 0.85,
      "summary": "...",
      "key_evidence": ["...", "..."]
    }
  ]
}
```

---

## 7. Dependencies

| Package | Version | Purpose |
|---|---|---|
| `anthropic` | ≥ 0.40.0 | Claude Researcher API (extended thinking + tool use) |
| `openai` | ≥ 1.50.0 | GPT-4o Director API (JSON mode) |
| `langgraph` | ≥ 0.2.0 | StateGraph pipeline orchestration |
| `langchain-core` | ≥ 0.3.0 | Required by LangGraph |
| `pydantic` | ≥ 2.7.0 | Data validation and state modelling |
| `feedparser` | ≥ 6.0.11 | RSS/Atom feed ingestion |
| `httpx` | ≥ 0.27.0 | HTTP client for fetch_url tool |
| `beautifulsoup4` | ≥ 4.12.0 | HTML stripping for fetch_url tool |
| `python-dotenv` | ≥ 1.0.0 | `.env` loading |
| `pyyaml` | ≥ 6.0.2 | `feeds.yaml` parsing |

---

## 8. Running Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env
# Edit .env and add ANTHROPIC_API_KEY and OPENAI_API_KEY

# 3. Dry run (feed harvest + GPT selection only, no Claude research)
python run.py --dry-run

# 4. Full pipeline run
python run.py

# 5. Optional flags
python run.py --feeds my_feeds.yaml --log-level DEBUG --workers 5
```

---

## 9. Known Limitations

**Paywalled articles:** The `fetch_url` tool can only read publicly accessible pages. Paywalled content returns a login page instead of article text. Claude handles this gracefully by falling back to training knowledge for those sources.

**Claim extraction:** The current feed parser uses the article headline as the claim text. Headlines are not always precise factual claims. A future improvement is to extract specific sub-claims from article bodies.

**No deduplication:** The same claim can appear across multiple feeds on multiple days. A content-hash dedup layer would prevent redundant research.

---

## 10. Changelog

| Version | Date | Changes |
|---|---|---|
| v1.0 | 2026-03-02 | Initial skeleton — LangGraph pipeline, Pydantic models, Claude Researcher, GPT Director, GitHub Pages publishing |
| v1.1 | 2026-03-02 | Added `fetch_url` tool-use loop to Researcher — Claude now reads live articles instead of relying solely on training knowledge |
| v1.2 | 2026-03-07 | Tuned for reliability — reduced claims to 3, sequential research, 3k thinking budget, 4k content cap, Director diversity rules, Researcher stop-early prompt |

---

## 11. Planned Upgrades

- LangGraph checkpointing so the pipeline can resume after a crash
- Human-in-the-loop approval node between verdict and publish
- Extract specific sub-claims from article bodies rather than using headlines
- Add claim deduplication across days
- Multi-day trends page showing verdict distribution over time
