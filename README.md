# AI 新闻规则简报基座

这个仓库的 `main` 分支是每日 AI 新闻简报系统的**纯规则基础框架**。

它只做稳定的信息抓取、来源分级、关键词匹配、规则打分、去重和 Markdown 输出。`main` 不调用任何模型 API，不需要 OpenAI、Anthropic、DeepSeek 或其他 API Key，也不使用 Agent 执行框架。

模型总结、深度解读、人话日报和更重的 AI 分析能力放在独立分支中演进，不放在 `main`。

## 工作链路

系统每天按固定流程运行：

1. 抓取来源

   从 `config/sources.yml` 中读取来源配置，抓取 RSS / Atom、GitHub Releases 和 Hacker News。

2. 标准化新闻

   每条信息会被整理成统一结构，包括标题、原始链接、来源名称、来源类型、来源等级、发布时间和 feed 摘要。

3. 时间过滤

   根据 `config/scoring.yml` 中的 `lookback_hours`，只保留最近一段时间内的信息。

4. 关键词匹配

   根据 `config/keywords.yml` 命中关键词，并写入 `matched_keywords` 和 `tags`。

5. 规则打分

   根据来源等级给基础分，再根据关键词加分，根据营销、招聘、赞助、活动等低价值信号降权。

6. 去重

   URL 完全相同的内容只保留一条；标题高度相似时，优先保留来源等级更高、规则分更高、发布时间更新的内容。

7. 排序输出

   按来源优先级、规则分数和发布时间排序，默认输出 Top 20 到 `output/daily.md`，同时生成日期归档文件 `output/YYYY-MM-DD.md`。

## 判断依据

这个系统的判断不来自模型，而来自三类规则。

### 1. 来源可靠性

来源等级决定基础可信度。

- `official_confirmed`：官方确认。公司官方博客、官方 changelog、arXiv 分类源、开源项目 release。
- `tech_community`：技术社区。Hacker News、Reddit、技术博客，用于发现讨论热度。
- `early_signal`：早期信号。速度快但噪声高，第一版只预留等级。
- `needs_verification`：待验证。来源不够明确或需要进一步核验。

输出时必须保留来源等级和原始链接。系统不把社区讨论当成官方确认。

### 2. 关键词重要性

关键词配置在 `config/keywords.yml`。

当前重点关注：

- 模型与大厂：OpenAI、Claude、Gemini、Llama、DeepSeek、Qwen 等。
- Agent / 编程工具：Agent、Codex、Claude Code、GitHub Copilot、Cursor、MCP 等。
- 开源与工具链：GitHub、release、RAG、embeddings、inference 等。
- 算力与半导体：NVIDIA、GPU、HBM、TSMC、CUDA、CoWoS 等。
- 商业化与效率：enterprise AI、automation、productivity、API、pricing 等。

关键词只影响排序，不代表事实已经成立。

### 3. 降权规则

低价值或噪声内容会被降权。

常见降权信号包括：

- webinar
- event only
- sponsored
- marketing
- hiring only
- pure funding news
- duplicate url

降权不是删除。它只是让这类内容更难进入 Top 20。

## 输出文件

规则简报输出到：

- `output/daily.md`：最新一份。
- `output/YYYY-MM-DD.md`：日期归档。

每条新闻都会保留：

- 标题
- 来源等级
- 来源名称
- 来源类型
- 发布时间
- 原文链接
- 命中关键词
- 规则分数
- feed 摘要
- 阅读提醒

## 分支定位

- `main`：纯规则基础框架，不调用模型 API，不做 Agent。
- `feature/practical-ai-toolchain-daily`：实用 AI 工具链日报分支，可继续加入模型总结、人话解读和更重的 AI 分析。

已冻结的情报中心实验分支已删除，避免分支含义混乱。需要追溯时，可以查看保留的冻结 tag。

## 本地运行

```bash
python scripts/main.py
```

运行后查看：

```bash
open output/daily.md
```

## GitHub Actions

定时任务使用北京时间 / 新加坡时间每天早上 7:30。

GitHub Actions cron 使用 UTC：

```yaml
cron: '30 23 * * *'
```

`workflow_dispatch` 会保留，方便手动测试。

## 设计原则

这个基础框架只负责发现和排序，不负责替你下最终结论。

系统必须保留原文链接，必须标注来源等级，必须区分官方确认、技术社区、早期信号和待验证内容。

后续即使在其他分支接入模型，也应该先由规则筛选候选新闻，再让模型处理少量高价值内容。模型输出不能替代来源分级、规则分数和原文链接。
