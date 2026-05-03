# Daily AI News Briefing

这是一个每日 AI 新闻简报自动化系统，基于 `Thysrael/Horizon` 的 AI 新闻雷达思路改造。当前阶段聚焦稳定抓取、来源分级、关键词匹配、规则打分、去重和 Markdown 简报生成。

## 当前阶段：No API Key 模式

第一版不会调用 OpenAI、Anthropic、DeepSeek 或任何模型 API，也不需要配置 `OPENAI_API_KEY`。因此当前版本不会产生模型 API 费用。

系统每天会抓取 RSS / Atom、GitHub Releases 和 Hacker News，将新闻统一成标准结构，并生成 `output/daily.md`。

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

推送到 GitHub 后，进入仓库的 Actions 页面，选择 `Daily AI Briefing No API`，点击 `Run workflow` 即可手动测试。

## 修改定时时间

定时任务在 `.github/workflows/daily-briefing.yml` 中配置：

```yaml
schedule:
  - cron: '30 23 * * *'
```

GitHub Actions 使用 UTC 时间。当前配置是 UTC 23:30，对应北京时间 / 新加坡时间次日早上 7:30。

## 查看每日简报

简报输出到 `output/daily.md`。GitHub Actions 每次运行后会自动提交 `output/` 目录变更。

## 后续升级为 API 总结模式

已预留 `scripts/summarize_with_llm.py`，但当前不会被调用。后续接入模型 API 时，建议只对规则筛选后的 Top 10 新闻做总结，并继续保留：

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
