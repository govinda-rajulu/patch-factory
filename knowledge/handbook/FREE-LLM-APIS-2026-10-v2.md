> Owner-supplied field guide, committed 8 Oct 2026 (packet W1) as written. Facts are dated
> 7 Oct 2026 and free tiers change monthly: re-check the provider's page before wiring anything.
> How this repository uses it: `docs/council/PROVIDERS.md` (8 Oct section) and
> `knowledge/handbook/FREE-LLM-AGENTS.md`.

# Free LLM access for repos: field guide v2 (double-checked 7 Oct 2026)
v2 = an independent fact-check pass (26 load-bearing claims re-verified on official pages) plus a gap hunt. Tags: **[official]** verified on provider docs; **[console]** offer exists, exact quota only shown in your dashboard; **[community]** forum/list claim only.
Free tiers change monthly. Re-check before wiring anything new.
## v2 changelog
- FIXED: LLM7 limits (old figures were wrong). Now: free token 60/min, 250/hour, 100K tokens/24h.
- FIXED: Groq Qwen model ID is `qwen/qwen3.8-27b`.
- FIXED: NVIDIA "credit system removed" has no official dated notice; reworded.
- FIXED: iFlow: built-in models stopped 17 Apr 2026; CLI still works with your own OpenAI-compatible key.
- CONFIRMED on official pages: GitHub Models retirement, Qwen OAuth end, Chutes, Together, Cerebras, OpenRouter, Gemini CLI quotas, Cloudflare, Kilo, Cohere, SambaNova, Scaleway, Alibaba, Fireworks, Jules, Oracle 2 OCPU/12 GB, Cloud Shell, Codespaces, Lightning, ZeroGPU, Modal, router repos, Copilot Free, Mistral Vibe.
- ADDED: Requesty, Reka ($10/month refreshing), Sarvam (India), OpenAI data-sharing tokens, IBM watsonx, Voyage + Jina (embeddings), China-gated options, Indian compute programs, more dead/not-free entries.
## 0. TL;DR stack for govinda-rajulu repos
1. **Primary agent in Actions:** `google-github-actions/run-gemini-cli` with `GEMINI_API_KEY` secret.
2. **Model-agnostic agent:** OpenCode (`opencode github install` / `opencode run`) on OpenRouter / NVIDIA / Groq.
3. **Router in front:** LiteLLM (mature) or FreeLLMAPI (built for free tiers). Fallback on 429/5xx.
4. **Add next (free, no card):** Groq, Requesty, Cloudflare Workers AI, Mistral, Kilo Gateway, Reka, Cohere trial.
5. **Worth $10 once:** OpenRouter credit purchase lifts free models from 50 to 1,000 requests/day.
6. **Never:** GitHub Models (retired), Qwen OAuth (dead), "free GPT/Claude proxy" sites or packages.
## 1. Recurring free tiers (no card)
| Provider | Best free models | Free limits | Base URL (OpenAI-style) | Notes | Conf |
|---|---|---|---|---|---|
| Google Gemini API (have) | Gemini Flash / Flash-Lite | per project, per model; see AI Studio. RPD resets midnight Pacific | `https://generativelanguage.googleapis.com/v1beta/openai/` | Free-tier data may improve Google products. Consumer app changes (9 Oct) are separate from API | official+console |
| OpenRouter (have) | rotating `:free` (Qwen, DeepSeek, Nemotron, gpt-oss, GLM, stealth) | 20 RPM, 50 RPD; 1,000 RPD after $10 lifetime purchase | `https://openrouter.ai/api/v1` | Upstream 429s even with quota left. Stealth models may log/train | official |
| NVIDIA NIM (have) | Kimi, DeepSeek, Nemotron, Llama, Qwen | up to 40 RPM most models; no per-token billing; no published RPD | `https://integrate.api.nvidia.com/v1` | Prototyping only. Logs prompts/outputs. No free RPM increases | official |
| **Groq** | `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`, Whisper | 30 RPM, 1,000 RPD, 8K TPM, 200K TPD each | `https://api.groq.com/openai/v1` | Fastest. Llama 3.x chat removed from free 16 Aug 2026 | official |
| **Requesty** (new) | Nemotron 3 Ultra/Super/Nano, Gemma 4 31B, Poolside Laguna, Mistral | 200 RPD, 20 RPM shared across free models | `https://router.requesty.ai/v1` | Gateway logs/analytics on; free lineup rotates | official |
| **Reka** (new) | Reka Flash / Core / Edge, Reka Research | $10 API credit refreshed monthly | `https://api.reka.ai/v1` | Check eligibility from India in dashboard | official |
| **Cloudflare Workers AI** | GLM-4.7 Flash, Gemma 4 26B, Nemotron 3 120B | 10,000 Neurons/day (00:00 UTC), 300 RPM | via AI Gateway | Kimi K2.6/K2.7, GLM-5.2 paid-only since 28 Jul 2026 | official |
| **Mistral (Free mode)** | Mistral Small 4, Ministral 3, Codestral | monthly allowance on your Limits page; no card | `https://api.mistral.ai/v1` | Shared with Vibe/Studio. Check training opt-out | console |
| **Kilo Gateway** | `kilo-auto/free`, Nemotron 3, MiniMax, StepFun | 200 req/hour per IP, anonymous OK | `https://api.kilo.ai/api/gateway` | Free routes may hit logging endpoints | official |
| **Cohere (trial)** | Command A+, Command A Reasoning, Aya, embed/rerank | 1,000 calls/month, 20 RPM chat | `https://api.cohere.com/compatibility/v1` | Evaluation only | official |
| **LLM7.io** | GLM / DeepSeek / Qwen routes | free token: 60/min, 250/hour, 100K tokens/24h | `https://api.llm7.io/v1` | Small; research gateway | official |
| **SambaNova** | DeepSeek-V3.1/3.2, Llama 3.3 70B, gpt-oss-120b | 20 RPM, **20 RPD**, 200K TPD | `https://api.sambanova.ai/v1` | Adding a card flips to paid | official |
| **Z.ai GLM Flash** | GLM-4.7-Flash, GLM-4.5-Flash, GLM-4.6V-Flash | $0/token; RPM unpublished | `https://api.z.ai/api/paas/v4` | Can be repriced anytime | official price |
| **Ollama Cloud** | gpt-oss cloud, qwen3-coder 480B cloud | small monthly allowance, 1 concurrent | `https://ollama.com/v1` | Claims zero retention | console |
| **Routeway** | rotating `:free` | 20 RPM, 200 RPD | `https://api.routeway.ai/v1` | Third-party gateway | official |
| **Inference.net** | free deployments only | 30 RPM | `https://api.inference.net/v1` | Most catalog paid | official |
| **OVHcloud AI Endpoints** | Qwen, gpt-oss, Llama, Mistral | anonymous 2 RPM per model per IP | `https://oai.endpoints.kepler.ai.cloud.ovh.net/v1` | Tests only | official |
| **IBM watsonx.ai** (new) | Granite + supported models | 300K tokens/month | IBM regional API/SDK (not OpenAI drop-in) | IBM Cloud signup | official |
| Aion Labs | Aion 2.x | 15 RPM, 20K tokens/day | `https://api.aionlabs.ai/v1` | Niche | official |
| Hugging Face Inference Providers | routed open models | $0.10/month | `https://router.huggingface.co/v1` | Smoke tests | official |
| Electron Hub (new) | `:free` pool | 10 Neutrinos/day, 5 RPM | `https://api.electronhub.ai/v1` | Small third party; charged even on failed calls | official/medium |
| AnyRouter (new) | `anyrouter/free` | ~10 RPD (docs conflict) | `https://anyrouter.dev/api/v1` | Unstable | medium |
| Pollinations | basic text | 1 req / 15 s anon | own API | Shared public service | official |
### Embeddings / RAG (not chat)
| Provider | Free | Base URL | Notes |
|---|---|---|---|
| **Voyage AI** | 200M tokens per current embedding model (one-time) | `https://api.voyageai.com/v1` | Batch API not covered | official |
| **Jina AI** | 10M tokens per key; `r.jina.ai` Reader keyless 20 RPM | `https://api.jina.ai/v1` | Non-commercial free key | official |
## 2. Conditional free tokens
| Offer | Amount | Catch | Conf |
|---|---|---|---|
| **OpenAI data-sharing program** | tiers 1-2: 250K flagship + 2.5M small tokens/day; tiers 3-5: 1M + 10M/day | Opt in to share prompts with OpenAI; needs positive balance (so paid account); only if banner appears | official |
| **Sarvam AI** (India) | ₹100 one-time; Startup Program 6-12 months credits | Indian models (Sarvam-105B/30B, speech, translation). `https://api.sarvam.ai/v1` | official |
## 3. One-time credits / trials
| Offer | Amount | Catch | Conf |
|---|---|---|---|
| Cerebras | $5, 30 days; 5 RPM / 1M TPD | Verified card required | official |
| Scaleway | 1M tokens + 60 min audio (GLM-5.2, DeepSeek V4 Flash, Qwen3.5-397B, Qwen3-Coder) | EU-hosted | official |
| Alibaba Model Studio (Singapore/Intl) | ~1M tokens per model, 90 days | Enable "Free Quota Only" or it bills | official |
| Fireworks | $1, 10 RPM | Prepaid | official |
| AI21 | $10 / 3 months | Native API | official |
| Novita | signup voucher (amount unpublished), $10 referral | Ignore third-party numbers | console |
| Nebius AI Builder Program | $400+, 90 days | Eligibility | official |
| Azure free account | $200 / 30 days (India listed) | Card + phone; Foundry inference eats credit | official |
| GCP | $300 / 90 days | No GPUs; can't pay AI Studio Gemini | official |
| AWS | $100 + up to $100, 6 months | Bedrock consumes credit, no free tier | official |
| Modal Starter | $30/month compute (recurring) | You deploy the model yourself | official |
## 4. China-gated (real-name ID; likely hard from India)
Tencent TokenHub/Hunyuan (1M tokens per model, 90 days, `https://api.hunyuan.cloud.tencent.com/v1`), Baidu Qianfan ERNIE-Speed/Lite/Tiny "long-term free" (`https://qianfan.baidubce.com/v2`), Volcengine Ark (per-model quota), Gitee AI (100 calls/day), SiliconFlow, ModelScope. Try only if signup accepts you.
## 5. Agents that run inside a GitHub repo
| Tool | Free | Headless in Actions? | Conf |
|---|---|---|---|
| **Gemini CLI + run-gemini-cli** | 1,000 req/day Google login; 250/day Flash-only with free API key | Yes, official Action | official |
| **OpenCode** | client free, BYO key; Zen rotating free models | Yes (`opencode github install`, `opencode run`) | official |
| **Mistral Vibe CLI** | Free mode | Yes (`vibe --prompt`) | official |
| **Codex CLI** | client free; custom `base_url` (LiteLLM/OpenRouter/FreeLLMAPI) | Yes (`codex exec`) | official |
| **iFlow CLI** | built-in models gone; works with your own key | Yes (BYO key only) | official |
| **Google Jules** | 15 tasks/day, 3 concurrent | No (hosted GitHub app, opens PRs) | official |
| **Amazon Q Developer app** | 50 agentic requests/month | Hosted app | official |
| **Copilot Free** | 2,000 completions/month + limited chat; CLI `copilot -p` | CLI yes; cloud agent paid-only | official |
| Claude Code Action | action free, inference not | Anthropic-protocol endpoints only | official |
## 6. Routers
| Project | Stars (7 Oct) | Why | Watch out |
|---|---|---|---|
| [LiteLLM](https://github.com/BerriAI/litellm) | ~60k, v1.104.0 (3 Oct) | Broadest providers incl. NIM/OpenRouter/Gemini; fallbacks, budgets, caching | Heavier |
| [FreeLLMAPI](https://github.com/tashfeenahmed/freellmapi) | ~23k, v0.13.4 (3 Oct) | Built for free tiers; quota tracking; Anthropic + Codex bridges | Community project |
| [New API](https://github.com/QuantumNous/new-api) | ~47k | Protocol conversion, key mgmt | AGPL, heavy |
| [GPT-Load](https://github.com/tbphp/gpt-load) | ~7k | Key scheduling, cooldowns | v2 breaks v1 data |
| [Portkey Gateway](https://github.com/Portkey-AI/gateway) | ~13k | Fallbacks, guardrails | Some features commercial |
Fallback rule: retry only 408/429/5xx/timeouts, honour `Retry-After`, backoff 1-2-4-8s cap 60s. 401/403 = disable key. Only fall back between models with the same tool-calling/context/protocol.
## 7. Free compute to self-host
| Option | What you get | Value |
|---|---|---|
| Kaggle | P100/T4, ~30 GPU h/week (community figure) | best notebook quota |
| Colab Free | T4 when available, max 12 h | 3-8B 4-bit, QLoRA |
| Lightning AI | up to 80 free GPU h to start | persistent workspace |
| HF ZeroGPU | 5 GPU min/day | demos only |
| Oracle Always Free ARM | 2 OCPU / 12 GB | tiny CPU models |
| Codespaces | 120 core-h/month, no GPU | dev env |
| Cloud Shell | 50 h/week, 5 GB, no GPU | dev env |
| IndiaAI Compute / E2E / Yotta | subsidised GPU or startup credits | need project proposal or registered startup |
## 8. Dead / not free (don't chase)
- **GitHub Models**: retired 30 Jul 2026.
- **Qwen Code OAuth free**: ended 15 Apr 2026.
- **Chutes** 200 RPD: retired 15 Mar 2026. **Kluster**: shut. **Lambda Inference**: winding down.
- **Together**: $5 minimum. **Cerebras** permanent free: now card trial.
- **Paid-only APIs**: DeepSeek, Moonshot/Kimi, xAI, Featherless, Perplexity Sonar ("no complimentary credits"), Venice API, DeepInfra, Poe API (spends points), Meta Model API, MiniMax, StepFun, Anthropic (tiny unstated credit), AgentRouter, Glama.
- **Not an API for Actions**: Puter.js (end-user pays), fal sandbox, Antigravity / Cursor / Windsurf / Kimi Code plans, GitLab Duo.
- **Unverified leads**: Glhf.chat, Agnes AI, Bhashini quotas, Yotta ₹10K promo.
## 9. Traps
1. One account per provider. Multi-account quota dodging = ban risk.
2. Free tiers log (NVIDIA, Gemini free, OpenRouter stealth, Kilo auto, Requesty, OpenAI data-sharing). Public code only; never Freespace data.
3. Avoid GPT4Free-style proxies, cheap-token resellers, random npm/PyPI "free AI proxy" packages (Sep 2026 reports: prompt logging, stolen keys, typosquat domains).
4. Actions: keys as secrets via env; no secrets on fork PRs; avoid `pull_request_target` + untrusted checkout; pin actions by SHA; start with `contents: read`.
5. Issue/PR text is attacker input. No write-capable agent with shell + secrets on it.
6. Free model IDs rotate. Read live `/models` at runtime.
## Sources (primary)
Groq https://console.groq.com/docs/rate-limits | Groq deprecations https://console.groq.com/docs/deprecations | Cerebras https://inference-docs.cerebras.ai/support/rate-limits | SambaNova https://docs.sambanova.ai/docs/en/models/rate-limits | Cloudflare https://developers.cloudflare.com/workers-ai/platform/pricing/ | OpenRouter https://openrouter.ai/docs/api_reference/limits | Gemini https://ai.google.dev/gemini-api/docs/openai | NVIDIA https://build.nvidia.com/llms.txt | Kilo https://kilo.ai/docs/gateway/authentication | LLM7 https://docs.llm7.io/limits | Cohere https://docs.cohere.com/docs/rate-limits | Requesty https://docs.requesty.ai/features/free-models | Reka https://reka.ai/news/end-of-summer-updates | Sarvam https://docs.sarvam.ai/api/getting-started/pricing | OpenAI data sharing https://help.openai.com/en/articles/10306912-sharing-feedback-evals-and-api-data-with-openai | IBM https://www.ibm.com/products/watsonx-ai/pricing | Voyage https://docs.voyageai.com/docs/pricing | Jina https://jina.ai/api-dashboard/pricing/ | Scaleway https://www.scaleway.com/en/docs/generative-apis/faq/ | Alibaba https://www.alibabacloud.com/help/en/model-studio/new-free-quota | Fireworks https://docs.fireworks.ai/guides/quotas_usage/account-quotas | GitHub Models retired https://github.blog/changelog/2026-07-30-github-models-is-now-retired/ | Qwen OAuth https://github.com/QwenLM/qwen-code/pull/3291 | Chutes https://chutes.ai/news/community-announcement-february | Together https://docs.together.ai/docs/billing-credits | Gemini CLI https://geminicli.com/docs/resources/quota-and-pricing/ | run-gemini-cli https://github.com/google-github-actions/run-gemini-cli | OpenCode https://opencode.ai/docs/github/ | Jules https://jules.google/docs/usage-limits/ | Oracle https://docs.oracle.com/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm | Perplexity https://www.perplexity.ai/help-center/en/articles/11187416 | Venice https://venice.ai/pricing | Meta https://ai.developer.meta.com/docs/getting-started/pricing-rate-limits
