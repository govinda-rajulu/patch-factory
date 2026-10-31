# Council providers: official free-tier limits (checked 23 Oct 2026)

This is the dated research record for the models currently named in
[`src/council/seats.json`](../../src/council/seats.json). Values are from each provider's own
public documentation, pricing, or rate-limit page. A provider that says the value is shown only
in an account dashboard is recorded as **not documented** here; we do not turn an anecdotal or
account-specific value into a repository budget. The council uses at most about 80% of a
published request limit when it can, with one call at a time per provider.

| Provider / models used by this repo | RPM | RPD | TPM / TPD | Other free cap | Official source and exact quote |
|---|---:|---:|---:|---|---|
| **Kilo Gateway**: `xingchen-agi/xing4.0-29b-a4b:free`, `nvidia/nemotron-3-ultra-550b-a55b:free`, `recursive/flint-v1.0:free` (full `kilo` seat; W16h dropped `kilo-auto/free`, refused with 400 in the 25 Oct probe) | **not stated** (200/hour = 3.33 RPM arithmetic) | not documented | not documented | Free models: **200 requests/hour/IP** | [Usage & Billing](https://kilo.ai/docs/gateway/usage-and-billing): “**Free models per IP \| 200 requests per hour**.” |
| **Z.AI**: `glm-4.7-flash`, `glm-4.5-flash` (full `zai` seat) | not documented | not documented | not documented | Both listed as free; quota is account-specific | [Pricing](https://docs.z.ai/guides/overview/pricing): “**GLM-4.7-Flash \| Free \| Free \| Free \| Free**” and “**GLM-4.5-Flash \| Free \| Free \| Free \| Free**.” [FAQ](https://docs.z.ai/help/faq): “**You can check the rate limits from here: https://z.ai/manage-apikey/rate-limits**.” |
| **Groq**: `qwen/qwen3.8-27b`, `openai/gpt-oss-120b`, `openai/gpt-oss-20b` | **30** | **1,000** | **8,000 TPM / 200,000 TPD** | Limits apply at organization level; cached tokens do not count | [Rate Limits](https://console.groq.com/docs/rate-limits): the exact rows are “**openai/gpt-oss-120b \| 30 \| 1K \| 8K \| 200K**”, “**openai/gpt-oss-20b \| 30 \| 1K \| 8K \| 200K**”, and “**qwen/qwen3.8-27b \| 30 \| 1K \| 8K \| 200K**”; the page also says “**Rate limits apply at the organization level, not individual users.**” |
| **OpenRouter**: `cohere/north-mini-code:free`, `google/gemma-4-31b-it:free`, `openrouter/free` | **20** | **50** without purchased credits; **1,000** after at least 10 credits | token limits not documented for free variants | Free-model cap is account-wide; `GET /api/v1/key` reports the daily counter | [API Credit & Rate Limits](https://openrouter.ai/docs/api_reference/limits): free-model table says “**Less than 10 \| 20 \| 50**” and “**At least 10 \| 20 \| 1000**.” |
| **NVIDIA NIM**: `openai/gpt-oss-20b`, `nvidia/nemotron-3-ultra-550b-a55b`, `nvidia/nemotron-3.5-super-vl-120b-a12b`, `nvidia/nemotron-3-super-120b-a12b` (W16h: models the 25 Oct probe found MISSING were dropped) | not documented | not documented | not documented | Free trial, no card; per-model limits are account/model-specific | [NVIDIA API Catalog FAQ](https://build.nvidia.com/llms.txt): “**All models offer a free trial tier with no credit card required.**” NVIDIA's official forum answer says: “**The rate limits vary for each model, and we do not publish those.**” ([source](https://forums.developer.nvidia.com/t/request-more-4-000-credits-option-on-build-nvidia-com/344567)). |
| **Mistral La Plateforme Free mode**: `codestral-latest`, `mistral-small-latest` | not documented (docs expose RPS, not a value) | not documented | not documented (docs say model-specific tokens/minute, no value) | Included monthly usage is shown in the account Limits page | [Usage and limits](https://docs.mistral.ai/admin/billing-usage/usage-limits): “**Completion rate limits are listed per model and include: Tokens per minute ... Requests per second**” and “**Free mode lets you create API keys and use included monthly usage within the limits shown on the Limits page.**” |
| **Cohere trial key**: `command-a-reasoning-08-2025`, `command-a-03-2025` | **20 per model** | not documented (monthly cap instead) | not documented | **1,000 API calls/month** for trial keys | [Rate limits](https://docs.cohere.com/docs/rate-limits): “**Trial keys ... are limited to 1,000 API calls a month.**” and the Chat table lists “**Command A Reasoning \| 20 req / min**” and “**Command A \| 20 req / min**.” |
| **Google Gemini API Free tier**: `gemini-3.6-flash`, `gemini-3-flash-preview`, `gemini-flash-latest` | not documented publicly; active value is in AI Studio | not documented publicly | not documented publicly | Free tier has free input/output tokens for eligible models; preview/experimental models are more restricted | [Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits): “**Limits vary depending on the specific model being used**” and “**Rate limits ... can be viewed in Google AI Studio**.” [Pricing](https://ai.google.dev/gemini-api/docs/pricing): Free tier says “**Free input & output tokens**.” |

## Raised council budgets and pacing

The request ceilings above are account/provider limits, not promises that a model will answer. The
repo now uses the following safe request pacing: Kilo 22.5 seconds between calls (160/hour),
OpenRouter 3.75 seconds (16/minute), Cohere 3.75 seconds (16/minute), and Groq 2.5 seconds
(24/minute). These are 80% of the corresponding published caps. NVIDIA, Mistral, Z.AI, Gemini,
and Cloudflare publish no usable public number for this account/model combination, so their
conservative existing gaps remain and are explicitly not described as quota guarantees.

`max_input_chars` is 200,000 characters for the full review/audit seats (Groq remains 25,000 because
its documented 8K TPM is the tightest seated cap). Groq remains on ask/probe only: its 25,000-character budget cannot hold the trained audit prompt, so it is not a default audit seat. Larger audit work is handled by the full seats. Kilo is a
full seat on the portal shard and Z.AI is a full seat on the etc shard, targeting the previously thin
App shelf and maintenance paths. No seat sets `max_tokens`: the request
omits that field so each provider enforces its own model output maximum. Groq remains restricted to small ask/probe jobs by its `jobs` list, 25,000-character budget,
pacing, and 8K TPM. The code does not set an artificial completion cap. Groq is not a default
audit seat because the trained audit prompt does not fit. An
explicit cap supplied by a caller is still honored and doubled once after truncation. A busy/exhausted
response (429/5xx or timeout) moves through the seat's own models and then its keyed backups.

The schedule remains two desk slots daily: Monday morning triage, Sunday morning model probe, the
rest audits (Sunday afternoon files review issues); solo shifts run only
on request since W16k (their crons were removed);
`L039` keeps one heavy job per run. Audit parts remain capped at 10 and 70,000 characters, and
the 30-minute audit deadline remains the per-run wall-clock cap. The workflow's concurrency group
prevents a newer run for the same PR/desk invocation from racing an older one.

## Rejected vendors recorded for W16 (owner brief §6, checked 23 Oct 2026)

| Vendor | Rejection recorded by owner |
|---|---|
| Qwen/Alibaba | One-time 1M tokens per model for 90 days, Singapore region; OAuth free tier ended 15 Apr 2026 |
| Moonshot Kimi direct | Requires a $1 top-up |
| DeepSeek direct | Paid only |
| Cerebras | Card needed |
| GitHub Models | Retired 30 Jul 2026 |
| Chutes | No free tier |
| Kiro | Terms ban proxies |
| MiniMax direct | Free amount not confirmed |

Candidates not tried: xKiro, BazaarLink, and Kilo without a key. OmniRoute is reference-only and
stale, not a source for these limits.

## Request behavior (unchanged)

| Provider | JSON / reasoning handling | Failure and fallback behavior |
|---|---|---|
| NVIDIA build | `response_format` JSON object; gpt-oss/Nemotron use low `reasoning_effort` | A 404/410 means the key is not entitled to that model; the next model is tried. |
| Gemini (OpenAI compatibility) | JSON object; low `reasoning_effort` maps to model thinking | 429/503 waits for `retryDelay`; an empty/cut reply moves on. |
| OpenRouter `:free` | JSON object where the endpoint supports it | Free models can disappear or be busy; provider fallback then seat backups are tried. |
| Mistral | JSON object (prompt also says JSON) | Model-specific limits are account-visible; failures move to the next preference. |
| Cohere compatibility | JSON object; reasoning effort only when accepted | Trial calls stay on the scheduled lanes; busy/refused calls move to the next model. |
| Groq | JSON object; gpt-oss low effort and Qwen no reasoning effort | The 25,000-character seat handles ask/probe only; the trained audit prompt does not fit, so Groq is excluded from default audits and calls remain paced against 8K TPM. |
| Kilo Gateway / Z.AI | OpenAI-compatible JSON requests | Full portal/etc seats (and backups); 429/busy responses fall through to the next model/provider. |

Every request asks for JSON mode. If a model rejects `response_format` or `reasoning_effort`, that
optional field is dropped for the rest of the run. A cut reply gets one larger retry, then moves
to the next model. Invalid or uncited answers do not count toward quorum. The scheduled heavy
lanes remain one audit shard per run. Parts are dispatched concurrently across providers, while
provider-shared seats (notably gpt and nemotron on NVIDIA) remain serialized and paced.
