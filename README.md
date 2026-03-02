# 📋 ClaimCheck Daily

An automated AI fact-checking pipeline that runs daily, researches claims from real news feeds using live web content, and publishes verdicts to a GitHub Pages website.

**Live site:** https://bharanirajendran-blip.github.io/ClaimCheck_Daily/

---

## What It Does

Every day the pipeline:
1. Pulls headlines from 7 RSS feeds (AP, Reuters, PolitiFact, FactCheck.org, WHO, Science Daily, MIT Tech Review)
2. GPT-4o (Director) selects the 5 most fact-checkable claims
3. Claude Opus (Researcher) fetches the live source articles and investigates each claim using extended thinking — in parallel
4. GPT-4o synthesises a verdict with a confidence score and key evidence
5. Results are published as a rendered HTML page and a JSON archive

---

## Architecture

```
feeds.yaml → harvest_node → select_node → research_node → verdict_node → publish_node
                              (GPT-4o)      (Claude Opus)    (GPT-4o)
                                            + fetch_url tool
```

Built with **LangGraph** (StateGraph pipeline) and **Pydantic** (validated data models throughout).

| Component | Role | Model |
|---|---|---|
| Director | Claim selection + verdict synthesis | GPT-4o |
| Researcher | Live web research with tool-use loop | Claude Opus + extended thinking |
| fetch_url tool | Fetches and strips article HTML to plain text | httpx + BeautifulSoup |
| Publisher | HTML + JSON output | — |

### How the Researcher tool-use loop works

Claude doesn't rely on training knowledge alone. When researching a claim it:
1. Calls `fetch_url` on the source article URL
2. Reads the returned plain text
3. Fetches additional corroborating sources as needed
4. Produces a structured research report grounded in the actual article content

This agentic loop continues for up to 5 rounds until Claude returns a final response.

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
│   ├── researcher.py   Claude Opus Researcher agent (tool-use loop)
│   ├── tools.py        fetch_url tool — live web article fetcher
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

- [Anthropic Claude](https://www.anthropic.com) — deep claim research with extended thinking + tool use
- [OpenAI GPT-4o](https://openai.com) — claim selection and verdict synthesis
- [LangGraph](https://langchain-ai.github.io/langgraph/) — stateful multi-agent pipeline
- [Pydantic v2](https://docs.pydantic.dev) — data validation and state modelling
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) — HTML stripping for web fetch tool
- [GitHub Pages](https://pages.github.com) — automated publishing

---

## Course

Grad5900 — Agentic AI
