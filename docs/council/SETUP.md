# Council setup: free keys, seats and lanes

**Limits checked 23 Oct 2026:** the dated official-provider table is [PROVIDERS.md](PROVIDERS.md); values here are a quick operational summary.

Written 6 Oct 2026 (packet T1). The original six keys were stored in this repository and in openskip on
7 Oct 2026, each tested against its provider first. Quotas and model names change without notice; the council
copes (a missing key skips the seat, a retired model falls through), but re-check a provider's
own page before relying on a number here. Keys live only in repository secrets
(Settings, Secrets and variables, Actions). They never go in chat, code, issues or this repo.

## Keys

The seated providers are free-tier or optional free-model services; key availability and quotas can change. Everything the council sends is already public in this
repository, so free-tier prompt use for training costs nothing private.

| Secret | Provider | Where to create it | Free limit (checked 23 Oct 2026) | Seats |
|---|---|---|---|---|
| `NVIDIA_API_KEY` | NVIDIA build | https://build.nvidia.com/settings/api-keys | free trial; exact per-model limits not published (see [PROVIDERS.md](PROVIDERS.md)) | gpt, nemotron |
| `GEMINI_API_KEY` | Google AI Studio | https://aistudio.google.com/app/apikey | per model, shown in AI Studio; free prompts may train Google models | gemini |
| `OPENROUTER_API_KEY` | OpenRouter `:free` models | https://openrouter.ai/keys | 20/min, 50/day without credits (1,000/day after 10 credits) | open |
| `MISTRAL_API_KEY` | Mistral La Plateforme, free mode | https://console.mistral.ai/api-keys | per workspace/model, shown in Admin Panel; no public numeric value | codestral |
| `COHERE_API_KEY` | Cohere trial key | https://dashboard.cohere.com/api-keys | 1,000 calls/month, 20/min per chat model; evaluation use | command |
| `GROQ_API_KEY` | Groq | https://console.groq.com/keys | 30/min, 1,000/day, 8,000 tokens/min (official table) | groq |
| `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` | Cloudflare Workers AI (W15h, optional) | https://dash.cloudflare.com/profile/api-tokens (template "Workers AI", Read); the account id is on the dashboard Overview page (32 hex characters) | 10,000 neurons a day, reset 00:00 UTC; no training on inputs | backup for every seat |
| `KILO_API_KEY` | Kilo Gateway (W16d full seat) | https://app.kilo.ai (API keys) | free models (ids end in :free; kilo-auto/free was dropped in W16h, the probe refused it) at 200 requests an hour (kilo.ai/docs/gateway/usage-and-billing) | full seat (plus backups) for the portal shard |
| `ZAI_API_KEY` | Z.AI (W16d full seat) | https://z.ai/manage-apikey/apikey-list | GLM-4.7-Flash and GLM-4.5-Flash free ([pricing](https://docs.z.ai/guides/overview/pricing)); numeric limits shown only in the account | full seat (plus backups) for the etc shard |

W15h (22 Oct 2026): Cloudflare has an OpenAI-style endpoint
(`/client/v4/accounts/<id>/ai/v1/chat/completions`, developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility),
so it is now wired as the last backup of every seat; nothing calls it until both secrets exist.
OpenRouter: one $10 credit purchase raises `:free` models from 50 to 1000 calls a day (openrouter.ai/docs/faq);
optional, the only paid step, owner's choice.

