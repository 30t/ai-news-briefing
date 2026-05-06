# AI News Briefing

一个无 API Key 的 AI 新闻规则简报系统。

本项目用于自动采集 AI 相关信息源，并通过可解释的规则流程完成新闻筛选、来源分级、关键词识别、规则打分、去重排序和 Markdown 简报输出。

它不调用大模型 API，不依赖 OpenAI、Anthropic、DeepSeek 或其他模型服务，也不把 AI 总结当作事实来源。它的定位是一个稳定、透明、可检查的新闻筛选底座：先把值得关注的 AI 信息从大量来源中筛出来，再保留原始链接、来源等级、命中关键词和规则分数，方便后续人工阅读、归档或接入更高阶分析流程。

---

## 项目定位

AI 新闻很多，但质量参差不齐。

有些来自官方博客，有些来自技术社区，有些只是营销活动、赞助内容、招聘信息或重复传播。直接让模型总结新闻，很容易把来源可靠性、原文链接和判断依据混在一起，最后看似有结论，实际不好验证。

本项目解决的是前置筛选问题：

- 自动抓取 AI 相关信息
- 区分官方来源、社区讨论、早期信号和待验证信息
- 根据关键词和来源等级进行规则评分
- 降低营销、活动、赞助、招聘等低价值信息的权重
- 对重复链接和相似标题进行去重
- 生成带有判断依据的 Markdown 简报

它不替你下最终结论，而是帮你建立一个可追溯的 AI 新闻入口。

---

## 核心能力

- 多来源新闻抓取
- RSS / Atom 信息解析
- GitHub Releases 抓取
- Hacker News 热点抓取
- 来源等级标注
- 关键词匹配
- 新闻主题标签生成
- 规则打分
- 噪声内容降权
- URL 去重
- 相似标题去重
- Top 新闻排序
- Markdown 简报生成
- 日期归档输出

---

## 系统工作流

```text
读取配置
  ↓
抓取新闻来源
  ↓
标准化新闻结构
  ↓
时间窗口过滤
  ↓
关键词匹配
  ↓
规则打分
  ↓
去重
  ↓
排序
  ↓
生成 Markdown 简报
```

---

## 工作流 1：读取配置

### 作用

加载新闻来源、关键词体系和评分规则。

### 使用文件

| 文件 | 作用 |
|---|---|
| `config/sources.yml` | 定义新闻来源 |
| `config/keywords.yml` | 定义关键词和主题标签 |
| `config/scoring.yml` | 定义时间窗口、评分规则、降权规则和排序参数 |

### 输出

输出后续流程需要使用的配置对象。

---

## 工作流 2：抓取新闻来源

### 作用

从不同渠道抓取 AI 相关新闻、技术博客、论文动态、开源项目更新和社区热点。

### 使用脚本

| 脚本 | 作用 |
|---|---|
| `scripts/fetch_rss.py` | 抓取 RSS / Atom 来源 |
| `scripts/fetch_github_releases.py` | 抓取 GitHub Releases |
| `scripts/fetch_hackernews.py` | 抓取 Hacker News 热门内容 |

### 来源类型

#### RSS / Atom

用于抓取官方博客、技术博客、arXiv 分类源和社区 RSS。

当前包含：

- OpenAI News
- Anthropic News
- Google DeepMind Blog
- Meta AI Blog
- Microsoft AI Blog
- Azure AI Blog
- NVIDIA Blog
- Hugging Face Blog
- GitHub Blog
- GitHub Changelog
- arXiv cs.AI
- arXiv cs.CL
- arXiv cs.LG
- Simon Willison
- Latent Space
- The Batch
- Reddit r/MachineLearning
- Reddit r/LocalLLaMA

#### GitHub Releases

用于追踪重点 AI 开源项目的版本更新。

当前包含：

- llama.cpp
- vLLM
- Transformers
- LangChain
- Ollama
- AutoGen
- Open WebUI

#### Hacker News

用于捕捉技术社区中讨论度较高的 AI 相关内容。

