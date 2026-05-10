# AI 新闻模型解读日报｜2026-05-10

## 今日一句话
今日技术社区围绕 **llama.cpp** 生态密集更新：多个版本连续发布，重点优化 Intel GPU 推理性能并新增 Sarvam MoE 架构支持；社区实测显示 Qwen3.6 35B 模型在 12GB 显存上可达 80 tok/s，BeeLlama.cpp 分支在 3090 上实现 135 tps 峰值。OpenAI 发布 Codex 安全运行实践，为 Agent 部署提供官方安全参考。端侧 AI 方面，手写 OpenCL 内核让 2020 年中端安卓手机跑起了小语言模型。

## 工具链更新汇总

### Allen AI 提出 EMO 预训练方法：让混合专家模型“自然长出”模块化能力
[16. Allen AI提出EMO预训练方法：通过混合专家模型实现涌现模块化](https://huggingface.co/blog/allenai/emo)

**背景**：当前大语言模型（LLM）通常是“大一统”的——一个模型处理所有任务，但实际应用中往往只需要其中一部分能力（比如只做代码生成或数学推理）。混合专家模型（MoE）理论上可以通过激活不同“专家”来按需调用能力，但实践中仍需要加载全部参数才能正常工作。

**这次发生了什么**：Allen AI（AI2）在 Hugging Face 博客上发布了 **EMO** 方法，这是一种端到端的预训练方式，让 MoE 模型的模块化结构直接从数据中“涌现”出来，而不依赖人工预设的专家分工规则。EMO 模型在特定任务上只需激活 12.5% 的专家就能保持接近全模型性能，同时全量使用时仍可作为通用模型工作。

**为什么重要**：模块化是提升模型可解释性和部署效率的关键方向。如果 EMO 方法成熟，未来用户可能只需加载与任务相关的“小模块”即可运行，大幅降低推理成本和内存占用。**但请注意**：博客未提供详细的量化实验结果或与现有方法的对比，目前仍处于早期研究阶段，不等于已经产品化。

## Agent / 编程工具趋势

### OpenAI 发布 Codex 安全运行实践：沙箱、审批、网络策略与代理原生遥测
[1. OpenAI 发布 Codex 安全运行实践：沙箱、审批、网络策略与代理原生遥测](https://openai.com/index/running-codex-safely)

**背景**：Codex 是 OpenAI 的 AI 编码代理（coding agent），能够自主编写和修改代码。随着 Agent 越来越多地直接操作代码库和基础设施，安全问题成为企业采用的核心障碍——一个错误的 Agent 操作可能导致数据泄露或系统损坏。

**这次发生了什么**：OpenAI 官方详细介绍了如何安全运行 Codex，核心措施包括：
- **沙箱隔离**：Agent 在隔离环境中执行，限制对主机系统的访问。
- **操作审批**：关键操作（如写入文件、执行命令）需要人工确认（HITL，人在回路中）。
- **网络策略**：限制 Agent 可以访问的网络资源，防止数据外泄。
- **代理原生遥测**：内置监控和日志系统，追踪 Agent 的每一步操作。

**为什么重要**：这是 OpenAI 首次系统性地公开 Agent 安全部署的官方参考，直接影响了所有使用 AI 编码代理的开发者和企业。对于正在评估或已部署 Codex 的团队，这些实践是必须了解的安全基线。

**建议动作**：如果你的团队正在使用或计划使用 AI 编码代理，建议仔细阅读原文，对照检查自己的安全策略是否覆盖了沙箱、审批和网络隔离。

### GitHub Copilot Cloud Agent 支持更灵活的 Secrets 和 Variables 配置
[4. GitHub Copilot Cloud Agent 支持更灵活的 Secrets 和 Variables 配置](https://github.blog/changelog/2026-05-08-more-flexible-secrets-and-variables-for-copilot-cloud-agent)

**背景**：GitHub Copilot Cloud Agent 是一个在后台运行的编码代理，它使用 GitHub Actions 作为运行环境。为了让 Agent 访问私有资源（如内部包注册表）或配置 MCP 服务器（让 Agent 连接外部工具和数据源的协议），需要传递 secrets（敏感信息）和 variables（变量）。

**原来的问题**：之前这些配置必须逐个仓库设置，在仓库的 Actions 设置下的 copilot 环境中操作。跨仓库共享配置（如一个通用的内部包注册令牌）非常麻烦。

**这次发生了什么**：GitHub 为 Copilot Cloud Agent 新增了独立的“Agents”类型的 secrets 和 variables，与现有的“Actions”、“Codespaces”、“Dependabot”类型并列。现在可以在组织级别配置并跨仓库共享，也可以在仓库设置中独立管理 Agent 的配置。

**为什么重要**：对于大规模使用 Copilot Cloud Agent 的团队，此更新显著简化了配置管理，提升了安全性和灵活性。

### GitHub Copilot 用量指标 API 新增代码审查评论类型细分
[5. GitHub Copilot 用量指标 API 新增代码审查评论类型细分](https://github.blog/changelog/2026-05-08-copilot-code-review-comment-types-now-in-usage-metrics-api)

**背景**：GitHub Copilot 的代码审查功能会自动在 PR 中生成行级审查评论。之前企业用户只能看到总体的建议数量，无法区分这些建议属于什么类型。

**这次发生了什么**：Copilot 用量指标 API 新增了 `copilot_suggestions_by_comment_type` 字段，可以按评论类型（如 security、bug_risk）查看 Copilot 生成的建议数量和开发者实际采纳的数量。目前支持企业和组织级别的单日和 28 天滚动报告，暂不支持仓库级别。

**为什么重要**：对于需要精细分析 Copilot 代码审查效果的团队，此 API 扩展提供了更细粒度的数据，可以判断 Copilot 在哪些类型的审查上最有价值。

### Claude Code 团队成员建议：用 HTML 替代 Markdown 作为 AI 输出格式
[3. Claude Code团队成员建议：用HTML替代Markdown作为AI输出格式](https://simonwillison.net/2026/May/8/unreasonable-effectiveness-of-html)

**背景**：自 GPT-4 时代以来，Markdown 因其 token 效率高（比 HTML 占用更少的 token 配额）成为 AI 输出的默认格式。但 Anthropic 的 Claude Code 团队成员 Thariq Shihipar 提出了不同的看法。

**这次发生了什么**：Shihipar 通过多个示例展示了 HTML 输出的优势：可以嵌入 SVG 图表、交互式小部件、页面导航等，让信息呈现更丰富、更易导航。他建议在提示词中要求 Claude 以 HTML 格式输出，例如“帮我审查这个 PR，创建一个 HTML 产物来描述它”。

**为什么重要**：随着模型上下文窗口的扩大（不再受 8K token 限制），HTML 的 token 开销不再是主要障碍。这一建议可能改变开发者与 AI 编码工具的交互方式，从“纯文本输出”转向“富媒体输出”。**注意**：这是社区讨论，不等于官方推荐。

### ESP32-S3 机器人协作项目：基于 ArUco 标记的视觉定位原型
[8. ESP32-S3机器人协作项目：基于ArUco标记的视觉定位原型](https://www.reddit.com/r/esp32/comments/1t7f255/esp32s3_robots_with_onboard_camera_aruco_coop)

**背景**：该项目旨在构建一个小型机器人车队，每个机器人有不同的“感官”（一个只能看、一个只能听、一个只有接近感应），通过共享信息实现协作游戏。

**这次发生了什么**：目前项目处于早期阶段，作者使用 XIAO ESP32-S3 作为机器人主控，通过 WiFi 传输摄像头画面到 PC 进行 ArUco 标记检测，实现定位。尚未涉及协作策略的实现。

**为什么重要**：展示了低成本边缘 AI 硬件在机器人协作中的可行性，但当前阶段信息有限，仅适合作为灵感参考。**注意**：社区讨论，结果可能受测试条件和硬件环境影响。

## 开源项目 Release 汇总

### llama.cpp 连续多版本发布：聚焦 Intel GPU 性能优化与 Sarvam MoE 支持
llama.cpp（高性能大模型推理服务框架）今日密集发布了多个版本，主要围绕 SYCL 后端（Intel GPU 支持）的性能优化和新模型架构支持。

#### b9093：新增 Sarvam MoE 架构支持
[14. llama.cpp b9093 发布：新增 Sarvam MoE 架构支持](https://github.com/ggml-org/llama.cpp/releases/tag/b9093)

**背景**：Sarvam 是印度 AI 公司开发的混合专家（MoE）模型系列，包括 30B（2.4B 活跃参数）和 105B（10.3B 活跃参数）两个版本。Sarvam-105B 在 Agent 和推理基准上接近前沿闭源模型。

**这次发生了什么**：b9093 版本正式合并了 Sarvam MoE 架构支持（PR #20275），并提供了 macOS、Linux、iOS 等多平台二进制包。**注意**：原文未明确说明从哪个版本升级而来。

**为什么重要**：Sarvam-105B 在 Agent 任务上表现突出，llama.cpp 支持后可在本地部署，对 Agent 工作流和边缘推理有实际价值。

#### b9088：为 SYCL 后端添加 BF16 支持，修复 Intel GPU 性能回退
[15. llama.cpp b9088：为 SYCL 后端 GET_ROWS 操作添加 BF16 支持，修复 Intel GPU 性能回退](https://github.com/ggml-org/llama.cpp/releases/tag/b9088)

**背景**：SYCL 是 llama.cpp 支持 Intel GPU 的后端。某些模型（如 Gemma4）使用 BF16 格式的嵌入张量，之前 SYCL 后端不支持 BF16 的 GET_ROWS 操作，导致这些操作回退到 CPU，每次 token 生成都需要完整的 GPU 到 CPU 张量传输，造成严重性能下降。

**这次发生了什么**：b9088 版本为 SYCL 后端的 GET_ROWS 操作添加了 BF16 数据类型支持，修复了此性能回退问题。

**为什么重要**：对于使用 Intel GPU 运行 Gemma4 等 BF16 嵌入模型的用户，此修复可显著提升推理性能。

#### b9089：优化 SYCL 后端 Flash Attention 内存分配
[17. llama.cpp b9089 发布：优化 SYCL 后端 Flash Attention 内存分配](https://github.com/ggml-org/llama.cpp/releases/tag/b9089)

**背景**：Flash Attention 是一种高效注意力机制实现，但在 SYCL 后端上存在内存分配开销问题。

**这次发生了什么**：b9089 版本通过重构代码，将相关函数移至独立文件，减少了 Flash Attention 过程中的内存分配开销。原文未给出明确量化结果。

#### b9087：SYCL 后端优化 Q5_K/Q8_0 量化路径
[18. llama.cpp b9087：SYCL后端优化Q5_K/Q8_0量化路径](https://github.com/ggml-org/llama.cpp/releases/tag/b9087)

**背景**：Q5_K 和 Q8_0 是 llama.cpp 中常用的模型量化格式，用于减少模型大小和加速推理。

**这次发生了什么**：b9087 版本为 SYCL 后端添加了 Q5_K 和 Q8_0 量化格式的 reorder MMVQ/dequant 路径优化，旨在提升 Intel GPU 上的推理性能。原文未给出明确量化结果。

**升级建议**：如果你使用 Intel GPU 运行 llama.cpp，建议升级到 b9088 及以上版本以获得 BF16 支持和性能优化。如果你关注 Sarvam MoE 模型，b9093 是必须升级的版本。

### BeeLlama.cpp：llama.cpp 高性能分支，单卡 3090 上 Qwen 3.6 27B 达 135 tps
[11. BeeLlama.cpp：llama.cpp高性能分支，支持DFlash推测解码与TurboQuant，Qwen 3.6 27B Q5在3090上达135 tps](https://www.reddit.com/r/LocalLLaMA/comments/1t88zvv/beellamacpp_advanced_dflash_turboquant_with)

**背景**：开发者 Anbeeld 需要一个 Windows 友好的推理方案，能在单张 RTX 3090 上运行 Qwen 3.6 27B Q5 模型，同时支持推测解码、高上下文窗口和多模态。

**这次发生了什么**：Anbeeld 发布了 **BeeLlama.cpp**，一个性能优化的 llama.cpp 分支，集成了：
- **DFlash 推测解码**：通过小模型生成草稿，大模型验证，加速推理。
- **自适应草案控制**：动态调整草稿生成策略。
- **TurboQuant / TCQ KV 缓存压缩**：减少 KV 缓存内存占用。
- **推理循环保护**：防止异常情况导致崩溃。

在单张 RTX 3090 上运行 Qwen 3.6 27B Q5 模型，实现 200K 上下文，峰值 135 tps（比基线快 2-3 倍）。

**为什么重要**：该分支针对单卡高上下文推理场景有显著性能提升，对本地部署和边缘 AI 开发者具有实用参考价值。**注意**：社区讨论，结果可能受测试条件和硬件环境影响。

### 社区实测：Qwen3.6 35B A3B 在 12GB VRAM 上实现 80 tok/s 和 128K 上下文
[10. 社区实测：Qwen3.6 35B A3B在12GB VRAM上实现80 tok/s和128K上下文](https://www.reddit.com/r/LocalLLaMA/comments/1t82zxv/80_toksec_and_128k_context_on_12gb_vram_with)

**背景**：Qwen3.6 35B A3B 是一个混合专家模型，总参数 35B，但每次推理只激活 3B 参数。对于只有 12GB VRAM 的消费级 GPU（如 RTX 4070 Super），运行大模型一直是个挑战。

**这次发生了什么**：Reddit 用户分享使用最新 llama.cpp MTP 分支（多 token 预测），在 RTX 4070 Super 12GB 上运行 Qwen3.6 35B A3B GGUF 模型，达到 80+ tok/s 生成速度，80% 以上草稿接受率，支持 128K 上下文。

**为什么重要**：该配置展示了在消费级 GPU 上运行大模型的高效可能性，对本地 AI 开发者和边缘部署场景有直接参考意义。**注意**：社区讨论，结果可能受测试条件和硬件环境影响。

### Open WebUI v0.9.3：新增语音模式静音控制与多项性能优化
[12. Open WebUI v0.9.3 发布：新增语音模式静音控制与多项性能优化](https://github.com/open-webui/open-webui/releases/tag/v0.9.3)

**背景**：Open WebUI 是一个开源的 AI 聊天界面，支持多种后端模型。

**这次发生了什么**：v0.9.3 主要新增了语音模式静音切换（快捷键 M），防止背景噪音意外中断；优化了提示词列表和聊天历史加载速度；在对话菜单中增加了直接删除功能。

**为什么重要**：语音模式静音控制和性能优化直接提升日常使用体验，对 Open WebUI 用户有实际价值。

### 手写 OpenCL 内核在 Adreno 6xx GPU 上运行小语言模型：2020 年中端安卓手机实测
[9. 手写OpenCL内核在Adreno 6xx GPU上运行小语言模型：2020年中端安卓手机实测](https://www.reddit.com/r/embedded/comments/1t83ung/handwritten_opencl_kernels_for_llm_inference_on)

**背景**：中端安卓手机的 Adreno 6xx GPU（Snapdragon 6/7 系列）处于一个尴尬的位置：太老无法使用厂商的 NPU SDK，而开源框架（llama.cpp、MLC、MNN）要么不支持，要么回退到 CPU。llama.cpp 官方文档明确表示“A6x 手机 GPU 可能因驱动和编译器过旧而不被支持”。

**这次发生了什么**：作者手写了 OpenCL 内核，在 Adreno 6xx GPU 上成功运行了 6 个小语言模型（如 SmolLM2-135M、Mamba2-130M 等），并给出了 fp16、贪心解码下的 token/s 性能数据。原文给出了具体的性能数字，但未在此处列出。

**为什么重要**：该工作填补了中端手机 GPU 推理的空白，为端侧 AI 部署提供了低成本、可复现的替代方案。**注意**：社区讨论，结果可能受测试条件和硬件环境影响。

### NVIDIA 发布 CUDA-Oxide 0.1：实验性 Rust 到 CUDA 编译器
[13. NVIDIA 发布 CUDA-Oxide 0.1：实验性 Rust 到 CUDA 编译器](https://www.phoronix.com/news/NVIDIA-CUDA-Oxide-0.1)

**背景**：CUDA 是 NVIDIA GPU 的编程框架，传统上使用 C/C++ 编写。Rust 因其内存安全特性在系统编程领域越来越受欢迎。

**这次发生了什么**：NVIDIA Labs 发布了 CUDA-Oxide 0.1 版本，这是一个将 Rust 代码编译为 CUDA 内核的实验性编译器。目前版本号 0.1，处于早期阶段。

**为什么重要**：如果成熟，可能改变 GPU 编程生态，让 Rust 开发者也能直接编写 GPU 内核。但 0.1 版本表明距离可用还有相当距离。**注意**：此信息来自 Phoronix，原文未提供官方确认链接，建议保持关注但暂不投入。

## 企业应用 / 商业化信号

（今日候选新闻中企业应用 / 商业化信号较少，主要 Agent 相关更新已在“Agent / 编程工具趋势”中覆盖。）

## 算力 / 半导体观察

### llama.cpp 连续优化 Intel GPU 推理性能
今日多个 llama.cpp 版本（b9087、b9088、b9089）聚焦于 SYCL 后端（Intel GPU 支持）的性能优化，包括 BF16 支持、Flash Attention 内存分配优化和 Q5_K/Q8_0 量化路径优化。这些更新位于**推理**环节，针对的是 Intel GPU 这一相对小众但重要的推理硬件生态。对于使用 Intel GPU 进行本地推理的用户，建议升级到最新版本。

### 社区实测：消费级 GPU 上的高效推理
[10. 社区实测：Qwen3.6 35B A3B在12GB VRAM上实现80 tok/s和128K上下文](https://www.reddit.com/r/LocalLLaMA/comments/1t82zxv/80_toksec_and_128k_context_on_12gb_vram_with) 和 [11. BeeLlama.cpp：llama.cpp高性能分支](https://www.reddit.com/r/LocalLLaMA/comments/1t88zvv/beellamacpp_advanced_dflash_turboquant_with) 展示了在消费级 GPU（RTX 4070 Super 12GB、RTX 3090）上运行大模型的高效可能性。这些结果对评估本地推理的硬件需求有直接参考意义。

## 嵌入式 AI / 物联网 / Edge AI

### 用 ESP32 将 60 美元咖啡机改造成自托管 Web 应用
[6. 用ESP32将60美元咖啡机改造成自托管Web应用](https://www.reddit.com/r/arduino/comments/1t8am0p/i_turned_a_60_espresso_machine_into_a_selfhosted)

**背景**：ESP32 是乐鑫科技推出的低成本 Wi-Fi/蓝牙双模微控制器，广泛应用于物联网项目。

**这次发生了什么**：作者用 ESP32、热电偶、SSR（固态继电器）和 OLED 显示屏，将一台 60 美元的咖啡机改造成可通过手机 Web 界面控制的设备。实现了 ±0.5°C 的锅炉温度控制精度，支持冲泡和蒸汽模式切换。

**为什么重要**：对于嵌入式 AI 或边缘计算爱好者，该项目展示了低成本设备智能化的可能性。但缺乏与 AI/Agent 工作流的直接关联。

### 社区 DIY：ESP32-C3+NFC+电子纸的信用卡大小智能卡原型
[7. 社区DIY：ESP32-C3+NFC+电子纸的信用卡大小智能卡原型](https://www.reddit.com/r/esp32/comments/1t7gn4c/an_actually_creditcard_sized_smartcard_with)

**背景**：ESP32-C3 是乐鑫科技推出的 RISC-V 架构 Wi-Fi/蓝牙微控制器，功耗更低。

**这次发生了什么**：作者分享了制作信用卡大小智能卡的原型，集成了 ESP32-C3、NFC 和电子纸显示屏，总厚度约 1mm。目前原型脆弱且外观粗糙，但正在改进。

**为什么重要**：对于关注端侧 AI 和嵌入式智能硬件的读者，这是一个有趣的硬件集成案例，但距离实用还有距离。

## 前沿研究观察

### Allen AI 提出 EMO 预训练方法
[16. Allen AI提出EMO预训练方法：通过混合专家模型实现涌现模块化](https://huggingface.co/blog/allenai/emo)

已在“工具链更新汇总”中详细展开。**重申**：这是研究信号，不等于产品落地。博客未提供详细的量化实验结果。

## 今日建议动作

1. **检查 Agent 安全策略**：如果你正在使用或计划使用 AI 编码代理（如 Codex、Copilot Cloud Agent），建议阅读 [OpenAI 的 Codex 安全实践](https://openai.com/index/running-codex-safely)，对照检查自己的沙箱、审批和网络策略。

2. **升级 llama.cpp**：如果你使用 Intel GPU 运行 llama.cpp，建议升级到 b9088 及以上版本以获得 BF16 支持和性能优化。如果你关注 Sarvam MoE 模型，b9093 是必须升级的版本。

3. **试用 BeeLlama.cpp**：如果你有单张 RTX 3090 或类似显卡，且需要高上下文窗口推理，可以关注 [BeeLlama.cpp](https://www.reddit.com/r/LocalLLaMA/comments/1t88zvv/beellamacpp_advanced_dflash_turboquant_with) 分支。

4. **关注 Sarvam MoE 模型**：Sarvam-105B 在 Agent 任务上表现突出，llama.cpp 支持后可在本地部署，建议关注后续社区评测。

5. **归档 CUDA-Oxide 0.1**：NVIDIA 的实验性 Rust 到 CUDA 编译器目前版本号 0.1，距离可用还有距离，建议保持关注但暂不投入。

6. **暂时忽略**：ESP32 咖啡机改造和智能卡原型项目属于硬件 DIY 爱好者的灵感参考，与 AI/Agent 工作流无直接关联，非嵌入式开发者可暂时忽略。

## 附录：候选来源索引

| 编号 | 标题 | 来源等级 | 来源名称 | 链接 |
|------|------|----------|----------|------|
| 1 | OpenAI 发布 Codex 安全运行实践：沙箱、审批、网络策略与代理原生遥测 | 官方确认 | OpenAI News | [链接](https://openai.com/index/running-codex-safely) |
| 2 | llama.cpp 新增 Sarvam MoE 架构支持：Sarvam-30B/105B 模型可本地推理 | 技术社区 | Reddit r/LocalLLaMA | [链接](https://www.reddit.com/r/LocalLLaMA/comments/1t8db1j/model_add_sarvam_moe_architecture_support_by) |
| 3 | Claude Code团队成员建议：用HTML替代Markdown作为AI输出格式 | 技术社区 | Simon Willison | [链接](https://simonwillison.net/2026/May/8/unreasonable-effectiveness-of-html) |
| 4 | GitHub Copilot Cloud Agent 支持更灵活的 Secrets 和 Variables 配置 | 官方确认 | GitHub Changelog | [链接](https://github.blog/changelog/2026-05-08-more-flexible-secrets-and-variables-for-copilot-cloud-agent) |
| 5 | GitHub Copilot 用量指标 API 新增代码审查评论类型细分 | 官方确认 | GitHub Changelog | [链接](https://github.blog/changelog/2026-05-08-copilot-code-review-comment-types-now-in-usage-metrics-api) |
| 6 | 用ESP32将60美元咖啡机改造成自托管Web应用 | 技术社区 | Reddit r/arduino | [链接](https://www.reddit.com/r/arduino/comments/1t8am0p/i_turned_a_60_espresso_machine_into_a_selfhosted) |
| 7 | 社区DIY：ESP32-C3+NFC+电子纸的信用卡大小智能卡原型 | 技术社区 | Reddit r/esp32 | [链接](https://www.reddit.com/r/esp32/comments/1t7gn4c/an_actually_creditcard_sized_smartcard_with) |
| 8 | ESP32-S3机器人协作项目：基于ArUco标记的视觉定位原型 | 技术社区 | Reddit r/esp32 | [链接](https://www.reddit.com/r/esp32/comments/1t7f255/esp32s3_robots_with_onboard_camera_aruco_coop) |
| 9 | 手写OpenCL内核在Adreno 6xx GPU上运行小语言模型：2020年中端安卓手机实测 | 技术社区 | Reddit r/embedded | [链接](https://www.reddit.com/r/embedded/comments/1t83ung/handwritten_opencl_kernels_for_llm_inference_on) |
| 10 | 社区实测：Qwen3.6 35B A3B在12GB VRAM上实现80 tok/s和128K上下文 | 技术社区 | Reddit r/LocalLLaMA | [链接](https://www.reddit.com/r/LocalLLaMA/comments/1t82zxv/80_toksec_and_128k_context_on_12gb_vram_with) |
| 11 | BeeLlama.cpp：llama.cpp高性能分支，支持DFlash推测解码与TurboQuant，Qwen 3.6 27B Q5在3090上达135 tps | 技术社区 | Reddit r/LocalLLaMA | [链接](https://www.reddit.com/r/LocalLLaMA/comments/1t88zvv/beellamacpp_advanced_dflash_turboquant_with) |
| 12 | Open WebUI v0.9.3 发布：新增语音模式静音控制与多项性能优化 | 官方确认 | Open WebUI | [链接](https://github.com/open-webui/open-webui/releases/tag/v0.9.3) |
| 13 | NVIDIA 发布 CUDA-Oxide 0.1：实验性 Rust 到 CUDA 编译器 | 待验证 | Phoronix | [链接](https://www.phoronix.com/news/NVIDIA-CUDA-Oxide-0.1) |
| 14 | llama.cpp b9093 发布：新增 Sarvam MoE 架构支持 | 官方确认 | llama.cpp | [链接](https://github.com/ggml-org/llama.cpp/releases/tag/b9093) |
| 15 | llama.cpp b9088：为 SYCL 后端 GET_ROWS 操作添加 BF16 支持，修复 Intel GPU 性能回退 | 官方确认 | llama.cpp | [链接](https://github.com/ggml-org/llama.cpp/releases/tag/b9088) |
| 16 | Allen AI提出EMO预训练方法：通过混合专家模型实现涌现模块化 | 官方确认 | Hugging Face Blog | [链接](https://huggingface.co/blog/allenai/emo) |
| 17 | llama.cpp b9089 发布：优化 SYCL 后端 Flash Attention 内存分配 | 官方确认 | llama.cpp | [链接](https://github.com/ggml-org/llama.cpp/releases/tag/b9089) |
| 18 | llama.cpp b9087：SYCL后端优化Q5_K/Q8_0量化路径 | 官方确认 | llama.cpp | [链接](https://github.com/ggml-org/llama.cpp/releases/tag/b9087) |
