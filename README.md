# AI News Briefing｜规则召回 + 模型编辑评审 + 模型解读框架

一个面向 AI / Agent / 工具链 / 算力半导体 / 端侧智能动态追踪的每日情报简报系统。

本项目不是简单新闻爬虫，也不是让模型直接总结互联网新闻。它采用两段式架构：第一段是规则采集与候选召回，负责抓取、标准化、时间过滤、关键词召回、来源可信分、噪声降权和去重；第二段是模型编辑评审与日报综合，负责判断候选信息是否真正值得阅读，并生成中文解读日报。

当前版本已经不再是 No API Key 项目。模型层是必需组件。如果没有 `LLM_API_KEY` 或 `DEEPSEEK_API_KEY`，系统会直接失败，不生成规则兜底日报。

---

## 项目定位

AI 新闻每天很多，但直接阅读会遇到几个问题：

- 来源混杂：官方博客、社区讨论、论文、媒体报道、营销内容混在一起。
- 信息重复：同一事件可能被多个渠道重复传播。
- 价值不均：重大产品发布、小版本更新、活动、招聘、赞助、低密度汇总混在一起。
- 关键词误导：标题或摘要命中很多关键词，只能说明“可能相关”，不能说明“重要”。
- 模型总结容易失真：如果直接把抓到的内容丢给模型，容易丢失原文链接、来源等级和判断依据。

本项目解决的是“先召回，再评审，再解读”的问题：

- 第一段先用规则系统建立可信、透明、可检查的 AI 情报候选池。
- 第二段再用模型编辑层逐条判断哪些信息值得进入日报。
- 最后把已评审候选池交给模型做结构化中文解读。
- 所有模型输出都必须回到原始链接、来源等级、编辑分和判断理由。

完整结构说明见：`docs/PIPELINE.md`。

---

## 核心能力

- 多来源 AI / Agent / 工具链 / 半导体 / 端侧智能信息抓取
- RSS / Atom 信息解析
- GitHub Releases 抓取
- Hacker News AI 主题粗过滤
- 统一新闻 item 结构
- 来源等级标注
- 关键词匹配与主题标签生成
- 规则召回分、来源可信分、关键词召回分生成
- 低价值内容降权
- URL 去重与相似标题去重
- LLM 编辑评审
- 新闻价值、个人相关性、可行动性、判断信心评分
- 内容类型与风险等级标注
- 模型入选理由生成
- 单条新闻中文标题、背景、摘要、重要性和建议动作生成
- 每日 AI 情报候选池 Markdown 输出
- 可选原文正文片段抓取
- 模型版中文解读日报生成
- 日期归档输出
- 无 API Key 直接失败，不生成规则兜底日报

---

## 系统总工作流

```text
第一段：规则采集与候选召回
  ↓
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
规则召回打分
  ↓
去重
  ↓
选择规则候选池

第二段：模型编辑评审与日报综合
  ↓
检查模型 API Key
  ├─ 无 API Key / 模型配置缺失 → 直接失败，不生成日报
  ↓
读取编辑政策
  ↓
模型编辑评审
  ↓
按模型编辑分排序
  ↓
生成每日 AI 情报候选池 Markdown
  ↓
选择模型日报候选池
  ↓
可选抓取原文正文片段
  ↓
生成模型解读日报
  ├─ 成功 → 输出 output/model/YYYY-MM-DD.md 和 output/model/latest.md
  └─ 失败 → 直接失败，不生成规则兜底日报
```

---

## 工作流 1：读取配置

### 作用

加载新闻来源、关键词体系、规则召回配置、模型配置和编辑政策。

### 使用文件

| 文件 | 作用 |
|---|---|
| `config/sources.yml` | 定义 RSS、GitHub Releases、Hacker News 等新闻来源 |
| `config/keywords.yml` | 定义关键词分类和主题标签 |
| `config/scoring.yml` | 定义时间窗口、来源可信分、召回规则、降权规则、去重阈值和输出数量 |
| `config/llm.yml` | 定义模型提供方、API Key 环境变量、编辑评审数量、模型日报参数和正文抓取策略 |
| `config/editorial_policy.yml` | 定义模型编辑评审规则、个人关注方向、高低分标准和评分校准规则 |

### 判定条件

- 第一段规则采集与候选召回需要读取 `sources.yml`、`keywords.yml`、`scoring.yml`。
- 第二段模型编辑评审与日报综合需要读取 `llm.yml` 和 `editorial_policy.yml`。
- 如果 `config/llm.yml` 不存在，系统直接失败。
- 如果 `config/editorial_policy.yml` 不存在，系统直接失败。
- 如果 `config/llm.yml` 中 `enabled` 为 `false`，系统直接失败。
- 如果未读取到 `LLM_API_KEY` 或 `DEEPSEEK_API_KEY`，系统直接失败。
- 当前版本不生成无模型的规则兜底日报。

