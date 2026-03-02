# 📋 ClaimCheck Daily

An automated AI fact-checking pipeline that runs daily, researches claims from real news feeds, and publishes verdicts to a GitHub Pages website.

**Live site:** https://bharanirajendran-blip.github.io/ClaimCheck_Daily/

---

## What It Does

Every day the pipeline:
1. Pulls headlines from 7 RSS feeds (AP, Reuters, PolitiFact, FactCheck.org, WHO, Science Daily, MIT Tech Review)
2. GPT-4o (Director) selects the 5 most fact-checkable claims
3. Claude Opus (Researcher) investigates each claim using extended thinking — in parallel
4. GPT-4o synthesises a verdict with a confidence score and key evidence
5. Results are published as a rendered HTML page and a JSON archive

---

## Architecture

```
feeds.yaml → harvest_node → select_node → research_node → verdict_node → publish_node
                              (GPT-4o)      (Claude Opus)    (GPT-4o)
```

Built with **LangGraph** (StateGraph pipeline) and **Pydantic** (validated data models throughout).

| Component | Role | Model |
|---|---|---|
| Director | Claim selection + verdict synthesis | GPT-4o |
| Researcher | Deep evidence research | Claude Opus (extended thinking) |
| Publisher | HTML + JSON output | — |

---

## Verdict Labels

| Label | Meaning |
|---|---|
| ✅ TRUE | Claim is accurate |
| 🟢 MOSTLY TRUE | Accurate with minor caveats |
| 🟡 MIXED | Partially true, partially false |
| 🟠 MOSTLY FALSE | Misleading or largely inaccurate |
| ❌ FALSE | Claim is inaccurate |
| ❔ UNVERIFIABLE | Insufficient evidence to judge |

---

## Project Structure

```
ClaimCheck_Daily/
├── agent/
│   ├── models.py       Pydantic data models + LangGraph PipelineState
│   ├── director.py     GPT-4o Director agent
│   ├── researcher.py   Claude Opus Researcher agent
│   ├── feeds.py        RSS/Atom feed parser
│   ├── pipeline.py     LangGraph StateGraph orchestration
│   ├── publisher.py    HTML + JSON renderer
│   └── utils.py        retry, logging, env helpers
├── docs/               GitHub Pages output (auto-generated)
├── outputs/            JSON archive (auto-generated)
├── feeds.yaml          RSS feed configuration
├── run.py              CLI entry point
├── SPEC.md             Full technical specification
└── SETUP.md            Setup and usage guide
```

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up API keys
cp .env.example .env
# Add ANTHROPIC_API_KEY and OPENAI_API_KEY to .env

# 3. Test without spending API credits
python run.py --dry-run

# 4. Full run
python run.py
```

See [SETUP.md](SETUP.md) for full setup instructions and troubleshooting.

---

## Output

Each run produces:
- `docs/YYYY-MM-DD.html` — rendered fact-check report (dark-themed, viewable in browser)
- `outputs/YYYY-MM-DD.json` — machine-readable verdicts

---

## Tech Stack

- [Anthropic Claude](https://www.anthropic.com) — deep claim research with extended thinking
- [OpenAI GPT-4o](https://openai.com) — claim selection and verdict synthesis
- [LangGraph](https://langchain-ai.github.io/langgraph/) — stateful multi-agent pipeline
- [Pydantic v2](https://docs.pydantic.dev) — data validation and state modelling
- [GitHub Pages](https://pages.github.com) — automated publishing

---

## Course

Grad5900 — Agentic AI
