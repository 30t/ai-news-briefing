# 规则候选层与模型解读层

当前 `main` 已经合并为一条完整日报流程，但仍保留两层边界：

- `output/sources/latest.md` 和 `output/sources/YYYY-MM-DD.md`：规则候选层。
- `output/model/latest.md` 和 `output/model/YYYY-MM-DD.md`：模型解读层。

这两个文件承担不同职责，不能混在一起理解。

## 规则候选层做什么

规则候选层不调用模型，只负责把新闻候选池整理清楚：

- 抓取 RSS / Atom。
- 抓取 GitHub Releases。
- 抓取 Hacker News。
- 按来源等级给基础分。
- 按关键词加分。
- 按营销、活动、招聘、赞助等噪声信号降权。
- 对 URL 和相似标题去重。
- 生成 `output/sources/latest.md`。
- 生成 `output/sources/YYYY-MM-DD.md` 日期归档。

每条新闻必须保留：

- 来源等级
- 来源名称
- 原文链接
- 发布时间
- 命中关键词
- 规则分数

## 模型解读层做什么

模型解读层只在规则候选池之后运行。

它读取规则筛出的候选新闻，抓取必要正文片段，然后生成：

- `output/model/latest.md`
- `output/model/YYYY-MM-DD.md`

模型层可以做人话解读、主题归纳、业务启发和行动建议，但不能替代：

- 来源分级
- 规则打分
- 原文链接
- 人工事实核验

如果缺少 `LLM_API_KEY` 或 `DEEPSEEK_API_KEY`，系统不会伪造模型日报，而是直接失败。

## 来源分级逻辑

- `official_confirmed`：官方确认。公司官方博客、官方 changelog、arXiv 分类源、GitHub Releases。
- `tech_community`：技术社区。Hacker News、Reddit、技术博客。
- `early_signal`：早期信号。速度快但噪声高。
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

## 当前 workflow

- `Generate Daily AI News Briefing`：完整流程，每天北京时间 / 新加坡时间 07:30 自动运行，也可以手动运行。
- `Refresh Model AI News Briefing`：只手动运行，只基于现有 `output/sources/latest.md` 重新生成 `output/model/latest.md` 和当天归档文件。