### 输出

输出后续流程使用的配置对象。

---

## 工作流 2：抓取新闻来源

### 作用

从不同渠道抓取 AI 相关新闻、技术博客、论文动态、开源项目更新、社区热点、算力半导体和端侧智能相关信息。

### 使用脚本

| 脚本 | 作用 |
|---|---|
| `scripts/fetch_rss.py` | 抓取 RSS / Atom 来源 |
| `scripts/fetch_github_releases.py` | 抓取 GitHub Releases |
| `scripts/fetch_hackernews.py` | 抓取 Hacker News 热门内容，并进行 AI 主题粗过滤 |

### 来源类型

#### RSS / Atom

用于抓取官方博客、技术博客、arXiv 分类源、社区 RSS、AI 媒体源、RISC-V / 嵌入式 / Edge AI 相关来源。

#### GitHub Releases

用于追踪重点 AI 开源项目、Agent 工具、AI 应用平台、RAG / 数据栈、开发工具、RISC-V / RTOS / Edge AI 工具链的版本更新。

#### Hacker News

用于捕捉技术社区中讨论度较高的 AI 相关内容。

当前判定条件：

```yaml
enabled: true
max_stories: 100
min_points: 30
```

### 输出

输出原始新闻列表，进入标准化流程。

---

## 工作流 3：标准化新闻结构

### 作用

不同来源返回的数据格式不一致。系统会把 RSS、GitHub Releases 和 Hacker News 的信息整理成统一结构，方便后续过滤、召回、去重、模型编辑评审和输出。

### 使用脚本

| 脚本 | 作用 |
|---|---|
| `scripts/utils.py` | 构建统一 item、清理 HTML、解析时间、标准化 URL、固定 UTC+8 时间显示 |
| `scripts/fetch_rss.py` | 从 RSS 中提取标题、链接、摘要、发布时间 |
| `scripts/fetch_github_releases.py` | 从 Release 中提取项目名、版本、发布时间和发布内容 |
| `scripts/fetch_hackernews.py` | 从 HN 中提取标题、链接、分数、评论链接和发布时间 |

### 统一字段

核心字段包括：`title`、`url`、`source_name`、`source_type`、`source_level`、`published_at`、`summary_or_excerpt`、`matched_keywords`、`tags`、`source_trust_score`、`keyword_relevance_score`、`rule_relevance_score`、`editorial`、`editorial_score`、`llm` 等。

### 输出

输出统一结构的信息 item 列表。

---

## 工作流 4：时间窗口过滤

### 作用

过滤掉时间过旧的信息，只保留最近一段时间内的候选内容。

### 使用脚本

| 脚本 | 作用 |
|---|---|
| `scripts/score_items.py` | 根据时间窗口过滤新闻 |

### 使用配置

```yaml
lookback_hours: 36
```

### 判定条件

- 只保留最近 36 小时内发布的信息。
- 如果某条信息没有可靠发布时间，系统会保留它，避免误删潜在有价值内容。

### 输出

输出时间窗口内的信息列表。

---

## 工作流 5：关键词匹配

### 作用

识别信息是否命中重点关注方向，并为信息生成主题标签。

### 使用文件

| 文件 | 作用 |
|---|---|
| `config/keywords.yml` | 定义关键词分类和标签 |

### 当前关注方向

包括模型与 AI 公司、Agent 与工作流、编程工具、AI 应用平台、RAG 与数据栈、开源基础设施、算力与半导体、RISC-V / OS / 端侧芯片、嵌入式 AI / Edge AI、商业产品与政策等。

### 判定条件

系统会在标题、摘要、来源名称中查找关键词。关键词命中只代表“可能相关”，不代表内容重要，也不代表事实已经被确认。

### 输出

输出带关键词和主题标签的信息列表。

---

## 工作流 6：规则召回打分

### 作用

根据来源等级、关键词命中和低价值信号，为每条信息生成规则召回分。规则分数只用于选择进入模型评审的候选池，不再作为最终新闻价值判断。

### 使用文件

| 文件 | 作用 |
|---|---|
| `config/scoring.yml` | 定义来源可信分、关键词召回分、降权规则、去重阈值和输出数量 |

### 来源可信分

来源等级提供可信度底座，但不代表内容自动重要。当前来源分以 `config/scoring.yml` 为准。

### 关键词召回分

关键词分只表示“与关注方向的相关程度”，不表示新闻价值。

### 降权规则

低价值或噪声内容会被降权，例如活动、营销、赞助、招聘、低密度汇总、传言、促销、重复链接等。

### 输出

输出带 `source_trust_score`、`keyword_relevance_score`、`rule_penalty`、`rule_relevance_score` 的候选列表。

