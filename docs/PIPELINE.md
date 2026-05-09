# AI Intelligence Briefing Pipeline

This project is no longer a rule-only or no-API-key news crawler.

It is a personal AI intelligence pipeline. The system uses deterministic rules for recall and traceability, then uses an LLM editorial judge to decide which items are truly worth reading, and finally uses an LLM synthesis step to generate the daily briefing.

## Current pipeline

```text
1. Load configuration
   ↓
2. Fetch sources
   ↓
3. Normalize items
   ↓
4. Time-window filter
   ↓
5. Rule-based recall scoring
   ↓
6. Deduplicate by URL and title similarity
   ↓
7. Select rule candidate pool
   ↓
8. LLM editorial review
   ↓
9. Rank by editorial score
   ↓
10. Write daily candidate pool
   ↓
11. Merge backlog
   ↓
12. Select model-daily items
   ↓
13. Optionally enrich article text
   ↓
14. Generate model daily synthesis
```

## Stage ownership

| Stage | Owner | Purpose | Output |
|---|---|---|---|
| Source fetch | Rules | Collect RSS, GitHub Releases and Hacker News items | Raw item list |
| Normalization | Rules | Convert all sources to one item structure | Standard item list |
| Time filter | Rules | Keep recent items only | Recent items |
| Keyword matching | Rules | Recall possibly relevant items | `matched_keywords`, `tags` |
| Source scoring | Rules | Provide trust baseline | `source_trust_score` |
| Keyword scoring | Rules | Provide recall strength only | `keyword_relevance_score` |
| Rule candidate ranking | Rules | Choose a limited pool for LLM review | Top candidate pool |
| Editorial review | LLM | Judge value, relevance, actionability and confidence | `editorial`, `editorial_score`, reusable `llm` fields |
| Final ranking | Rules over LLM output | Sort by editorial score | Top daily items |
| Daily candidate pool | Markdown generator | Show traceable ranking and judge reasons | `output/daily.md`, `output/YYYY-MM-DD.md` |
| Model daily synthesis | LLM | Organize selected items into a readable daily briefing | `output/model-daily.md` |

## Key design rules

### Keywords are recall signals, not value signals

A keyword match only means an item may be relevant. It does not mean the item is important.

For example, an item that mentions `DeepSeek`, `release`, `funding`, and `API` may still be a rumor or low-confidence community discussion. It should be reviewed by the LLM judge before being ranked highly.

### Source level is a trust baseline, not automatic importance

Official sources are more reliable, but not every official item is important. A small patch release, dependency bump, webinar, or marketing post can still be low value.

### The LLM editorial judge is the main ranking layer

The LLM judge evaluates:

- newsworthiness
- personal relevance
- actionability
- confidence
- content type
- risk level
- include / maybe / exclude decision
- short Chinese reason

It also generates reusable single-item explanation fields:

- `final_title_zh`
- `background_zh`
- `core_summary_zh`
- `evidence_or_result_zh`
- `why_it_matters_zh`
- `reader_action_zh`

These fields are stored in `item["llm"]` and reused by the model daily synthesis step. This avoids calling another per-item summarization model step.

### No API key means no daily briefing

The project now requires an LLM API key. If neither `LLM_API_KEY` nor `DEEPSEEK_API_KEY` exists, the run fails.

There is no rule-only fallback daily briefing.

## Main files

| File | Role |
|---|---|
| `scripts/main.py` | Orchestrates the end-to-end pipeline |
| `scripts/score_items.py` | Keyword matching, source trust score, rule recall score, deduplication and ranking helper |
| `scripts/judge_candidates_with_llm.py` | LLM editorial review and reusable single-item explanation generation |
| `scripts/generate_markdown.py` | Writes traceable daily candidate pool with editorial scores and reasons |
| `scripts/generate_model_daily.py` | Generates the final model-synthesized daily briefing |
| `scripts/fetch_article_text.py` | Optional article text enrichment before final synthesis |
| `config/sources.yml` | Source list |
| `config/keywords.yml` | Keyword and tag definitions |
| `config/scoring.yml` | Source trust scores, recall scoring and noise penalties |
| `config/llm.yml` | LLM provider, API key env names and pipeline limits |
| `config/editorial_policy.yml` | Editorial policy used by the LLM judge |

## Deprecated mental model

The old mental model was:

```text
source score + keyword score + penalty = final ranking
```

That is no longer the correct interpretation.

The current mental model is:

```text
rules find candidates
LLM judges value
rules sort and preserve traceability
LLM synthesizes the final daily briefing
```

## Current model-call structure

There are now two LLM stages:

```text
1. Per-item editorial review
2. Whole-briefing synthesis
```

The old extra per-item summarization stage is no longer called by `main.py`.

## Failure behavior

The workflow should fail when:

- `config/llm.yml` is missing
- `config/editorial_policy.yml` is missing
- `LLM_API_KEY` and `DEEPSEEK_API_KEY` are both missing
- the editorial judge repeatedly fails
- final model daily generation fails

The system should not silently generate a rule-only substitute.