当前判定条件：

```yaml
enabled: true
max_stories: 100
min_points: 20
```

含义：

- 开启 Hacker News 抓取
- 最多读取前 100 条热门内容
- 只保留分数不低于 20 的内容

### 输出

输出原始新闻列表，进入后续标准化流程。

---

## 工作流 3：标准化新闻结构

### 作用

不同来源返回的数据格式并不一致。系统会把 RSS、GitHub Releases 和 Hacker News 的信息整理成统一结构，方便后续过滤、打分和输出。

### 使用脚本

| 脚本 | 作用 |
|---|---|
| `scripts/utils.py` | 构建统一 item、清理 HTML、解析时间、标准化 URL |
| `scripts/fetch_rss.py` | 从 RSS 中提取标题、链接、摘要、时间 |
| `scripts/fetch_github_releases.py` | 从 release 中提取项目名、版本、发布时间和 release 内容 |
| `scripts/fetch_hackernews.py` | 从 HN 中提取标题、链接、分数、评论链接和发布时间 |

### 统一字段

每条新闻会被整理为：

| 字段 | 含义 |
|---|---|
| `title` | 新闻标题 |
| `url` | 原文链接 |
| `source_name` | 来源名称 |
| `source_type` | 来源类型 |
| `source_level` | 来源等级 |
| `published_at` | 发布时间 |
| `summary_or_excerpt` | 摘要或正文片段 |
| `matched_keywords` | 命中的关键词 |
| `tags` | 主题标签 |
| `score` | 规则分数 |

### 输出

输出统一结构的新闻 item 列表。

---

## 工作流 4：时间窗口过滤

### 作用

过滤掉时间过旧的信息，只保留最近一段时间内的新闻。

### 使用脚本

| 脚本 | 作用 |
|---|---|
| `scripts/score_items.py` | 根据时间窗口过滤新闻 |

### 使用配置

```yaml
lookback_hours: 24
```

### 判定条件

只保留最近 24 小时内发布的信息。

如果某条信息没有可靠发布时间，系统会保留它，避免误删潜在有价值内容。

### 输出

输出时间窗口内的新闻列表。

---

## 工作流 5：关键词匹配

### 作用

识别新闻是否命中重点关注方向，并为新闻生成主题标签。

### 使用文件

| 文件 | 作用 |
|---|---|
| `config/keywords.yml` | 定义关键词分类和标签 |

### 当前关注方向

| 分类 | 标签 | 关注内容 |
|---|---|---|
| 模型与 AI 公司 | `model` | OpenAI、GPT、Claude、Gemini、Llama、DeepSeek、Qwen、Kimi 等 |
| Agent 与编程工具 | `agent` | Agent、Codex、Claude Code、GitHub Copilot、Cursor、MCP 等 |
| 开源与工具链 | `open_source` | GitHub、release、benchmark、RAG、embeddings、inference 等 |
| 算力与半导体 | `semiconductor` | NVIDIA、GPU、HBM、TSMC、CUDA、CoWoS、AI chip 等 |
| 商业化与职业影响 | `business` | enterprise AI、automation、pricing、API、startup、partnership 等 |

### 判定条件

系统会在以下文本中查找关键词：

- 标题
- 摘要
- 来源名称

只要命中某一分类下的关键词，就会记录：

- `matched_keywords`
- `tags`

关键词命中只代表“相关”，不代表该内容一定重要，也不代表事实已经被确认。

### 输出

输出带关键词和主题标签的新闻列表。

---

## 工作流 6：规则打分

### 作用

根据来源等级、关键词命中和低价值信号，为每条新闻计算规则分数。

### 使用文件

| 文件 | 作用 |
|---|---|
| `config/scoring.yml` | 定义来源基础分、关键词加分和降权规则 |

### 来源基础分

| 来源等级 | 含义 | 基础分 |
|---|---|---:|
| `official_confirmed` | 官方确认 | 50 |
| `tech_community` | 技术社区 | 25 |
| `early_signal` | 早期信号 | 10 |
| `needs_verification` | 待验证 | 5 |

