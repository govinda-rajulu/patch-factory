# Council setup: free keys, seats and lanes

Written 6 Oct 2026 (packet T1). All six keys were stored in this repository and in openskip on
7 Oct 2026, each tested against its provider first. Quotas and model names change without notice; the council
copes (a missing key skips the seat, a retired model falls through), but re-check a provider's
own page before relying on a number here. Keys live only in repository secrets
(Settings, Secrets and variables, Actions). They never go in chat, code, issues or this repo.

## Keys

All six are free without a card. Everything the council sends is already public in this
repository, so free-tier prompt use for training costs nothing private.

| Secret | Provider | Where to create it | Free limit (seen 6 Oct 2026) | Seats |
|---|---|---|---|---|
| `NVIDIA_API_KEY` | NVIDIA build | https://build.nvidia.com/settings/api-keys | about 40 requests a minute per model | gpt, nemotron |
| `GEMINI_API_KEY` | Google AI Studio | https://aistudio.google.com/app/apikey | per model, shown in AI Studio; free prompts may train Google models | gemini |
| `OPENROUTER_API_KEY` | OpenRouter `:free` models | https://openrouter.ai/keys | about 20 a minute, 50 a day | open |
| `MISTRAL_API_KEY` | Mistral La Plateforme, free (Experiment) plan | https://console.mistral.ai/api-keys | per workspace, shown in the console; phone check at signup | codestral |
| `COHERE_API_KEY` | Cohere trial key | https://dashboard.cohere.com/api-keys | 1000 calls a month, 20 a minute; evaluation use | command |
| `GROQ_API_KEY` | Groq | https://console.groq.com/keys | about 30 a minute, 1000 a day, 8000 tokens a minute | groq |

Not seated, with the reason: Cerebras (trial credit with a card, no lasting free tier),
GitHub Models (retired 30 Jul 2026), Cloudflare Workers AI (needs an account id and is not the
OpenAI chat shape), Hugging Face ($0.10 a month), Together, SambaNova, Scaleway, Chutes (credit
or paid only), ModelScope and SiliconFlow (identity checks). Candidates for later, unverified:
Ollama Cloud, Kilo Gateway, Z AI GLM Flash, LLM7. Research sources: the
[awesome-free-llm-apis](https://github.com/mnfst/awesome-free-llm-apis) and
[free-llm-api-resources](https://github.com/cheahjs/free-llm-api-resources) lists, then each
provider's own pricing or rate-limit page.

## Seats and budgets

`src/council/seats.json`: seven seats on six providers. On 7 Oct 2026 the `kimi` seat was removed
(none of its four NVIDIA models is served to this key) and, earlier that day, the NVIDIA-hosted
`mistral` seat was dropped (its model returned 404, and the `codestral` seat reaches Mistral
directly) and `minimax` became `kimi` (none of its models was served). `max_input_chars` is each seat's budget;
a pack larger than the budget makes that seat abstain instead of failing. So the Groq seat (8000
tokens a minute) answers probes and small asks, while the large seats take reviews and audits.
Quorum stays 3 valid answers. A seat's optional `jobs` list limits what it is sent (Groq: probe
and ask), and `reasoning_effort` plus `max_tokens` keep reasoning models from spending their
whole answer budget thinking (7 Oct 2026: four seats failed that way, see LESSONS 19).

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
| rotation | schedule, 03:17 and 15:17 UTC | none (desk issue in seats.json) | one audit shard per run, triage on Monday mornings, on the desk |

Run heavy jobs one at a time. On 7 Oct 2026 eleven audit shards dispatched together ran the free
tiers out (most seats busy); the schedule exists so that never happens again.

Audit shards (`src/council/shards.json`): workflows, council, selection, build-shell,
build-python, etc, portal, docs, tests-build, tests, rest. Each shard is split into parts of at
most 70000 characters, so every part fits a 100000-character seat with its trusted context.
Records under `docs/review/`, generated files, the licence, the archive and binary files are
never sent. A run stops starting new parts after 30 minutes and names the parts it did not reach.

## How results are used

Council output is a set of leads. The reviewer reads each finding against the code at the same
commit, keeps what reproduces, and turns it into an issue or a gated packet. Nothing merges,
builds or publishes because of a council comment (README, Defences).
