# Daily AI News Briefing

这是一个每日 AI 新闻简报自动化系统，基于 `Thysrael/Horizon` 的 AI 新闻雷达思路改造。当前阶段聚焦稳定抓取、来源分级、关键词匹配、规则打分、去重和 Markdown 简报生成。

## 当前阶段：规则抓取 + 可选 LLM 增强

系统默认仍可以在没有任何模型 API Key 的情况下运行：如果没有配置 `LLM_API_KEY` 或 `DEEPSEEK_API_KEY`，程序会自动使用规则版标题、摘录和中文大意，不会产生模型 API 费用。

如果配置 DeepSeek API Key，系统会只对规则筛选后的 Top 20 新闻调用模型。进入模型前，系统会尽量抓取原文正文片段；模型直接生成中文标题、核心总结和“为什么重要”。原始标题、来源等级、发布时间、规则分数和原文链接仍会保留。

系统每天会抓取 RSS / Atom、GitHub Releases 和 Hacker News，将新闻统一成标准结构，并生成 `output/daily.md`。

## DeepSeek 成本预估

第一版 LLM 增强默认使用 DeepSeek `deepseek-v4-flash`。按 DeepSeek 官方 API 价格：

- 输入 cache hit：`$0.07 / 100万 tokens`
- 输入 cache miss：`$0.27 / 100万 tokens`
- 输出：`$1.10 / 100万 tokens`

官方价格页：<https://api-docs.deepseek.com/quick_start/pricing-details-usd>

本项目每天只处理 Top 20 条新闻，预计每天成本约 `$0.01 - $0.03`，每月约 `$0.3 - $1`，折合人民币大约 `2 - 8 元`。实际费用取决于原文正文片段长度、输出长度、缓存命中和服务商最新价格。

成本控制策略：

- 只对 Top 20 新闻调用模型，不总结全部抓取结果。
- 每条新闻限制正文片段长度、输入摘要长度和模型输出长度。
- API 调用失败时自动回退规则版。
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

- `enabled`：是否启用模型增强。即使为 `true`，没有 API Key 时也会自动回退规则版。
- `provider`：默认 `deepseek`。
- `model`：默认 `deepseek-v4-flash`。
- `base_url`：默认 `https://api.deepseek.com`。
- `api_key_env`：默认从 `LLM_API_KEY` 读取。
- `fallback_api_key_env`：默认也支持 `DEEPSEEK_API_KEY`。
- `max_items_for_llm`：每天最多让模型处理多少条，默认 20。
- `fetch_article_text`：进入模型前是否尝试抓取原文正文片段，默认开启。
- `article_text_limit`：每条新闻最多送入模型的正文片段长度，默认 5000 字符。

本地测试可以这样设置：

```bash
export LLM_API_KEY="你的 DeepSeek API Key"
python scripts/main.py
```

不设置 `LLM_API_KEY` 时，程序仍然可以运行，只是不做模型增强。

## 本地运行

```bash
pip install -r requirements.txt
python scripts/main.py
```

运行后查看：

```bash
open output/daily.md
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

简报输出到 `output/daily.md`。GitHub Actions 每次运行后会自动提交 `output/` 目录变更。

## 后续升级方向

当前已经支持可选 LLM 增强。Top 20 仍由规则分数决定：来源等级基础分 + 关键词加分 + 降权规则 + 去重。后续如果希望模型参与选择，可以升级为“规则 Top 40 → 抓正文 → 模型重排 Top 20”。

后续如果要升级为更深度的 API 总结模式，建议仍然只对规则筛选后的 Top 10 或 Top 20 新闻做总结，并继续保留：

- 原始链接
- 来源等级
- 命中关键词
- 规则分数
- 官方 / 社区 / 早期信号判断

建议新增的总结字段：

- 核心结论
- 为什么重要
- 对 AI 行业的影响
- 对半导体 / 算力 / 职业选择 / 创业机会的启发

也可以继续扩展 Notion、Obsidian、飞书或邮件输出。

模型选择和成本说明见 `docs/model-selection.md`。