---

## 工作流 7：去重

### 作用

减少重复内容，避免同一事件被多个相似标题或相同链接反复输出。

### 使用脚本

| 脚本 | 作用 |
|---|---|
| `scripts/score_items.py` | URL 去重、标题相似度去重、保留更优内容 |

### 去重规则

- URL 完全相同：只保留更优的一条。
- 标题相似度达到阈值：视为可能重复。
- 当前阈值：`title_similarity_threshold: 0.86`。

### 输出

输出去重后的候选列表。

---

## 工作流 8：排序与 Top 候选池

### 作用

作为第一段的收口：先用规则召回分从大量信息中选出有限候选池，再交给第二段的模型编辑评审。

### 使用脚本

| 脚本 | 作用 |
|---|---|
| `scripts/score_items.py` | 按当前排序分排序并截取候选池 |
| `scripts/judge_candidates_with_llm.py` | 第二段使用：对候选池逐条进行模型编辑评审 |

### 使用配置

```yaml
max_items_per_day: 40
editorial_candidate_pool_size: 120
editorial_judge_max_items: 120
```

### 排序依据

1. 模型评审前：按 `rule_relevance_score` 选择规则候选池。
2. 模型评审后：按 `editorial_score` 选择最终 Top 列表。

### 输出

第一段输出规则候选池；第二段输出每日 Top 40 模型评审候选信息池。

---

## 工作流 9：生成每日 AI 情报候选池 Markdown

### 作用

将模型评审后的 Top 信息列表生成可阅读、可归档、可继续分析的 Markdown 文件。

### 使用脚本

| 脚本 | 作用 |
|---|---|
| `scripts/generate_markdown.py` | 生成每日 AI 情报候选池 Markdown |

### 每条信息包含

来源等级、来源名称、发布时间、原文链接、命中关键词、来源可信分、关键词召回分、规则召回分、模型编辑分、编辑决策、内容类型、风险等级、模型分项、入选原因、Feed 摘要和阅读提醒。

### 输出文件

| 文件 | 作用 |
|---|---|
| `output/sources/latest.md` | 最新一份每日 AI 情报候选池 |
| `output/sources/YYYY-MM-DD.md` | 按日期归档的历史候选池文件 |

---

## 工作流 10：模型编辑评审

### 作用

作为第二段的核心：用模型判断候选信息是否值得进入日报，并生成后续日报可复用的单条解释字段。

### 使用文件

| 文件 | 作用 |
|---|---|
| `config/llm.yml` | 模型提供方、API Key 环境变量、候选池数量和模型调用参数 |
| `config/editorial_policy.yml` | 编辑规则、个人关注方向、高低分标准、评分校准 |
| `scripts/judge_candidates_with_llm.py` | 执行逐条模型编辑评审 |

### 当前模型配置

```yaml
enabled: true
provider: deepseek
model: deepseek-chat
base_url: https://api.deepseek.com
api_key_env: LLM_API_KEY
fallback_api_key_env: DEEPSEEK_API_KEY
fallback_on_error: false
write_failure_file: false
```

### 判定条件

模型层必须同时满足：`config/llm.yml` 存在、`config/editorial_policy.yml` 存在、`enabled` 为 `true`，并且环境变量或 GitHub Secrets 中存在 `LLM_API_KEY` 或 `DEEPSEEK_API_KEY`。

如果条件不满足，系统直接失败，不生成规则兜底日报。

### 输出

为候选信息补充 `editorial`、`editorial_score` 和 `llm` 字段。

---

## 工作流 11：选择模型日报候选池

### 作用

从已经过模型编辑评审的 Top 候选池中挑选更适合整篇日报综合解读的内容，避免把全部抓取结果都交给最终日报模型。

### 使用脚本

| 脚本 | 作用 |
|---|---|
| `scripts/generate_model_daily.py` | 选择模型日报候选池，并定义模型日报结构 |

### 使用配置

```yaml
model_daily_candidate_pool_size: 40
model_daily_max_items: 18
model_daily_max_release_items: 6
```

### 输出

输出最多 18 条模型日报候选信息。

---

## 工作流 12：抓取原文正文片段

### 作用

在生成模型日报前，尽量从原始 URL 抓取正文片段，让最终日报模型不只依赖 RSS 摘要或标题。

### 使用脚本

| 脚本 | 作用 |
|---|---|
| `scripts/fetch_article_text.py` | 抓取原文 HTML，提取 meta description、段落、标题和列表文本 |

### 使用配置

```yaml
fetch_article_text: true
article_fetch_timeout_seconds: 12
article_text_limit: 5000
```

### 输出

为模型日报候选信息补充 `article_text` 和 `article_text_source` 字段。

---

