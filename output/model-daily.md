# AI 新闻模型解读日报｜2026-05-17

## 今日一句话

今日 AI 新闻的核心信号是 **Agent 安全与评测正在成为独立的研究方向**，同时 **开源模型在 Agent 基准上首次超越闭源旗舰**，而 **本地推理硬件的选型对比也有了更真实的数据支撑**。GitHub Copilot 的自动模型选择功能则让企业用户能以更低成本使用 Agent。

## 工具链更新汇总

**llama.cpp b9180 发布：新增 MTP（多 token 预测）支持，提升 speculative decoding 效率**

[7. llama.cpp b9180 发布：新增 MTP（多 token 预测）支持，提升 speculative decoding 效率](https://github.com/ggml-org/llama.cpp/releases/tag/b9180)

**背景**：llama.cpp 是目前最流行的本地大模型推理引擎之一，广泛用于个人电脑、服务器甚至边缘设备上运行开源模型。它支持 CPU、GPU（Vulkan、Metal、CUDA）等多种后端，是本地 AI 部署的核心工具。

**原来的问题**：Speculative decoding（推测解码）是一种加速推理的技术——用一个更小的“草稿模型”快速生成多个 token，再由大模型验证。但之前的实现中，如果草稿 token 被拒绝，目标模型需要从检查点重新开始，造成计算浪费。

**这次发生了什么**：本次 b9180 版本为 speculative decoding 新增了 **MTP（Multi-Token Prediction，多 token 预测）支持**。MTP 是一种让模型一次性预测多个未来 token 的训练和推理方法，能提高草稿 token 的接受率。

**具体变化**：
- 新增 MTP 模型转换工具（`convert.py` 更新）
- 后端适配：Vulkan 和 Metal 后端均增加了 GDN（Gated Delta Net）部分序列回滚支持，允许在草稿 token 被拒绝时只回滚到 `draft_max` 位置，而不是从头开始
- 减少了目标模型的计算浪费

**结果或证据**：原文未给出明确量化结果，但技术原理上，MTP 和部分回滚机制能显著提升 speculative decoding 的效率和稳定性。

**为什么重要**：对于依赖本地推理的开发者、边缘 AI 部署以及需要低延迟推理的场景（如实时对话、代码补全），MTP 支持意味着在相同硬件上可以获得更快的推理速度。

**建议动作**：如果你正在使用 llama.cpp 进行本地推理，并且使用了 speculative decoding，建议升级到 b9180 并测试 MTP 带来的性能提升。普通用户可暂时忽略，等待社区反馈。

## Agent / 编程工具趋势

**社区实测：Strix Halo、RTX 3090 与 RTX 5070 推理性能对比**

[2. 社区实测：Strix Halo、RTX 3090与RTX 5070推理性能对比](https://www.reddit.com/r/LocalLLaMA/comments/1tf9iyk/ran_the_same_models_across_strix_halo_rtx_3090)

**背景**：Strix Halo 是 AMD 的下一代 APU（融合 CPU 和 GPU 的芯片），RTX 3090（24GB 显存）和 RTX 5070（12GB 显存）是 NVIDIA 的两代消费级 GPU。这三款硬件覆盖了从集成显卡到高端独显的推理场景。

**原来的问题**：社区中关于不同硬件推理性能的对比往往来自厂商宣传或零散测试，缺乏在同一测试条件下的“苹果对苹果”比较，尤其是针对 Agent 和 RAG（检索增强生成）工作负载。

**这次发生了什么**：一位 Reddit 用户在 r/LocalLLaMA 社区发布了一份详细的硬件推理性能对比测试。**社区讨论，不等于官方确认，结果可能受测试条件、样本和硬件环境影响。**

**具体变化**：
- 测试了 55 次运行，涵盖 5 种后端（ROCm、Vulkan、CPU、CUDA、vLLM-CUDA）
- 模型从 0.35B 到 35B-A3B（MoE 混合专家模型）
- 工作负载包括短提示聊天、长上下文 RAG、代码生成和 Agent 场景（并发 1 和 4）
- 每次运行前验证 VRAM 是否足够，温度设为 0，3 次测量取结果

**结果或证据**：
- **RTX 5070（12GB GDDR7，Vulkan）在 12GB 显存能容纳的模型上全面超越 RTX 3090（24GB GDDR6X，CUDA）**：例如 Gemma-3-4b 聊天任务，5070 达 156.6 tok/s，3090 为 142.0 tok/s
- **RTX 3090 在 14-31B 参数区间凭借更大显存胜出**：例如 Gemma-4-26B-A4B 聊天任务，3090 达 100.5 tok/s，而 Strix Halo 的 ROCm 后端仅 43.7 tok/s
- Strix Halo 的 Vulkan 后端通常比 ROCm 后端略快

**为什么重要**：该对比为端侧推理硬件选型提供了真实、可复现的性能数据，尤其对 Agent 和 RAG 工作流的部署决策有参考价值。它表明：**显存大小仍然是选择大模型推理硬件的关键因素**，但新一代 GPU 的带宽优势在小模型上非常明显。

**建议动作**：如果你正在为本地 Agent 或 RAG 应用选择硬件，可以仔细阅读该测试的完整数据。对于 12GB 显存能容纳的模型（如 7B-8B 参数），RTX 5070 性价比更高；对于需要运行 14B 以上模型的场景，RTX 3090 的 24GB 显存仍是优势。

---

**Qwen3.6-35B-A3B 登上 Terminal-Bench 2.0 排行榜，超越 Gemini 2.5 Pro**

[5. Qwen3.6-35B-A3B登上Terminal-Bench 2.0排行榜，超越Gemini 2.5 Pro](https://www.reddit.com/r/LocalLLaMA/comments/1temio0/qwen3635ba3b_and_9b_are_officially_on_the_public)

**背景**：Terminal-Bench 2.0 是一个专门评测 AI Agent 在终端（命令行）环境中完成任务能力的基准测试，涵盖代码编写、文件操作、系统管理等任务。Qwen3.6-35B-A3B 是阿里云 Qwen 系列的最新开源模型，采用 MoE（混合专家）架构，总参数 35B，激活参数约 3B。

**原来的问题**：此前 Terminal-Bench 排行榜上，闭源模型 Gemini 2.5 Pro 和 Qwen3-Coder-480B（480B 参数）占据前列，开源模型在 Agent 基准上的竞争力有待验证。

**这次发生了什么**：Qwen3.6-35B-A3B 在 Terminal-Bench 2.0 上达到 **24.6%（±3.2）**，超过 Gemini 2.5 Pro 的 19.6% 和 Qwen3-Coder-480B 的 23.9%。**社区讨论，不等于官方确认，结果可能受测试条件、样本和硬件环境影响。**

**具体变化**：该结果由社区项目 `little-coder` 配合 Qwen3.6-35B-A3B 取得，展示了开源模型在 Agent 基准上的竞争力。

**为什么重要**：这是开源模型首次在 Terminal-Bench 上超越闭源旗舰模型，且 Qwen3.6-35B-A3B 的参数量远小于 Gemini 2.5 Pro 和 Qwen3-Coder-480B。同时，Qwen3.5-9B 也取得了 9.2% 的分数，表明 **10B 以下的小模型在 Agent 基准上也能取得可测量结果**，这对本地 Agent 部署和模型选型有重要参考意义。

**建议动作**：关注 Agent 工作流的开发者可以测试 Qwen3.6-35B-A3B 在终端任务上的表现。该模型在 Hugging Face 上可下载，适合本地部署。

---

**Intern-S2-Preview：35B 参数的科学多模态基础模型**

[6. internlm/Intern-S2-Preview · Hugging Face](https://www.reddit.com/r/LocalLLaMA/comments/1tdrw0s/internlminterns2preview_hugging_face)

**背景**：Intern-S2-Preview 是上海 AI 实验室（InternLM 团队）发布的新模型，基于 Qwen3.5 继续预训练，总参数 35B。**社区讨论，不等于官方确认，结果可能受测试条件、样本和硬件环境影响。**

**原来的问题**：科学领域的 AI 模型通常需要大量参数（如万亿级参数）才能达到专业水平，部署成本极高。

**这次发生了什么**：Intern-S2-Preview 探索了“任务缩放”（task scaling）——通过增加科学任务的难度、多样性和覆盖范围，而非单纯增加参数和数据，来提升模型能力。它采用从预训练到强化学习的全链条训练流程，在多个核心专业科学任务上达到了与万亿级参数 Intern-S1-Pro 相当的性能。

**具体变化**：
- 仅 35B 参数，但性能与万亿级模型相当
- 增强了小分子结构的空间建模能力
- 引入了实值预测模块
- 是首个具备材料晶体结构生成能力的开源模型
- 同时保持了强大的通用推理、多模态理解和 Agent 能力

**为什么重要**：这表明 **任务缩放可能是比参数缩放更高效的模型能力提升路径**，尤其适用于科学计算等专业领域。对于需要科学 AI 能力但算力有限的团队，35B 模型比万亿级模型更可部署。

**建议动作**：关注科学 AI 和材料计算的研究者可以测试 Intern-S2-Preview 在自身任务上的表现。该模型在 Hugging Face 上可用。

## 开源项目 Release 汇总

**llama.cpp b9180 发布：新增 MTP 支持**

已在“工具链更新汇总”章节详细展开，此处不再重复。

## 企业应用 / 商业化信号

**GitHub Copilot Cloud Agent 支持自动模型选择**

[1. Copilot cloud agent supports auto model selection](https://github.blog/changelog/2026-05-14-copilot-cloud-agent-supports-auto-model-selection)

**背景**：GitHub Copilot 是 GitHub 推出的 AI 编程助手，其 Cloud Agent 功能允许开发者在云端运行 Agent 任务，自动完成代码编写、调试、重构等复杂工作流。

**原来的问题**：开发者在使用 Copilot Cloud Agent 时，需要手动选择底层模型（如 GPT-4、Claude 等），不同模型有不同的性能、成本和速率限制，选择不当可能导致成本过高或任务失败。

**这次发生了什么**：GitHub 为 Copilot Cloud Agent 新增了 **自动模型选择（Auto Model Selection）** 功能。当用户在模型选择器中选择“Auto”时，Copilot 会根据系统健康状态和模型性能，智能选择当前可用的最佳模型。

**具体变化**：
- 自动选择基于系统健康度和模型性能
- 使用 Auto 模式可享受 **10% 的模型乘数折扣**
- 不受每周速率限制影响

**结果或证据**：原文未给出明确量化结果，但该功能直接降低了用户的使用成本和决策复杂度。

**为什么重要**：这是 AI 编程工具从“手动选模型”向“智能路由”演进的重要一步。对于企业用户，自动模型选择意味着更低的运营成本和更稳定的服务质量。对于个人开发者，10% 的折扣和不受速率限制是直接的经济激励。

**建议动作**：如果你正在使用 GitHub Copilot Cloud Agent，建议切换到 Auto 模型选择模式，以降低成本和避免速率限制。企业管理员可以评估该功能对团队开发效率的影响。

## 算力 / 半导体观察

**社区实测：Strix Halo、RTX 3090 与 RTX 5070 推理性能对比**

已在“Agent / 编程工具趋势”章节详细展开。该测试的核心结论对算力选型有直接参考价值：**显存大小仍是推理硬件的关键瓶颈，但新一代 GPU 的带宽优势在小模型上非常明显**。

## 嵌入式 AI / 物联网 / Edge AI

今日无直接相关的嵌入式 AI 或 Edge AI 新闻。但 llama.cpp b9180 的 MTP 支持对边缘推理场景有潜在意义——更高效的 speculative decoding 意味着在低功耗设备上也能获得更快的推理速度。

## 前沿研究观察

**AgentTrap：第三方 Agent 技能运行时信任失效的测量基准**

[3. AgentTrap：第三方Agent技能运行时信任失效的测量基准](https://arxiv.org/abs/2605.13940)

**背景**：随着 Agent 生态的发展，开发者越来越多地使用第三方开发的“技能”（skills）或“工具”（tools）来扩展 Agent 的能力。这些第三方技能可能包含恶意代码或逻辑漏洞。

**原来的问题**：目前缺乏系统性的方法来评估第三方 Agent 技能在运行时（runtime）的信任失效问题——即技能在执行过程中是否会被恶意利用，导致数据泄露、系统破坏或权限提升。

**这次发生了什么**：arXiv 上的一篇论文提出了 **AgentTrap 基准**，包含 141 个任务（91 个恶意 + 50 个良性），覆盖 16 个安全维度。**研究信号不等于产品落地。**

**具体变化**：
- 在沙箱环境中评估 Agent 的完整执行轨迹
- 判断攻击是否成功、被阻止或未触发
- 覆盖了多种攻击向量，如命令注入、文件系统滥用、网络访问等

**为什么重要**：Agent 供应链安全是 Agent 大规模部署的关键障碍。AgentTrap 为开发者评估和防御第三方技能风险提供了可操作的测试框架。随着 Agent 生态的快速发展，这类安全基准将成为行业标准。

**建议动作**：如果你正在开发或使用 Agent 平台，建议阅读该论文并考虑将 AgentTrap 纳入安全测试流程。对于普通用户，这是一个值得关注的趋势——未来 Agent 平台可能会要求第三方技能通过类似的安全测试。

---

**BenchJack：系统审计 AI Agent 基准测试**

[4. Do Androids Dream of Breaking the Game? Systematically Auditing AI Agent Benchmarks with BenchJack](https://arxiv.org/abs/2605.12673)

**背景**：AI Agent 基准测试（如 SWE-bench、Terminal-Bench 等）是评估 Agent 能力的重要工具，但基准测试本身可能存在设计缺陷，导致分数不能真实反映 Agent 的实际能力。

**原来的问题**：社区中已有讨论指出，部分 Agent 基准测试存在“作弊”空间——模型可以通过记忆答案、利用测试集泄露等方式获得虚高分数。

**这次发生了什么**：arXiv 上的一篇论文提出了 **BenchJack**，一个系统审计 AI Agent 基准测试的工具。**研究信号不等于产品落地。**

**具体变化**：论文未提供详细摘要，但从标题和领域判断，BenchJack 旨在发现基准测试中的漏洞和设计缺陷，帮助社区构建更可靠的评测体系。

**为什么重要**：基准测试的可信度直接影响 Agent 领域的研发方向。如果基准测试存在系统性漏洞，可能导致社区资源被误导。BenchJack 的出现有助于提升 Agent 评测的严谨性。

**建议动作**：关注 Agent 基准测试的研究者和开发者可以阅读该论文，了解当前基准测试的潜在问题。对于普通用户，这是一个提醒：不要盲目相信基准测试分数，应结合实际场景评估 Agent 能力。

## 今日建议动作

1. **检查 GitHub Copilot 设置**：如果你使用 Copilot Cloud Agent，切换到 Auto 模型选择模式，享受 10% 折扣和不受速率限制的福利。
2. **测试 llama.cpp b9180**：如果你使用 llama.cpp 进行本地推理并启用了 speculative decoding，升级到 b9180 并测试 MTP 带来的性能提升。
3. **评估 Qwen3.6-35B-A3B**：关注 Agent 工作流的开发者可以下载该模型，在 Terminal-Bench 或自己的终端任务上测试其表现。
4. **阅读 Agent 安全论文**：如果你正在开发 Agent 平台或使用第三方技能，建议阅读 AgentTrap 论文，了解如何评估和防御第三方技能风险。
5. **归档硬件对比数据**：社区实测的 Strix Halo、RTX 3090、RTX 5070 对比数据值得保存，作为未来硬件选型的参考。
6. **暂时忽略**：BenchJack 论文目前信息有限，可暂时归档，等待后续更新。

## 附录：候选来源索引

| 编号 | 标题 | 来源等级 | 来源名称 | 链接 |
|------|------|----------|----------|------|
| 1 | Copilot cloud agent supports auto model selection | 官方确认 | GitHub Changelog | [链接](https://github.blog/changelog/2026-05-14-copilot-cloud-agent-supports-auto-model-selection) |
| 2 | 社区实测：Strix Halo、RTX 3090与RTX 5070推理性能对比 | 技术社区 | Reddit r/LocalLLaMA | [链接](https://www.reddit.com/r/LocalLLaMA/comments/1tf9iyk/ran_the_same_models_across_strix_halo_rtx_3090) |
| 3 | AgentTrap：第三方Agent技能运行时信任失效的测量基准 | 早期信号 | arXiv cs.AI | [链接](https://arxiv.org/abs/2605.13940) |
| 4 | Do Androids Dream of Breaking the Game? Systematically Auditing AI Agent Benchmarks with BenchJack | 早期信号 | arXiv cs.AI | [链接](https://arxiv.org/abs/2605.12673) |
| 5 | Qwen3.6-35B-A3B登上Terminal-Bench 2.0排行榜，超越Gemini 2.5 Pro | 技术社区 | Reddit r/LocalLLaMA | [链接](https://www.reddit.com/r/LocalLLaMA/comments/1temio0/qwen3635ba3b_and_9b_are_officially_on_the_public) |
| 6 | internlm/Intern-S2-Preview · Hugging Face | 技术社区 | Reddit r/LocalLLaMA | [链接](https://www.reddit.com/r/LocalLLaMA/comments/1tdrw0s/internlminterns2preview_hugging_face) |
| 7 | llama.cpp b9180 发布：新增 MTP（多 token 预测）支持，提升 speculative decoding 效率 | 官方确认 | llama.cpp | [链接](https://github.com/ggml-org/llama.cpp/releases/tag/b9180) |
