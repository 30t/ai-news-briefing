# AI 新闻模型解读日报｜2026-05-11

## 今日一句话

本周 AI 领域的关键信号集中在**本地推理效率的突破**和**Agent 安全与可观测性的深化**：DeepSeek V4 完整论文公开了 FP4 量化训练细节，Redis 作者在 Mac 上跑通了 1M 上下文的 DeepSeek V4 Flash；OpenAI 详细披露了 Codex 的安全运行机制，Katanemo 提出无需 GPU 的 Agent 轨迹筛选方法；同时，DIY 硬件市场因内存涨价正在萎缩，而社区在 12GB VRAM 显卡上实现了 80 tok/s 的推理速度。

---

## 工具链更新汇总

### Open WebUI v0.9.5：安全加固与渲染控制
[5. Open WebUI v0.9.5 发布：新增 SSRF 保护、iframe CSP 和 Markdown 渲染控制](https://github.com/open-webui/open-webui/releases/tag/v0.9.5)

**Open WebUI** 是一个流行的自托管 AI 对话平台，支持连接各种大模型后端（如 Ollama、vLLM、OpenAI API 等），提供聊天、文件上传、工具调用等功能。本次 v0.9.5 版本主要聚焦安全性和用户体验：

- **SSRF 保护**：默认阻止所有出站 HTTP 请求的 3xx 重定向（通过 `AIOHTTP_CLIENT_ALLOW_REDIRECTS` 环境变量控制），防止攻击者利用公开 URL 将请求重定向到内部网络地址（如 192.168.x.x、127.0.0.1、云元数据端点）。受影响的功能包括网页抓取、图片加载、OAuth 发现、工具服务器执行和代码解释器登录。
- **iframe 内容安全策略（CSP）**：管理员可通过 `IFRAME_CSP` 环境变量配置 srcdoc iframe 的 CSP，限制 LLM 生成或用户上传的 HTML 在预览中能加载和执行的内容。
- **Markdown 渲染控制**：用户现在可以在界面设置中独立禁用用户消息和助手回复的 Markdown 渲染，避免粘贴含 Markdown 敏感字符的文本时出现意外格式。

**为什么重要**：自托管平台的安全风险常被低估。SSRF 保护直接防止了内部网络泄露，CSP 配置阻止了恶意脚本执行，这两项更新让 Open WebUI 更适合企业或敏感环境部署。建议自托管用户尽快升级。

### Open WebUI v0.9.3：性能优化与语音模式改进
[16. Open WebUI v0.9.3：Added](https://github.com/open-webui/open-webui/releases/tag/v0.9.3)

v0.9.3 版本（5月9日发布）主要优化了性能：提示词列表和聊天历史加载速度显著提升（通过单次数据库查询过滤），同时新增语音模式的静音切换（快捷键 M）和自动取消静音功能。**原文未给出量化性能提升数据**，但架构优化方向明确。建议普通用户关注 v0.9.5 的安全更新，v0.9.3 的改进已包含在 v0.9.5 中。

---

## Agent / 编程工具趋势

### OpenAI 详解 Codex 安全运行机制
[9. Running Codex safely at OpenAI](https://openai.com/index/running-codex-safely)

**背景**：Codex 是 OpenAI 的编程 Agent，能够自主编写和执行代码。随着 Agent 权限增大（如文件读写、网络访问、数据库操作），安全问题成为企业采用的核心障碍。

**本次内容**：OpenAI 官方博客详细披露了 Codex 在生产环境中的安全架构，包括：
- **沙箱隔离**：代码执行在隔离环境中运行，无法访问宿主系统。
- **审批机制**：关键操作（如文件删除、网络请求）需要人工确认（HITL，人在回路中）。
- **网络策略**：限制 Agent 可访问的网络端点，防止数据外泄。
- **Agent 原生遥测**：内置监控和日志系统，追踪 Agent 的每一步操作。

**为什么重要**：这是 OpenAI 首次系统性地公开 Agent 安全架构，为企业和开发者提供了可参考的安全设计模式。对于正在构建或采购 Agent 工具的团队，这些原则（沙箱 + 审批 + 网络策略 + 遥测）应成为基本要求。

### GitHub Copilot CLI 的 Rubber Duck 支持更多模型
[3. Rubber Duck in GitHub Copilot CLI now supports more models](https://github.blog/changelog/2026-05-07-rubber-duck-in-github-copilot-cli-now-supports-more-models)

**背景**：Rubber Duck 是 GitHub Copilot CLI 中的跨模型审查 Agent，它使用不同模型家族的组合来提供“第二意见”——即让一个模型审查另一个模型生成的代码，以发现架构问题、细微 bug 和跨文件冲突。

**本次变化**：
- 当用户选择 GPT 模型作为编排器时，Rubber Duck 现在可以使用 Claude 驱动的审查 Agent 提供第二意见。
- 当用户选择 Claude 作为编排器时，Rubber Duck 升级为使用 GPT-5.5 作为审查模型。

**为什么重要**：这种“跨家族模型互审”策略利用了不同模型的能力差异来提升代码质量。用户无需手动切换模型，Copilot CLI 自动调度。需要启用 `/experimental` 功能才能使用。

### Grok Code Fast 1 即将在 GitHub Copilot 中弃用
[4. Upcoming deprecation of Grok Code Fast 1](https://github.blog/changelog/2026-05-08-upcoming-deprecation-of-grok-code-fast-1)

GitHub 宣布将于 **5月15日** 弃用 Grok Code Fast 1 模型，涉及 Copilot Chat、内联编辑、ask 和 agent 模式以及代码补全等所有体验。弃用原因是模型提供商停止支持。建议使用 Grok Code Fast 1 的用户在截止日期前切换到其他支持的模型。企业管理员需在 Copilot 设置中启用替代模型的访问权限。

### Katanemo Labs 提出 Signals：无需 GPU 的轻量级 Agent 轨迹筛选方法
[14. Katanemo Labs 提出 Signals：无需 LLM 的轻量级 Agent 轨迹筛选方法](https://www.reddit.com/r/MachineLearning/comments/1t9d3et/signals_finding_the_most_informative_agent_traces)

**背景**：在 Agent 开发和部署中，开发者需要审查大量 Agent 执行轨迹（trajectories）来发现问题、改进行为。传统方法要么靠人工逐条审查（成本高），要么用额外的 LLM 调用自动评估（也贵且慢）。

**本次研究**：Katanemo Labs（DigitalOcean 旗下）提出 **Signals** 方法，从 Agent 交互中计算结构化信号（如 misalignment、stagnation、looping、exhaustion 等），无需额外 LLM 调用或 GPU。在 τ-bench 上的标注研究中，基于信号的采样达到 **82% 信息率**（随机采样为 54%），效率提升 1.52 倍。

**为什么重要**：该方法直接降低了 Agent 轨迹审查成本，且已开源实现（项目 [Plano](https://github.com/katanemo/plano)）。对于大规模 Agent 部署团队，这是一个立即可用的工具。**注意**：这是社区研究，结果基于特定 benchmark，实际效果可能因场景而异。

### Qwen/WebWorld：面向 Web Agent 训练的开源世界模型系列
[6. Qwen/WebWorld 32B/14B/8B (Qwen3 finetune)](https://www.reddit.com/r/LocalLLaMA/comments/1t6c6vs/qwenwebworld_32b14b8b_qwen3_finetune)

**背景**：Web Agent 需要理解网页结构和用户交互，但训练数据获取困难。WebWorld 是一个基于 Qwen3 微调的开源世界模型系列，专门用于训练和评估 Web Agent。

**关键数据**：
- 在 100 万+ 真实网页交互轨迹上训练，支持 30 步以上的长周期模拟。
- 支持多种状态表示格式：A11y Tree（无障碍树）、HTML、XML、Markdown 和自然语言。
- 基于 WebWorld 合成轨迹训练的 Agent 在 MiniWob++ 上提升 **+9.9%**，在 WebArena 上提升 **+10.9%**。
- 作为推理时的前瞻搜索世界模型，WebWorld 表现优于 GPT-5。

**为什么重要**：WebWorld 提供了高质量的开源训练数据生成器和世界模型，对 Web Agent 研究和开发有直接价值。模型已在 Hugging Face 上发布（32B/14B/8B 三个尺寸）。**注意**：这是社区发布，结果基于特定 benchmark，不等于产品化。

### Redis 作者发布 DS4：在 Mac Metal 上运行 DeepSeek V4 Flash
[15. Redis作者发布DS4：在Mac Metal上运行DeepSeek V4 Flash，支持1M上下文窗口](https://www.reddit.com/r/LocalLLaMA/comments/1t95k73/ds4)

**背景**：Salvatore Sanfilippo（Redis 创始人）在 GitHub 上开源了 **DS4** 项目，目标是让 DeepSeek V4 Flash 在 Mac Metal 硬件上运行，并支持 1M 上下文窗口。

**当前进展**：
- 已在 Mac Metal 上成功运行 1M 上下文窗口。
- 发布了在 DGX 上运行的视频。
- 服务器已支持 OpenAI 和 Anthropic 端点，可用于 Agentic 代码工具。

**为什么重要**：Redis 作者的技术创新可能推动本地大模型推理效率，尤其对 Mac 用户和 Agent 工作流开发者有直接价值。**注意**：这是社区项目，仍处于早期阶段，性能和生产可用性有待验证。

### 本地 LLM 代码生成测试：质量 vs 速度
[7. Testing Local LLMs in Practice: Code Generation, Quality vs. Speed](https://www.reddit.com/r/LocalLLaMA/comments/1t7et9q/testing_local_llms_in_practice_code_generation)

一位开发者分享了他构建的评估框架，用于测试本地 LLM 在自主编写 Go 代码（日志解析器生成）时的质量和速度。框架包括编译验证、字段类型校验、解析质量评估和吞吐量追踪。**原文未给出具体模型排名**，但提出了一个可复用的评估方法论。对于正在评估本地模型用于代码生成的团队，这是一个值得参考的测试框架。

### Lightning-MLX：为 Apple Silicon 优化的本地推理引擎
[8. I've created the fastest local AI engine for Apple Silicon. Optimised for agentic use.](https://www.reddit.com/r/LocalLLaMA/comments/1t6uzdk/ive_created_the_fastest_local_ai_engine_for_apple)

一位开发者发布了 **Lightning-MLX**，一个针对 Apple Silicon 优化的本地推理引擎，专注于编码 Agent、工具调用和短周期工作流。在 MacBook Max M5（128GB）上，Qwen3.6-27B 达到 **40.67 tok/s**，Qwen3.6-35B-A3B 达到 **220.86 tok/s**。**注意**：这是社区项目，结果基于特定硬件和测试条件，不等于官方基准。

### llama.cpp 新增 Sarvam MoE 架构支持
[10. model: add sarvam_moe architecture support by sumitchatterjee13 · Pull Request #20275 · ggml-org/llama.cpp](https://www.reddit.com/r/LocalLLaMA/comments/1t8db1j/model_add_sarvam_moe_architecture_support_by)

llama.cpp 正在合并对 **Sarvam MoE** 架构的支持。Sarvam 是印度 AI 公司发布的混合专家（MoE）模型系列，包括 Sarvam-30B（2.4B 活跃参数）和 Sarvam-105B（10.3B 活跃参数），在推理、编码和 Agent 任务上表现突出，尤其擅长 22 种印度语言。**注意**：这是 Pull Request 阶段，尚未合并到主分支。

---

## 开源项目 Release 汇总

### llama.cpp b9095：新增内部 AllReduce 内核，支持无 NCCL 的 2 GPU 张量并行
[13. llama.cpp b9095：新增内部 AllReduce 内核，支持无 NCCL 的 2 GPU 张量并行](https://github.com/ggml-org/llama.cpp/releases/tag/b9095)

**背景**：llama.cpp 是高性能大模型推理框架，支持多种硬件后端。在多 GPU 张量并行（Tensor Parallelism）场景下，通常需要 NCCL（NVIDIA 的集合通信库）来在 GPU 之间同步数据。

**本次更新**：b9095 版本新增了 `ggml_cuda_allreduce_provider`，通过 `GGML_CUDA_ALLREDUCE` 环境变量可选择 `nccl` 或 `internal` 提供者。内部实现使用单阶段 CUDA 内核，通过 D2H 拷贝、跨 GPU 握手和归约合并为一次内核启动。

**当前限制**：仅支持 2 张 GPU、FP32 张量。超过 2 张 GPU 或非 FP32 时会回退到元后端 CPU 归约。

**为什么重要**：对于多卡推理用户，该功能可减少对 NCCL 的依赖，简化部署并可能降低延迟，尤其适合本地或边缘场景。建议多 GPU 用户测试此版本。

### DeepSeek V4 完整论文公开：FP4 量化训练细节与训练稳定性技巧
[11. DeepSeek V4 paper full version is out, FP4 QAT details and stability tricks 【D】](https://www.reddit.com/r/MachineLearning/comments/1t7yrvr/deepseek_v4_paper_full_version_is_out_fp4_qat)

**背景**：DeepSeek V4 是 DeepSeek 的最新大模型系列，包含 V4-Pro 和 V4-Flash 两个版本。此前预览版论文为 58 页，完整版增加了大量技术细节。

**关键发现**：
- **FP4 量化感知训练（QAT）**：在训练后期直接进行 FP4 量化训练。MoE 专家权重量化为 FP4（主要 GPU 内存消耗者），CSA 索引器的 QK 路径使用 FP4 激活。QK 选择器实现 2 倍加速，99.7% 召回率保持。推理直接在 FP4 权重上运行。
- **效率对比**：相比 V3.2 基线，V4-Pro 的 1M 上下文 FLOPs 降至 27%，KV 缓存降至 10%；V4-Flash 的 FLOPs 降至 10%，KV 缓存降至 7%。
- **训练稳定性**：万亿参数 MoE 训练中的 loss spike 问题通过两种机制解决：**预期路由**（故意让主模型和路由器更新不同步，打破反馈循环）和 **SwiGLU 钳位**（对 SwiGLU 线性路径和门控路径设置硬限制）。

**为什么重要**：FP4 量化训练是行业前沿方向，DeepSeek 的实践证明了在万亿参数规模下实现 FP4 推理的可行性。**注意**：这是论文研究，不等于已经产品化。但效率数据极具参考价值。

### 在 2020 年中端安卓手机上运行 6 个小语言模型
[12. Hand-written OpenCL kernels for LLM inference on Adreno 6xx — running 6 small language models on a 2020 mid-range Android phone](https://www.reddit.com/r/embedded/comments/1t83ung/handwritten_opencl_kernels_for_llm_inference_on)

一位开发者编写了手写 OpenCL 内核，在搭载 Adreno 6xx GPU（Snapdragon 6/7 系列）的 2020 年中端安卓手机上运行了 6 个小语言模型。llama.cpp 官方文档曾表示“A6x 手机 GPU 可能不支持”。实测结果（fp16，贪心解码，5 次运行中位数）：
- SmolLM2-135M：23.65 tok/s
- Mamba2-130M：23.18 tok/s
- Mamba-130M：22.15 tok/s
- OpenELM-270M：14.81 tok/s
- LFM2.5-350M：11.51 tok/s
- Qwen2.5-0.5B：10.41 tok/s

项目已开源：[adreno-llms](https://github.com/a8nova/adreno-llms)。**注意**：这是社区实验，结果受硬件和测试条件影响，不等于产品化。

### 12GB VRAM 上实现 80 tok/s 和 128K 上下文
[18. 80 tok/sec and 128K context on 12GB VRAM with Qwen3.6 35B A3B and llama.cpp MTP](https://www.reddit.com/r/LocalLLaMA/comments/1t82zxv/80_toksec_and_128k_context_on_12gb_vram_with)

一位社区用户分享了在 **RTX 4070 Super（12GB VRAM）** 上使用最新 llama.cpp 构建和 MTP（Multi-Token Prediction）PR 的配置：Qwen3.6-35B-A3B 模型在 Q4_K_XL 量化下达到 **80+ tok/s**，草稿接受率 80%+，支持 128K 上下文。**注意**：这是社区测试结果，需要从源码构建并应用未合并的 PR，不适合生产环境。

---

## 企业应用 / 商业化信号

### GitHub Copilot 模型更新：Grok Code Fast 1 弃用
（已在 Agent / 编程工具趋势章节详细展开，此处不再重复）

### OpenAI Codex 安全架构公开
（已在 Agent / 编程工具趋势章节详细展开，此处不再重复）

### GitHub Copilot CLI Rubber Duck 多模型支持
（已在 Agent / 编程工具趋势章节详细展开，此处不再重复）

---

## 算力 / 半导体观察

### DIY 市场萎缩：高 RAM 价格冲击 PC 组装市场
[17. DIY market declining amid high RAM prices](https://www.reddit.com/r/LocalLLaMA/comments/1t6gmcn/diy_market_declining_amid_high_ram_prices)

**背景**：DIY（Do It Yourself，自己组装电脑）市场是个人开发者、AI 爱好者和中小团队获取算力的重要渠道。

**关键数据**：
- 华硕 2025 年出货 1500 万块主板，预计 2026 年仅出货 1000 万块。
- AI 需求导致芯片产能被挤压，内存和 CPU 出现短缺和涨价。
- 四大台湾主板制造商全部下调 2026 年出货目标，部分出现“崩盘式”下滑。
- NVIDIA GPU 升级放缓，加上 CPU 和内存短缺，导致主板制造商出货目标全面崩溃。

**为什么重要**：对于依赖 DIY 硬件进行本地 AI 推理的用户，这意味着硬件成本上升、选择减少。建议关注二手市场和企业淘汰设备，同时考虑云 GPU 实例作为替代方案。**注意**：这是行业媒体报道和社区讨论，数据来自 Digitimes，需关注后续官方财报验证。

### llama.cpp b9095 内部 AllReduce 内核
（已在开源项目 Release 汇总章节详细展开，此处不再重复）

### DeepSeek V4 FP4 量化训练
（已在开源项目 Release 汇总章节详细展开，此处不再重复）

---

## 嵌入式 AI / 物联网 / Edge AI

### 在 2020 年中端安卓手机上运行 LLM
（已在开源项目 Release 汇总章节详细展开，此处不再重复）

### AgenTEE：边缘设备上的机密 LLM Agent 执行
[2. AgenTEE: Confidential LLM Agent Execution on Edge Devices](https://arxiv.org/abs/2604.18231)

**背景**：在边缘设备上运行 LLM Agent 面临隐私和安全挑战——模型权重和用户数据可能被泄露。AgenTEE 提出利用 TEE（可信执行环境，Trusted Execution Environment）在边缘设备上实现机密 LLM Agent 执行。

**为什么重要**：如果实现，这将使边缘 AI 设备（如手机、IoT 网关）能够安全运行 Agent，保护模型权重和用户数据。**注意**：这是 arXiv 论文，属于早期研究信号，不等于已经产品化。原文信息不足，无法判断具体实现细节和性能数据。

---

## 前沿研究观察

### Can LLMs Make (Personalized) Access Control Decisions?
[1. Can LLMs Make (Personalized) Access Control Decisions?](https://arxiv.org/abs/2511.20284)

**背景**：访问控制（Access Control）是信息安全的核心问题——决定谁可以访问什么资源。传统方法依赖预定义规则，但个性化场景（如每个用户有不同权限）需要更灵活的方案。

**研究问题**：LLM 能否做出个性化访问控制决策？**原文信息不足，无法判断具体方法、实验设置和结果**。**注意**：这是 arXiv 论文，属于早期研究信号，不等于已经产品化。

### AgenTEE：边缘设备上的机密 LLM Agent 执行
（已在嵌入式 AI / 物联网 / Edge AI 章节详细展开，此处不再重复）

### DeepSeek V4 完整论文
（已在开源项目 Release 汇总章节详细展开，此处不再重复）

### Katanemo Signals
（已在 Agent / 编程工具趋势章节详细展开，此处不再重复）

---

## 今日建议动作

1. **检查 Open WebUI 版本**：如果自托管 Open WebUI，立即升级到 v0.9.5 以获得 SSRF 保护和 CSP 配置。检查 `AIOHTTP_CLIENT_ALLOW_REDIRECTS` 和 `IFRAME_CSP` 环境变量配置。

2. **评估 GitHub Copilot 模型切换**：如果使用 Grok Code Fast 1，在 5月15日前切换到其他支持的模型。企业管理员需检查 Copilot 设置中的模型策略。

3. **试用 Rubber Duck 跨模型审查**：在 GitHub Copilot CLI 中启用 `/experimental`，体验跨家族模型互审功能。

4. **关注 DeepSeek V4 论文细节**：FP4 量化训练和训练稳定性技巧对模型训练团队有参考价值。建议阅读完整论文。

5. **评估 Katanemo Signals**：如果正在开发或运维 Agent 系统，试用 [Plano](https://github.com/katanemo/plano) 项目中的 Signals 方法，降低轨迹审查成本。

6. **测试 llama.cpp b9095**：如果使用 2 张 GPU 进行推理，测试新的内部 AllReduce 内核，评估是否可减少对 NCCL 的依赖。

7. **关注 DS4 项目进展**：如果使用 Mac 进行本地推理，关注 [DS4](https://github.com/antirez/ds4/) 项目，但暂不建议用于生产环境。

8. **重新评估 DIY 硬件采购计划**：鉴于内存和 CPU 涨价趋势，考虑云 GPU 实例或二手企业设备作为替代方案。

9. **暂时忽略**：AgenTEE 和 LLM 访问控制论文仍处于早期研究阶段，暂无需深入跟进。

---

## 附录：候选来源索引

| 编号 | 标题 | 来源等级 | 来源名称 | 链接 |
|------|------|----------|----------|------|
| 1 | Can LLMs Make (Personalized) Access Control Decisions? | 早期信号 | arXiv cs.AI | [链接](https://arxiv.org/abs/2511.20284) |
| 2 | AgenTEE: Confidential LLM Agent Execution on Edge Devices | 早期信号 | arXiv cs.OS | [链接](https://arxiv.org/abs/2604.18231) |
| 3 | Rubber Duck in GitHub Copilot CLI now supports more models | 官方确认 | GitHub Changelog | [链接](https://github.blog/changelog/2026-05-07-rubber-duck-in-github-copilot-cli-now-supports-more-models) |
| 4 | Upcoming deprecation of Grok Code Fast 1 | 官方确认 | GitHub Changelog | [链接](https://github.blog/changelog/2026-05-08-upcoming-deprecation-of-grok-code-fast-1) |
| 5 | Open WebUI v0.9.5 发布：新增 SSRF 保护、iframe CSP 和 Markdown 渲染控制 | 官方确认 | Open WebUI | [链接](https://github.com/open-webui/open-webui/releases/tag/v0.9.5) |
| 6 | Qwen/WebWorld 32B/14B/8B (Qwen3 finetune) | 技术社区 | Reddit r/LocalLLaMA | [链接](https://www.reddit.com/r/LocalLLaMA/comments/1t6c6vs/qwenwebworld_32b14b8b_qwen3_finetune) |
| 7 | Testing Local LLMs in Practice: Code Generation, Quality vs. Speed | 技术社区 | Reddit r/LocalLLaMA | [链接](https://www.reddit.com/r/LocalLLaMA/comments/1t7et9q/testing_local_llms_in_practice_code_generation) |
| 8 | I've created the fastest local AI engine for Apple Silicon. Optimised for agentic use. | 技术社区 | Reddit r/LocalLLaMA | [链接](https://www.reddit.com/r/LocalLLaMA/comments/1t6uzdk/ive_created_the_fastest_local_ai_engine_for_apple) |
| 9 | Running Codex safely at OpenAI | 官方确认 | OpenAI News | [链接](https://openai.com/index/running-codex-safely) |
| 10 | model: add sarvam_moe architecture support | 技术社区 | Reddit r/LocalLLaMA | [链接](https://www.reddit.com/r/LocalLLaMA/comments/1t8db1j/model_add_sarvam_moe_architecture_support_by) |
| 11 | DeepSeek V4 paper full version is out, FP4 QAT details and stability tricks | 技术社区 | Reddit r/MachineLearning | [链接](https://www.reddit.com/r/MachineLearning/comments/1t7yrvr/deepseek_v4_paper_full_version_is_out_fp4_qat) |
| 12 | Hand-written OpenCL kernels for LLM inference on Adreno 6xx | 技术社区 | Reddit r/embedded | [链接](https://www.reddit.com/r/embedded/comments/1t83ung/handwritten_opencl_kernels_for_llm_inference_on) |
| 13 | llama.cpp b9095：新增内部 AllReduce 内核，支持无 NCCL 的 2 GPU 张量并行 | 官方确认 | llama.cpp | [链接](https://github.com/ggml-org/llama.cpp/releases/tag/b9095) |
| 14 | Katanemo Labs 提出 Signals：无需 LLM 的轻量级 Agent 轨迹筛选方法 | 技术社区 | Reddit r/MachineLearning | [链接](https://www.reddit.com/r/MachineLearning/comments/1t9d3et/signals_finding_the_most_informative_agent_traces) |
| 15 | Redis作者发布DS4：在Mac Metal上运行DeepSeek V4 Flash，支持1M上下文窗口 | 技术社区 | Reddit r/LocalLLaMA | [链接](https://www.reddit.com/r/LocalLLaMA/comments/1t95k73/ds4) |
| 16 | Open WebUI v0.9.3：Added | 官方确认 | Open WebUI | [链接](https://github.com/open-webui/open-webui/releases/tag/v0.9.3) |
| 17 | DIY market declining amid high RAM prices | 技术社区 | Reddit r/LocalLLaMA | [链接](https://www.reddit.com/r/LocalLLaMA/comments/1t6gmcn/diy_market_declining_amid_high_ram_prices) |
| 18 | 80 tok/sec and 128K context on 12GB VRAM with Qwen3.6 35B A3B and llama.cpp MTP | 技术社区 | Reddit r/LocalLLaMA | [链接](https://www.reddit.com/r/LocalLLaMA/comments/1t82zxv/80_toksec_and_128k_context_on_12gb_vram_with) |
