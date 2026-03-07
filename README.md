# 📋 ClaimCheck Daily

An automated AI fact-checking pipeline that runs daily, researches claims from real news feeds using live web content, and publishes verdicts to a GitHub Pages website.

**Live site:** https://bharanirajendran-blip.github.io/ClaimCheck_Daily/

---

## What It Does

Every day the pipeline:
1. Pulls headlines from 7 RSS feeds (AP, Reuters, PolitiFact, FactCheck.org, WHO, Science Daily, MIT Tech Review)
2. GPT-4o (Director) selects the 3 most fact-checkable claims — from different sources and topics
3. Claude Opus (Researcher) fetches the live source articles and investigates each claim using extended thinking
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
3. Writes a structured analysis immediately after reading the source
4. Produces a research report with sub-questions, evidence, caveats, and key sources

This agentic loop runs for up to 5 rounds until Claude returns a final response.

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
└── SPEC.md             Full technical specification
```

---

## Setup

### Requirements

You need two API keys:

| Key | Where to get it |
|---|---|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com → API Keys |
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys |

### Install & Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up API keys
cp .env.example .env
# Open .env and add your ANTHROPIC_API_KEY and OPENAI_API_KEY

# 3. Test without spending Claude credits
python run.py --dry-run

# 4. Full pipeline run (~2 minutes, ~$0.60)
python run.py
```

### Optional flags

```bash
python run.py --log-level DEBUG        # verbose logging
python run.py --dry-run                # skip Claude research
python run.py --workers 2              # increase parallel workers (default: 1)
```

### Output files

| File | Description |
|---|---|
| `docs/YYYY-MM-DD.html` | Dark-themed report, open in any browser |
| `docs/index.html` | Landing page with links to all past reports |
| `outputs/YYYY-MM-DD.json` | Machine-readable verdicts |

```bash
open docs/$(date +%Y-%m-%d).html      # macOS
```

---

## GitHub Actions Automation (Currently Disabled)

The repo includes `.github/workflows/daily.yml` which runs the pipeline automatically at 08:00 UTC and publishes to GitHub Pages.

**It is currently disabled.** To re-enable safely:
1. Make the repo **private** (Settings → General → Change visibility)
2. Add secrets under Settings → Secrets and variables → Actions:
   - `ANTHROPIC_API_KEY`
   - `OPENAI_API_KEY`
3. Go to **Actions tab → ClaimCheck Daily → Enable workflow**

---

## Troubleshooting

**`max_tokens must be greater than thinking.budget_tokens`**
Make sure you have the latest `researcher.py` — `max_tokens=10000`, `thinking_budget=3000`.

**`Repository not found` when pushing**
Create the repo on github.com first (empty, no README), then push.

**`src refspec main does not match any`**
No commits yet — run `git add . && git commit -m "initial"` first.
Or rename the branch: `git branch -m master main`.

**Paywalled articles return login page content**
`fetch_url` can only read public pages. Claude notes this and falls back to training knowledge for that source.

**`ModuleNotFoundError: bs4`**
Run `pip install beautifulsoup4`.

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