### 关键词加分

系统会根据不同关键词方向加分。

当前加分方向包括：

| 方向 | 示例 |
|---|---|
| 模型与实验室 | OpenAI、Anthropic、DeepMind、Meta AI、xAI |
| 模型名称 | GPT、Claude、Gemini、Llama、DeepSeek、Qwen、Kimi |
| Agent 与工具 | Agent、Codex、Claude Code、GitHub Copilot、Cursor、MCP |
| 产品信号 | benchmark、release、API、pricing |
| 开源 | GitHub Release、open source |
| 算力与半导体 | GPU、NVIDIA、HBM、TSMC、CoWoS |
| 商业影响 | enterprise AI、automation、productivity |

### 降权规则

低价值或噪声内容会被降权。

| 降权信号 | 含义 |
|---|---|
| `webinar` | 网络研讨会 |
| `event only` | 纯活动信息 |
| `sponsored` | 赞助内容 |
| `marketing` | 营销内容 |
| `hiring only` | 纯招聘信息 |
| `pure funding news` | 单纯融资新闻 |
| `duplicate url` | 重复链接 |

### 输出

输出带规则分数的新闻列表。

---

## 工作流 7：去重

### 作用

减少重复新闻，避免同一事件被多个相似标题或相同链接反复输出。

### 使用脚本

| 脚本 | 作用 |
|---|---|
| `scripts/score_items.py` | URL 去重、标题相似度去重、保留更优内容 |

### 去重规则

#### 1. URL 去重

如果多条新闻的 URL 完全相同，只保留更优的一条。

优先级判断：

1. 来源等级更高
2. 规则分数更高
3. 发布时间更新

#### 2. 标题相似度去重

如果标题高度相似，系统会视为重复内容。

当前阈值：

```yaml
title_similarity_threshold: 0.86
```

含义：

当两条新闻标题相似度达到 0.86 或以上时，系统会认为它们可能是同一事件的重复传播。

### 输出

输出去重后的新闻列表。

---

## 工作流 8：排序与 Top 列表

### 作用

将新闻按优先级排序，并选出当天最值得关注的内容。

### 使用脚本

| 脚本 | 作用 |
|---|---|
| `scripts/score_items.py` | 排序并截取 Top 列表 |

### 使用配置

```yaml
max_items_per_day: 20
```

### 排序依据

排序优先级为：

1. 来源等级
2. 规则分数
3. 发布时间

也就是说，系统会优先保留更可靠、更相关、更新的信息。

### 输出

输出每日 Top 新闻列表。

---

## 工作流 9：生成 Markdown 简报

### 作用

将筛选后的新闻列表生成可阅读、可归档、可继续分析的 Markdown 文件。

### 使用脚本

| 脚本 | 作用 |
|---|---|
| `scripts/generate_markdown.py` | 生成每日 Markdown 简报 |

### 每条新闻包含

| 字段 | 含义 |
|---|---|
| 标题 | 新闻标题 |
| 来源等级 | 官方确认、技术社区、早期信号或待验证 |
| 来源名称 | 具体来源 |
| 来源类型 | RSS、GitHub Releases 或 Hacker News |
| 发布时间 | 新闻发布时间 |
| 原文链接 | 可追溯的原始链接 |
| 命中关键词 | 触发匹配的关键词 |
| 规则分数 | 系统计算出的排序分数 |
| 入选原因 | 为什么进入今日列表 |
| Feed 摘要 | 来源 feed 中提供的摘要 |
| 阅读提醒 | 根据信息来源给出的阅读提示 |

### 输出文件

| 文件 | 作用 |
|---|---|
| `output/daily.md` | 最新一份每日 AI 新闻简报 |
| `output/YYYY-MM-DD.md` | 按日期归档的历史简报 |

---

## 来源等级

### `official_confirmed`

官方确认来源。

通常包括：

- 公司官方博客
- 官方 changelog
- arXiv 分类源
- 开源项目 release 页面

