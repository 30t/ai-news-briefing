"""
Reserved extension point for future API-based summaries.

The current No API Key version must not call OpenAI, Anthropic, DeepSeek, or
any other model API. A later phase can add a function here that summarizes only
the Top 10 ranked items and keeps original links, source levels, and rule scores.
"""


def summarize_top_items(*args, **kwargs):
    raise NotImplementedError("LLM summarization is intentionally disabled in No API Key mode.")
