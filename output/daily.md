# AI 早报｜2026-05-03

## 今日一句话

今天共抓取 1973 条信息，筛选出 Top 20 条。优先展示官方确认来源，其次是技术社区热议和早期信号。

## 今日优先阅读

### 1. Ollama: v0.23.0

- 来源等级：官方确认
- 来源：Ollama
- 类型：GitHub Release
- 发布时间：2026-05-03 03:34
- 原文链接：https://github.com/ollama/ollama/releases/tag/v0.23.0
- 命中关键词：Claude, Claude Code
- 规则分数：83
- 原文摘录：
  > ## Claude Desktop with Ollama Launch Claude Desktop is now supported with Ollama Launch. Both Claude Cowork and Claude Code are supported within the Claude Desktop App. ``` ollama launch claude-desktop ``` Claude Code on the terminal can still be accessed through the CLI with: ``` ollama launch claude ``` ## What's Changed * Launch Claude Desktop with `ollama launch claude` * The Ollama app now surfaces featured mod...

- 阅读提醒：
  这是官方来源，可信度较高。

---

### 2. llama.cpp: b9010

- 来源等级：官方确认
- 来源：llama.cpp
- 类型：GitHub Release
- 发布时间：2026-05-02 22:08
- 原文链接：https://github.com/ggml-org/llama.cpp/releases/tag/b9010
- 命中关键词：CUDA, GitHub, GPU, Llama
- 规则分数：80
- 原文摘录：
  > fix: CUDA device PCI bus ID de-dupe OOMing (ignoring other 3 gpus entirely) (#22533) * fix: CUDA device PCI bus ID detection for multi-GPU de-dupe * HIP, MUSA macros --------- Co-authored-by: Johannes Gäßler **macOS/iOS:** - [macOS Apple Silicon (arm64)](https://github.com/ggml-org/llama.cpp/releases/download/b9010/llama-b9010-bin-macos-arm64.tar.gz) - [macOS Apple Silicon (arm64, KleidiAI enabled)](https://github.c...

- 阅读提醒：
  这是官方来源，可信度较高。

---

## 技术社区热议

### 3. I implemented meta paper [P]

- 来源等级：技术社区
- 来源：Reddit r/MachineLearning
- 类型：RSS
- 发布时间：2026-05-02 14:37
- 原文链接：https://www.reddit.com/r/MachineLearning/comments/1t1rni9/i_implemented_meta_paper_p
- 命中关键词：benchmark, Gemini, GitHub, Meta AI
- 规则分数：53
- 原文摘录：
  > github link : genji970/Scaling-Test-Time-Compute-for-Agentic-Coding-: paper implementation of Meta Ai paper link : https://arxiv.org/abs/2604.16529v1 As far as I know, there is no public implementation of this paper yet, so I built a minimal research implementation of the core PDR+RTV pipeline. I made project to run gemini-3.1-pro model and test on SWE benchmark(In paper, there is one more benchmark and used models...

- 阅读提醒：
  这是社区讨论，不等于事实确认，需要结合原文判断。

---

### 4. GPT 5.5 just leaked its chain of thought to me in codex, and it looks like an idea from 5 months ago in this sub.

- 来源等级：技术社区
- 来源：Reddit r/LocalLLaMA
- 类型：RSS
- 发布时间：2026-05-03 01:35
- 原文链接：https://www.reddit.com/r/LocalLLaMA/comments/1t27wja/gpt_55_just_leaked_its_chain_of_thought_to_me_in
- 命中关键词：Codex, GPT
- 规则分数：50
- 原文摘录：
  > https://www.reddit.com/r/LocalLLaMA/comments/1p0lnlo/make_your_ai_talk_like_a_caveman_and_decrease/ In the middle of a project I'm working on, I got this output from GPT 5.5-medium via codex: Implemented the narrower fix in Homm3ImportUnitPreviewModelHook.cs? Need absolute path. Need know cwd absolute. v:... Use markdown. final with path. Need avoid bogus path. Use Homm3ImportUnitPreviewModelHook.cs? Format requires...

- 阅读提醒：
  这是社区讨论，不等于事实确认，需要结合原文判断。

---

### 5. Sightings

- 来源等级：技术社区
- 来源：Simon Willison
- 类型：RSS
- 发布时间：2026-05-02 17:26
- 原文链接：https://simonwillison.net/2026/May/2/sightings
- 命中关键词：Claude, Claude Code
- 规则分数：50
- 原文摘录：
  > /elsewhere/sightings/ I have a new camera (a Canon R6 Mark II) so I'm taking a lot more photos of birds. I share my best wildlife photos on iNaturalist , and based on yesterday's successful prototype I decided to add those to my blog. I built this feature on my phone using Claude Code for web, as an extension of my beats system for syndicating external content. Here's the PR and prompt. As with my other forms of inc...

- 阅读提醒：
  这是社区讨论，不等于事实确认，需要结合原文判断。

---

### 6. Qwen3.6-27B at 72 tok/s on RTX 3090 on Windows using native vLLM (no WSL, no Docker), portable launcher and installer

- 来源等级：技术社区
- 来源：Reddit r/LocalLLaMA
- 类型：RSS
- 发布时间：2026-05-02 08:12
- 原文链接：https://www.reddit.com/r/LocalLLaMA/comments/1t1judm/qwen3627b_at_72_toks_on_rtx_3090_on_windows_using
- 命中关键词：GitHub, GPU, open source
- 规则分数：47
- 原文摘录：
  > The angle here is native Windows, no WSL. Simple installation, open source, no telemetry. Not selling or promoting anything: https://github.com/devnen/qwen3.6-windows-server Numbers (RTX 3090, Windows 10): - 72 tok/s short prompt - 64.5 tok/s long prompt (~25k tokens) - 53.4 tok/s at 127k ctx (single GPU) - 160k ctx on PP=2 (2×3090 GPUs) Honestly, these aren't r/LocalLLaMA records. Community has hit 80–82 tok/s on a...

- 阅读提醒：
  这是社区讨论，不等于事实确认，需要结合原文判断。

---

### 7. [RELEASE] - Finally, my first TTS model is out! 🎙️ Flare-TTS 28M

- 来源等级：技术社区
- 来源：Reddit r/LocalLLaMA
- 类型：RSS
- 发布时间：2026-05-02 10:52
- 原文链接：https://www.reddit.com/r/LocalLLaMA/comments/1t1mmnd/release_finally_my_first_tts_model_is_out
- 命中关键词：GPU, release
- 规则分数：45
- 原文摘录：
  > Hey r/LocalLLaMA ! I am back with a new model, and it's something special today 😃 It's Flare-TTS 28M, my first text to speech (TTS) model trained completely from scratch on a single A6000 GPU for ~24 hours, ~300 epochs and the full LJSpeech dataset! Link to the HF model: https://huggingface.co/LH-Tech-AI/Flare-TTS-28M Example result: https://cdn-uploads.huggingface.co/production/uploads/697f2832c2c5e4daa93cece7/vluu...

- 阅读提醒：
  这是社区讨论，不等于事实确认，需要结合原文判断。

---

### 8. A Dark-Money Campaign Is Paying Influencers to Frame Chinese AI as a Threat

- 来源等级：技术社区
- 来源：Reddit r/LocalLLaMA
- 类型：RSS
- 发布时间：2026-05-02 06:35
- 原文链接：https://www.reddit.com/r/LocalLLaMA/comments/1t1i4yg/a_darkmoney_campaign_is_paying_influencers_to
- 命中关键词：funding, open source, OpenAI
- 规则分数：45
- 原文摘录：
  > Build American AI, a nonprofit linked to a super PAC bankrolled by executives at OpenAI and Andreessen Horowitz, is funding a campaign to spread pro-AI messaging and stoke fears about China. So Local LLM is important .... always! Need to support who giving us more Open source & weights. Last month, Half of the open models came from there only . submitted by /u/pmttyji [link] [comments]

- 阅读提醒：
  这是社区讨论，不等于事实确认，需要结合原文判断。

---

### 9. The agent harness belongs outside the sandbox

- 来源等级：技术社区
- 来源：Hacker News
- 类型：Hacker News
- 发布时间：2026-05-02 21:21
- 原文链接：https://www.mendral.com/blog/agent-harness-belongs-outside-sandbox
- HN 分数：85
- 命中关键词：Agent
- 规则分数：40
- 原文摘录：
  > HN points: 85. Comments: https://news.ycombinator.com/item?id=47990675

- 阅读提醒：
  这是社区讨论，不等于事实确认，需要结合原文判断。

---

### 10. Open Design: Use Your Coding Agent as a Design Engine

- 来源等级：技术社区
- 来源：Hacker News
- 类型：Hacker News
- 发布时间：2026-05-02 12:16
- 原文链接：https://github.com/nexu-io/open-design
- HN 分数：196
- 命中关键词：Agent
- 规则分数：40
- 原文摘录：
  > HN points: 196. Comments: https://news.ycombinator.com/item?id=47985750

- 阅读提醒：
  这是社区讨论，不等于事实确认，需要结合原文判断。

---

### 11. We are finally there: Qwen3.6-27B + agentic search; 95.7% SimpleQA on a single 3090, fully local

- 来源等级：技术社区
- 来源：Reddit r/LocalLLaMA
- 类型：RSS
- 发布时间：2026-05-02 11:21
- 原文链接：https://www.reddit.com/r/LocalLLaMA/comments/1t1n6o8/we_are_finally_there_qwen3627b_agentic_search_957
- 命中关键词：Agent
- 规则分数：40
- 原文摘录：
  > LDR maintainer here. Thanks to the strong support of r/LocalLLaMA community LDR got very far. I haven't reported in a while because I thought I was not ready for another prominent post in one of the leading outlets of Local LLM research. But I think the LDR community finally there again. I think it is finally time to report again. Setup RTX 3090, 24GB Ollama backend (qwen3.6:27b) LDR's langgraph_agent strategy — Lan...

- 阅读提醒：
  这是社区讨论，不等于事实确认，需要结合原文判断。

---

### 12. Kimi K2.6 just beat Claude, GPT-5.5, and Gemini in a coding challenge

- 来源等级：技术社区
- 来源：Hacker News
- 类型：Hacker News
- 发布时间：2026-05-03 04:05
- 原文链接：https://thinkpol.ca/2026/04/30/an-open-weights-chinese-model-just-beat-claude-gpt-5-5-and-gemini-in-a-programming-challenge
- HN 分数：98
- 命中关键词：Claude, Gemini, GPT, Kimi
- 规则分数：35
- 原文摘录：
  > HN points: 98. Comments: https://news.ycombinator.com/item?id=47993235

- 阅读提醒：
  这是社区讨论，不等于事实确认，需要结合原文判断。

---

### 13. CAISI releases evaluation report: DeepSeek V4 becomes the most powerful model in China, but still lags about 8 months behind the US frontier

- 来源等级：技术社区
- 来源：Reddit r/LocalLLaMA
- 类型：RSS
- 发布时间：2026-05-03 03:10
- 原文链接：https://www.reddit.com/r/LocalLLaMA/comments/1t29wx0/caisi_releases_evaluation_report_deepseek_v4
- 命中关键词：DeepSeek
- 规则分数：35
- 原文摘录：
  > https://preview.redd.it/pz8qeln0auyg1.png?width=1400&format=png&auto=webp&s=00ee5218734cfae4783d702411d63e3a4c6bbc60 https://preview.redd.it/hem9mad5auyg1.png?width=1184&format=png&auto=webp&s=2a26fec2b49204e64b44a78b30902ab80f7df53c https://preview.redd.it/s0d8qkd6auyg1.png?width=1400&format=png&auto=webp&s=1db808f9749870c8a06854e555b21259473546a6 https://preview.redd.it/gp6zy6k7auyg1.png?width=1400&format=png&auto...

- 阅读提醒：
  这是社区讨论，不等于事实确认，需要结合原文判断。

---

### 14. Open source does not imply open community

- 来源等级：技术社区
- 来源：Hacker News
- 类型：Hacker News
- 发布时间：2026-05-03 02:36
- 原文链接：https://blog.feld.me/posts/2026/04/open-source-does-not-imply-open-community
- HN 分数：108
- 命中关键词：open source
- 规则分数：35
- 原文摘录：
  > HN points: 108. Comments: https://news.ycombinator.com/item?id=47992772

- 阅读提醒：
  这是社区讨论，不等于事实确认，需要结合原文判断。

---

### 15. Local image generation on Mac: 10 models compared (SD 1.5 → Flux dev → Qwen-Image → Gemini)

- 来源等级：技术社区
- 来源：Reddit r/LocalLLaMA
- 类型：RSS
- 发布时间：2026-05-03 01:08
- 原文链接：https://www.reddit.com/r/LocalLLaMA/comments/1t27cf0/local_image_generation_on_mac_10_models_compared
- 命中关键词：Gemini, Qwen
- 规则分数：35
- 原文摘录：
  > Tested 10 image generation models on M1 Max 64GB for photorealism, text rendering, and cultural accuracy (Japanese/Asian content). Key findings: Qwen-Image Lightning (8-step distillation) beats the full model in quality while being 9x faster (10min vs 93min) Flux dev is the best local model for photorealism, but has strong English-centric bias (puts cilantro in ramen, turns izakayas into teahouses) Gemini nails kanj...

- 阅读提醒：
  这是社区讨论，不等于事实确认，需要结合原文判断。

---

### 16. I made a visualizer for Hugging Face models

- 来源等级：技术社区
- 来源：Reddit r/LocalLLaMA
- 类型：RSS
- 发布时间：2026-05-02 23:18
- 原文链接：https://www.reddit.com/r/LocalLLaMA/comments/1t24y4p/i_made_a_visualizer_for_hugging_face_models
- 命中关键词：Qwen
- 规则分数：35
- 原文摘录：
  > I built hfviewer.com , a small tool for visually exploring Hugging Face model architectures. You can paste a Hugging Face URL and get an interactive visualization of the architecture, which can make it easier to understand how different models are structured and compare them at a glance. Here is the recent Qwen3.6-27B model as an example: https://hfviewer.com/Qwen/Qwen3.6-27B And here is a side-by-side view of the G...

- 阅读提醒：
  这是社区讨论，不等于事实确认，需要结合原文判断。

---

### 17. The Claude Delusion: Richard Dawkins believes his AI chatbot is conscious

- 来源等级：技术社区
- 来源：Hacker News
- 类型：Hacker News
- 发布时间：2026-05-02 22:44
- 原文链接：https://www.dailygrail.com/2026/05/the-claude-delusion-richard-dawkins-believes-his-female-ai-chatbot-is-conscious
- HN 分数：62
- 命中关键词：Claude
- 规则分数：35
- 原文摘录：
  > HN points: 62. Comments: https://news.ycombinator.com/item?id=47991340

- 阅读提醒：
  这是社区讨论，不等于事实确认，需要结合原文判断。

---

### 18. Qwen/SAE-Res-Qwen3.5-27B-W80K-L0_100 · Hugging Face

- 来源等级：技术社区
- 来源：Reddit r/LocalLLaMA
- 类型：RSS
- 发布时间：2026-05-02 21:45
- 原文链接：https://www.reddit.com/r/LocalLLaMA/comments/1t22s9l/qwensaeresqwen3527bw80kl0_100_hugging_face
- 命中关键词：Qwen
- 规则分数：35
- 原文摘录：
  > I can't believe my luck! one of my next research steps was going to be on vector based model steering, and look at the gift that qwen gave us. You can learn about this here https://youtu.be/5L_tYKt2ENo submitted by /u/FaustAg [link] [comments]

- 阅读提醒：
  这是社区讨论，不等于事实确认，需要结合原文判断。

---

### 19. Clojurists Together – Q2 2026 Open Source Funding Announcement

- 来源等级：技术社区
- 来源：Hacker News
- 类型：Hacker News
- 发布时间：2026-05-02 21:34
- 原文链接：https://www.clojuriststogether.org/news/q2-2026-funding-announcement
- HN 分数：78
- 命中关键词：funding, open source
- 规则分数：35
- 原文摘录：
  > HN points: 78. Comments: https://news.ycombinator.com/item?id=47990789

- 阅读提醒：
  这是社区讨论，不等于事实确认，需要结合原文判断。

---

### 20. Ban phrases on llama.cpp with this script.

- 来源等级：技术社区
- 来源：Reddit r/LocalLLaMA
- 类型：RSS
- 发布时间：2026-05-02 21:22
- 原文链接：https://www.reddit.com/r/LocalLLaMA/comments/1t227hk/ban_phrases_on_llamacpp_with_this_script
- 命中关键词：GitHub, Llama
- 规则分数：35
- 原文摘录：
  > Check the README for setup instructions: https://github.com/BigStationW/llama-cpp-phrase-ban submitted by /u/Total-Resort-3120 [link] [comments]

- 阅读提醒：
  这是社区讨论，不等于事实确认，需要结合原文判断。

---

## 本系统的判断原则

本简报不把自动化摘要视为最终事实。
请优先查看官方来源和原文链接。
社区热议和早期信号仅用于发现趋势，不直接作为事实依据。
