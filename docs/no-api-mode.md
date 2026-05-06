# No API Key 模式说明

`main` 分支固定为 No API Key 模式。

它不调用模型 API，不需要配置 `LLM_API_KEY`、`DEEPSEEK_API_KEY`、`OPENAI_API_KEY` 或其他密钥，也不会产生模型 API 费用。

## 为什么 main 不接 API Key

这个分支的目标是把新闻系统的基础链路跑稳定：

- 来源抓取是否稳定；
- 来源等级是否清楚；
- 关键词匹配是否可解释；
- 规则打分是否可调整；
- 去重是否可靠；
- Markdown 输出是否稳定；
- 每条新闻是否保留原始链接。

如果一开始就接入模型，系统会变得更难判断：到底是来源质量有问题、规则有问题，还是模型总结有问题。

所以 `main` 只保留可解释的规则链路。

## No API Key 模式能做什么

- 抓取 RSS / Atom。
- 抓取 GitHub Releases。
- 抓取 Hacker News。
- 按来源等级给基础分。
- 按关键词加分。
- 按营销、活动、招聘、赞助等噪声信号降权。
- 对 URL 和相似标题去重。
- 生成 `output/daily.md`。
- 生成 `output/YYYY-MM-DD.md` 日期归档。
- 保留每条新闻的来源等级、来源名称、原文链接、发布时间、命中关键词和规则分数。

## No API Key 模式不能做什么

- 不会阅读完整正文。
- 不会生成模型摘要。
- 不会生成中文深度解读。
- 不会判断事实真伪。
- 不会替代人工阅读原文。
- 不会使用 Agent 自动规划或执行任务。

## 来源分级逻辑

- `official_confirmed`：官方确认。公司官方博客、官方 changelog、arXiv 分类源、GitHub Releases。
- `tech_community`：技术社区。Hacker News、Reddit、技术博客。
- `early_signal`：早期信号。第一版预留，不默认抓取 X / Telegram。
- `needs_verification`：待验证。来源不够明确或需要进一步核验。

## 规则打分逻辑

系统先按来源等级给基础分：

- 官方确认：+50
- 技术社区：+25
- 早期信号：+10
- 待验证：+5

然后按关键词组加分。

例如 Agent、Codex、GitHub Copilot、Cursor、MCP 会提高编程工具与自动化相关新闻优先级；NVIDIA、GPU、HBM、TSMC、CUDA、CoWoS 会提高算力和半导体相关新闻优先级。

低价值内容会降权，例如 webinar、event only、sponsored、marketing、hiring only、pure funding news。

## 为什么必须保留原文链接

自动化系统只能帮助发现信息和排序，不能替代事实核验。

保留原文链接可以让读者回到第一来源，确认发布时间、上下文、发布方身份和原始措辞。

尤其是技术社区和早期信号，它们只能用于发现趋势，不能直接作为事实结论。

## 后续模型能力放在哪里

模型总结、人话解读、业务启发、语音友好日报等能力不放在 `main`。

这些能力放在独立分支，例如：

- `feature/practical-ai-toolchain-daily`

这样 `main` 始终保持为可解释、低成本、稳定的规则基础框架。