Not seated, with the reason: Cerebras (trial credit with a card, no lasting free tier),
GitHub Models (retired 30 Jul 2026), Hugging Face ($0.10 a month), Together, SambaNova, Scaleway, Chutes (credit
or paid only), ModelScope and SiliconFlow (identity checks). Candidates for later, unverified:
Ollama Cloud, LLM7 (Kilo Gateway and Z AI GLM Flash are seated since W15i). Research sources: the
[awesome-free-llm-apis](https://github.com/mnfst/awesome-free-llm-apis) and
[free-llm-api-resources](https://github.com/cheahjs/free-llm-api-resources) lists, then each
provider's own pricing or rate-limit page.

## Seats and budgets

`src/council/seats.json`: nine seats on eight providers. On 7 Oct 2026 the `kimi` seat was removed
(none of its four NVIDIA models is served to this key) and, earlier that day, the NVIDIA-hosted
`mistral` seat was dropped (its model returned 404, and the `codestral` seat reaches Mistral
directly) and `minimax` became `kimi` (none of its models was served). `max_input_chars` is each seat's budget;
a pack larger than the budget makes that seat abstain instead of failing. So the Groq seat (8000
tokens a minute) answers probes and small asks; its 25000-character budget cannot hold the trained
audit prompt, so it is not a default audit seat. The Kilo and Z.AI full seats take reviews and
audits when their keys are present.
Quorum stays 3 valid answers. A seat's optional `jobs` list limits what it is sent (Groq: probe and ask),
and the configured low `reasoning_effort` keeps reasoning models from spending their whole answer
budget thinking. Calls do not set `max_tokens`; the provider controls output limits.

### W15h: why seats failed, and what changed (22 Oct 2026)

Desk #154, 7 to 22 Oct: most lost answers were `UNAVAILABLE no listed model answered (N missing,
N busy, N cut at max_tokens)`; codestral and command almost always answered. Three causes, none
"a seat added for show": model ids retired by the provider (missing), free-tier limits hit by
seats calling at once (busy; gpt and nemotron share one NVIDIA account), and reasoning models
spending the answer budget thinking (cut). Since W15h:

- `discover` patterns per seat add up to two catalogue models after the seat's own list.
- `backups` per seat: models on other providers, tried after the seat's own; a backup without a
  key is skipped. The desk names them `model via provider (backup)`.
- A cut reply gets one more try with twice the room (at most 16000) and `reasoning_effort` low.
- Seats run concurrently across providers; calls to one provider go one at a time and retain their pacing gap. `PACE` in `src/council/council.py` uses 80% of each
  documented request limit where available (Kilo 22.5s, OpenRouter/Cohere 3.75s, Groq 2.5s);
  providers with account-only limits retain a conservative gap.
- Audit memory: a shard whose files and prompt match its last audit (valid answers, under 14
  days old) is not sent again. `PF_REAUDIT=1` forces a fresh audit.

## Lanes: small to heavy

| Lane | Job (Actions, Council) | Inputs | What comes back |
|---|---|---|---|
| S: one fact | mode `ask` | `question`, optional `target`, `issue` | yes, no or unknown with cited fact keys |
| M: one decision | mode `question` | `target`, `kind`, `name`, `issue` | a vote table; BANNED and CONFIRM run first |
| M: one change | every pull request (automatic) | none | merged findings with seat agreement |
| L: one shard | mode `audit` | `shard`, `issue` | merged findings for that shard, one comment per shard |
| XL: whole repo | mode `audit` once per shard, same issue | every id in `src/council/shards.json` | one comment per shard on one issue |
| M: issue hygiene | mode `triage` | `issue` (where the table goes) | close, keep or owner per open issue, cited |
| health | mode `probe` | none | which seats answer, in the run summary |
| rotation | schedule, 03:17 and 15:17 UTC | none (desk issue in seats.json) | one audit shard per run; Monday morning triage, Sunday morning model probe; on the desk |
| fix lane (W14) | inside every audit | none | one-line fixes that apply and parse, as artifact `council-fixes`; never pushed |

Run heavy jobs one at a time. On 7 Oct 2026 eleven audit shards dispatched together ran the free
tiers out (most seats busy); the schedule exists so that never happens again.

Audit shards (`src/council/shards.json`): workflows, council, selection, build-shell,
build-python, etc, portal, docs, tests-build, tests, rest. Each shard is split into parts of at
most 70000 characters and goes only to seats whose max_input_chars can hold it with the trusted
context (src/council/seats.json; a small seat such as Groq's is ask and probe only).
Records under `docs/review/`, generated files, the licence, the archive and binary files are
never sent. A run stops starting new parts after 30 minutes and names the parts it did not reach. The next run
uses those recorded part numbers first, then resumes the normal path order; the line remains honest
when the run reaches another limit.

## How results are used

Council output is a set of leads. The reviewer reads each finding against the code at the same
commit, keeps what reproduces, and turns it into an issue or a gated packet. Nothing merges,
builds or publishes because of a council comment (README, Defences).
