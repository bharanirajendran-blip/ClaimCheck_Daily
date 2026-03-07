# ClaimCheck Daily — Setup & Usage Guide

## API Keys Required

You need two API keys to run this project:

| Key Name | Where to Get It | Where to Put It |
|---|---|---|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com → API Keys | `.env` file |
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys | `.env` file |

---

## Step-by-Step Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` in any text editor and fill in your keys:

```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Save the file. It stays on your machine and is never uploaded to GitHub.

### 3. Run a dry run first (no API cost for Claude)

```bash
python run.py --dry-run
```

This parses all feeds, harvests claim candidates, and asks GPT to select the top 3 — but skips the Claude research step. Good for checking everything is wired up correctly.

### 4. Run the full pipeline

```bash
python run.py
```

This runs the complete pipeline:
1. Parses 7 RSS feeds → ~40 candidate claims
2. GPT-4o selects the 3 best claims (diverse sources and topics)
3. Claude researches each claim sequentially, fetching live articles
4. GPT-4o synthesises a verdict for each
5. Publishes `docs/YYYY-MM-DD.html` and `outputs/YYYY-MM-DD.json`

---

## Optional Flags

```bash
# Use a different feeds file
python run.py --feeds my_feeds.yaml

# Change output directories
python run.py --docs-dir public --outputs-dir results

# Verbose logging
python run.py --log-level DEBUG

# Dry run (skip Claude research)
python run.py --dry-run

# Control Claude workers (default: 1, sequential to stay within rate limits)
python run.py --workers 2
```

---

## Output Files

After a successful run you will find:

| File | Description |
|---|---|
| `docs/YYYY-MM-DD.html` | Dark-themed report page, viewable in any browser |
| `docs/index.html` | Landing page with links to all past reports |
| `outputs/YYYY-MM-DD.json` | Machine-readable verdicts in JSON format |

Open the HTML file directly in your browser:

```bash
open docs/2026-03-02.html        # macOS
start docs/2026-03-02.html       # Windows
xdg-open docs/2026-03-02.html    # Linux
```

---

## Environment Variables Reference

All variables go in your `.env` file. Only the first two are required.

```
# Required
ANTHROPIC_API_KEY=sk-ant-...      # Claude Researcher
OPENAI_API_KEY=sk-...             # GPT Director

# Optional overrides
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929   # use Sonnet for lower cost
OPENAI_MODEL=gpt-4o
LOG_LEVEL=INFO                    # DEBUG | INFO | WARNING | ERROR
MAX_CLAIMS_PER_DAY=3
RESEARCH_WORKERS=1
USE_EXTENDED_THINKING=true
```

---

## Troubleshooting

**`max_tokens must be greater than thinking.budget_tokens`**
This is fixed in the current version. If you see it, make sure you have the latest `researcher.py` (`max_tokens=10000`, `thinking_budget=3000`).

**`Repository not found` when pushing to GitHub**
Create the repo on github.com first (empty, no README), then push.

**`src refspec main does not match any`**
You have no commits yet. Run `git add . && git commit -m "initial"` first.
Or your branch is named `master` — use `git branch -m master main` to rename it.

**Paywalled articles come back with login page content**
The `fetch_url` tool can only read publicly accessible pages. Paywalled sources (NYT, WSJ, etc.) will return a login wall. Claude will note this and fall back to training knowledge for those specific sources.

**`ModuleNotFoundError: bs4`**
Run `pip install beautifulsoup4` — required for the fetch_url web tool.
