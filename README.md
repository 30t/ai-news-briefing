# Daily AI News Briefing

这是一个每日 AI 情报中心自动化系统，基于 `Thysrael/Horizon` 的 AI 新闻雷达思路改造。当前阶段聚焦稳定抓取、来源分级、关键词匹配、规则打分、7 天历史去重，以及适合阅读和语音朗读的 Markdown 情报稿生成。

## 当前阶段：规则抓取 + 必需 LLM 整稿

本分支必须配置 DeepSeek API Key。如果没有 `LLM_API_KEY` 或 `DEEPSEEK_API_KEY`，程序会直接失败，不生成低质量规则回退稿。

系统会先抓取 RSS / Atom、GitHub Releases 和 Hacker News，再按规则打分、去重、取更大的候选池，过滤过去 7 天已经进入早报的重复新闻。最后把当天最多 20 条新闻交给 DeepSeek 生成完整的“每日 AI 情报中心”。

每天会生成两个内容一致的文件：

- `output/daily.md`：最新入口。
- `output/YYYY-MM-DD.md`：每日归档。

系统还会维护 `output/history.json`，用于 7 天跨天去重。

## DeepSeek 成本预估

本分支默认使用 DeepSeek `deepseek-v4-flash`。按 DeepSeek 官方 API 价格：

- 输入 cache hit：`$0.07 / 100万 tokens`
- 输入 cache miss：`$0.27 / 100万 tokens`
- 输出：`$1.10 / 100万 tokens`

官方价格页：<https://api-docs.deepseek.com/quick_start/pricing-details-usd>

本项目每天最多处理 20 条新闻，并会额外做整稿生成。预计成本仍然较低，但实际费用取决于正文片段长度、输出长度、缓存命中和服务商最新价格。

成本控制策略：

- 只对历史去重后的最多 20 条新闻做模型处理，不总结全部抓取结果。
- 每条新闻限制正文片段长度、输入摘要长度和模型输出长度。
- API Key 缺失或整稿调用失败时直接失败，不生成规则回退稿。
- 第一版使用 `deepseek-v4-flash`，暂不使用更贵的 `deepseek-v4-pro` 或 `deepseek-reasoner`。
- API Key 只放在 GitHub Secrets 或本地环境变量，不写入代码。

## 配置新闻来源

编辑 `config/sources.yml`。当前文件使用 YAML 兼容的 JSON 写法，因此即使没有安装 PyYAML 也能运行；如果安装了 PyYAML，也可以改成普通 YAML。

- `rss_sources`：配置 RSS / Atom 来源。
- `github_releases`：配置重要开源项目的 GitHub 仓库。
- `hackernews`：配置 Hacker News 抓取开关、最大抓取数量和最低分数。

来源等级可选：

- `official_confirmed`：官方确认
- `tech_community`：技术社区
- `early_signal`：早期信号
- `needs_verification`：待验证

## 配置关键词

编辑 `config/keywords.yml`。当前文件同样使用 YAML 兼容的 JSON 写法。

关键词按类别组织，例如模型与大厂、Agent / 编程工具、开源项目、半导体与算力、商业化与职业启发。命中的关键词会写入每条新闻的 `matched_keywords`，类别会写入 `tags`。

## 调整打分规则

编辑 `config/scoring.yml`。当前文件同样使用 YAML 兼容的 JSON 写法。

- `max_items_per_day`：每天最多输出多少条，默认 20。
- `lookback_hours`：只保留最近多少小时的内容，默认 24。
- `source_level_scores`：不同来源等级的基础分。
- `keyword_scores`：命中特定关键词组的加分。
- `penalties`：webinar、sponsored、marketing 等低价值内容的降权。

## 配置 LLM 增强

编辑 `config/llm.yml`。

- `require_llm`：是否强制要求模型 API Key，当前为 `true`。
- `provider`：默认 `deepseek`。
- `model`：默认 `deepseek-v4-flash`。
- `base_url`：默认 `https://api.deepseek.com`。
- `api_key_env`：默认从 `LLM_API_KEY` 读取。
- `fallback_api_key_env`：默认也支持 `DEEPSEEK_API_KEY`。
- `max_items_for_llm`：每天最多让模型处理多少条，默认 20。
- `candidate_pool_size`：规则排序后先取多少条进入历史去重候选池，默认 60。
- `history_dedupe_days`：跨天历史去重窗口，默认 7 天。
- `must_listen_min` / `must_listen_max`：今日必听新闻数量范围。
- `fetch_article_text`：进入模型前是否尝试抓取原文正文片段，默认开启。
- `article_text_limit`：每条新闻最多送入模型的正文片段长度，默认 5000 字符。

本地测试可以这样设置：

```bash
export LLM_API_KEY="你的 DeepSeek API Key"
python scripts/main.py
```

不设置 `LLM_API_KEY` 或 `DEEPSEEK_API_KEY` 时，程序会直接失败。

## 本地运行

```bash
pip install -r requirements.txt
python scripts/main.py
```

运行后查看：

```bash
open output/daily.md
```

历史归档文件会按日期保存，例如：

```bash
open output/2026-05-03.md
```

## GitHub Actions 手动运行

推送到 GitHub 后，进入仓库的 Actions 页面，选择 `Daily AI Briefing`，点击 `Run workflow` 即可手动测试。

如果要在 GitHub Actions 中启用 DeepSeek 增强，请在仓库设置里添加 Secret：

- `LLM_API_KEY`：推荐统一使用这个名字。
- `DEEPSEEK_API_KEY`：也支持这个名字，作为备用。

## 修改定时时间

定时任务在 `.github/workflows/daily-briefing.yml` 中配置：

```yaml
schedule:
  - cron: '30 23 * * *'
```

GitHub Actions 使用 UTC 时间。当前配置是 UTC 23:30，对应北京时间 / 新加坡时间次日早上 7:30。

## 查看每日简报

简报会输出到当天日期文件，例如 `output/2026-05-03.md`；同时 `output/daily.md` 会保持为最新一份。GitHub Actions 每次运行后会自动提交 `output/` 目录变更，包括 `output/history.json`。

## 后续升级方向

## 输出结构

`output/daily.md` 是“每日 AI 情报中心”，固定包含：

- 今日一句话
- 今日三条主线
- 今日必听新闻
- 今日一句话带过
- 今日风险提醒
- 今日行动建议

输出不再包含冗长原文摘录，也不再包含“中文翻译 / 大意（规则版）”。社区来源会明确标注“社区讨论，不等于官方确认”。

后续可以继续扩展 Notion、Obsidian、飞书或邮件输出。

模型选择和成本说明见 `docs/model-selection.md`。