这类内容优先作为事实入口，但仍建议查看原文确认细节。

### `tech_community`

技术社区来源。

通常包括：

- Hacker News
- Reddit
- 技术博客
- 社区讨论

这类内容适合观察趋势和讨论热度，但不等于官方确认。

### `early_signal`

早期信号来源。

用于保留可能有价值但尚未充分确认的信息。

这类内容适合收藏观察，不适合直接作为确定结论。

### `needs_verification`

待验证来源。

用于标记来源不够明确、需要进一步核验的信息。

这类内容必须优先查看原文链接，不应直接作为事实依据。

---

## 设计原则

### 1. 原文优先

每条新闻必须保留原文链接。

系统输出的是信息入口，不是最终结论。

### 2. 来源分级

系统必须区分官方确认、社区讨论、早期信号和待验证信息。

社区热议不能被当成官方确认。

### 3. 规则透明

每条新闻为什么被选中，应该能通过来源等级、关键词、分数和降权规则解释。

### 4. 模型不替代事实来源

即使后续接入大模型总结，也应该先保留原文链接、来源等级和规则分数。

模型可以帮助阅读，但不能替代来源核验。

### 5. 先筛选，再分析

系统先用规则筛出少量高价值候选新闻，再交给人工或模型做进一步解读。

---

## 文件说明

| 文件 | 说明 |
|---|---|
| `README.md` | 项目说明文件 |
| `config/sources.yml` | 新闻来源配置，定义 RSS / Atom、GitHub Releases、Hacker News 等信息来源 |
| `config/keywords.yml` | 关键词与标签配置，定义模型、Agent、开源、半导体、商业化等关注方向 |
| `config/scoring.yml` | 评分、过滤、去重和排序规则配置 |
| `scripts/main.py` | 主流程入口，串联抓取、过滤、关键词匹配、打分、去重、排序和输出 |
| `scripts/fetch_rss.py` | RSS / Atom 抓取脚本 |
| `scripts/fetch_github_releases.py` | GitHub Releases 抓取脚本 |
| `scripts/fetch_hackernews.py` | Hacker News 抓取脚本 |
| `scripts/score_items.py` | 时间过滤、关键词匹配、打分、去重和排序逻辑 |
| `scripts/generate_markdown.py` | Markdown 简报生成逻辑 |
| `scripts/utils.py` | 通用工具函数，包括配置读取、时间解析、HTML 清理、URL 标准化和 item 构建 |
| `output/daily.md` | 最新生成的每日 AI 新闻简报 |
| `output/YYYY-MM-DD.md` | 按日期归档的历史简报文件 |
| `requirements.txt` | 依赖说明；当前无必须第三方依赖 |
| `.gitignore` | Git 忽略规则 |

---

## 输出示例结构

```markdown
# 每日 AI 新闻规则简报｜YYYY-MM-DD

## 今日概况

今天自动抓取若干条信息，按来源等级、关键词、规则分数和去重规则筛出 Top 新闻。

## 判断标签

- 官方确认
- 技术社区
- 早期信号 / 待验证

## 官方确认与项目发布

### 1. 新闻标题

- 来源等级
- 来源名称
- 来源类型
- 发布时间
- 原文链接
- 命中关键词
- 规则分数
- 入选原因
- Feed 摘要
- 阅读提醒
```

---

## 项目边界

本项目当前只做规则层面的新闻筛选和 Markdown 输出。

它不负责：

- 生成模型总结
- 判断新闻最终真伪
- 替代人工阅读原文
- 调用大模型 API
- 生成投资、商业或技术决策结论

它负责：

- 抓取信息
- 标注来源
- 匹配关键词
- 计算规则分数
- 去除重复内容
- 输出可追溯的简报文件

---

## 适合用于

- 每日 AI 新闻收集
- AI 工具链动态追踪
- 开源项目 release 监控
- Agent / 编程工具趋势观察
- 算力与半导体相关新闻筛选
- 后续接入模型总结前的规则筛选层
- 个人知识库或第二大脑的信息入口