## 工作流 13：单条信息解释生成

### 作用

对候选信息生成中文标题、背景解释、核心摘要、证据说明、重要性判断和建议动作。

### 当前实现

当前版本不再单独调用旧的逐条摘要流程。单条解释已经合并进 `scripts/judge_candidates_with_llm.py` 的模型编辑评审阶段，以避免模型重复处理同一条信息。

### 使用脚本

| 脚本 | 作用 |
|---|---|
| `scripts/judge_candidates_with_llm.py` | 一次完成编辑评审和单条解释字段生成 |
| `scripts/summarize_with_llm.py` | 保留为兼容模块，主流程当前不再调用 |

### 输出

为信息补充可被最终日报复用的 `llm` 字段。

---

## 工作流 14：生成模型解读日报

### 作用

作为第二段的收口：把模型编辑评审后的候选信息整理成一份适合中文阅读、播报和复盘的 AI 情报日报。

### 使用脚本

| 脚本 | 作用 |
|---|---|
| `scripts/generate_model_daily.py` | 生成模型解读日报，控制固定章节、来源索引、链接和失败校验 |

### 必须包含的章节

模型日报必须包含：`今日一句话`、`工具链更新汇总`、`Agent / 编程工具趋势`、`开源项目 Release 汇总`、`企业应用 / 商业化信号`、`算力 / 半导体观察`、`嵌入式 AI / 物联网 / Edge AI`、`前沿研究观察`、`今日建议动作`、`附录：候选来源索引`。

### 输出文件

| 文件 | 作用 |
|---|---|
| `output/model/latest.md` | 最新模型版 AI 情报解读日报 |
| `output/model/YYYY-MM-DD.md` | 按日期归档的模型版 AI 情报解读日报 |

如果模型日报生成失败，系统直接失败，不生成规则兜底文件。

---

## 工作流 15：基于已有候选池单独生成模型日报

### 作用

用于在已经存在 `output/sources/latest.md` 或 `output/sources/YYYY-MM-DD.md` 已评审候选池的情况下，单独重新生成 `output/model/latest.md` 或 `output/model/YYYY-MM-DD.md`。

### 当前状态

当前主流程仍以 `scripts/main.py` 为入口，完整执行第一段规则采集与候选召回、第二段模型编辑评审与日报综合。

如果需要单独重跑模型日报，使用 `python scripts/generate_model_from_daily.py` 复用最新候选池，使用 `python scripts/generate_model_from_daily.py --date YYYY-MM-DD` 复用某天候选池，或使用 `python scripts/generate_model_from_daily.py --all` 批量回填所有历史候选池。这个脚本不会重新抓取数据源。GitHub Actions 的 `Refresh Model AI Intelligence Briefing` 手动运行入口也支持 `latest`、`date` 和 `all` 三种范围。

### 推荐原则

- 不要从未评审的规则候选池直接生成模型日报。
- 不要绕过 `config/editorial_policy.yml`。
- 不要恢复无 API Key 规则兜底日报。
- 单独重跑模型日报时，应保留原始链接、来源等级、编辑分和模型评审理由。

---

## 运行方式

### GitHub Actions 自动运行

`.github/workflows/daily-news.yml` 会定时运行：

```yaml
cron: '30 23 * * *'
```

对应 UTC+8 时间约为每天早上 07:30。

Actions 执行的是完整两段式流水线：

```text
Stage 1: rule-based collection and candidate recall
Stage 2: LLM editorial review and daily synthesis
```

### 必需 Secrets

至少需要配置其中一个：

| Secret | 作用 |
|---|---|
| `LLM_API_KEY` | 主模型 API Key |
| `DEEPSEEK_API_KEY` | DeepSeek API Key 兜底环境变量 |

如果两个都没有，工作流会失败。

---

## 输出文件

| 文件 | 作用 |
|---|---|
| `output/sources/latest.md` | 最新每日 AI 情报候选池，包含规则召回信息和模型编辑评审结果 |
| `output/sources/YYYY-MM-DD.md` | 按日期归档的每日候选池 |
| `output/model/latest.md` | 最新模型综合生成的中文 AI 情报日报 |
| `output/model/YYYY-MM-DD.md` | 按日期归档的模型综合生成的中文 AI 情报日报 |
| `docs/PIPELINE.md` | 当前真实 pipeline 结构说明 |

---

## 判断原则

本系统不把关键词命中当成新闻价值，不把来源等级当成重要性，也不把社区讨论当成官方确认。

当前正确理解是：

```text
第一段：规则负责采集信息、召回候选
第二段：模型负责评审价值、生成日报
```

旧理解已经不再适用：

```text
来源分 + 关键词分 + 降权分 = 最终排序
```

现在它只用于前置候选召回，不用于最终新闻价值判断。
