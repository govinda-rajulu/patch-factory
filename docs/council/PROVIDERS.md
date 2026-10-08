# Council providers: what each free API accepts (7 Oct 2026)

Research record behind the V1 and V2 council changes. Sources: each provider's own docs and
forums, read 7 Oct 2026. Free tiers change without notice; the council copes, but re-check a
provider page before relying on a number. Keys and limits: [SETUP.md](SETUP.md).

| Provider | JSON | Reasoning | Seen failures and what the council does |
|---|---|---|---|
| NVIDIA build | `response_format` json_object (syntax only; NIM's schema mode is `nvext.guided_json`) | gpt-oss and Nemotron: `reasoning_effort` low | 404 "Function not found for account" for a model `/v1/models` lists (kimi-k2.6, deepseek): the key is not entitled. 404 always falls through; missing models are remembered per run. |
| Gemini (OpenAI compatibility) | json_object; schema mode varies by model | `reasoning_effort` low maps to a thinking level; thinking counts against max tokens | Busy (429/503) under parallel load; wait for `retryDelay`. Empty content when thinking used the budget: max_tokens 8000. |
| OpenRouter `:free` | json_object; schema only on endpoints that support it (`provider.require_parameters`) | `reasoning_effort` or `reasoning.effort` | Free models come and go: missing and busy are normal; about 50 calls a day. |
| Mistral | json_object (the prompt must say JSON) | none needed | Answered every part on 6-7 Oct (codestral-latest). |
| Cohere compatibility | json_object | `reasoning_effort` only `none` or `high` | Trial key: 1000 calls a month, so heavy jobs stay on the schedule. |
| Groq | json_object | gpt-oss low; qwen `none` | 8000 tokens a minute: seat takes probe and ask only. |

Council behaviour that follows (council.py): every call asks for JSON mode; a 400 or 422 that
names `response_format` or `reasoning` drops that field once and is remembered; a cut reply
(`finish_reason` length, empty content) moves to the next model and is reported; one repair
turn shows the seat its exact refusal; findings must quote a real line or are dropped; heavy
jobs run one at a time on the desk schedule.

## 8 Oct 2026: checked against the owner's v2 field guide

Source: `knowledge/handbook/FREE-LLM-APIS-2026-10-v2.md` (owner-supplied, facts dated 7 Oct
2026; free tiers change monthly). Against the seats in `src/council/seats.json`:

- Groq's Qwen id `qwen/qwen3.8-27b` matches the guide's corrected id. GitHub Models stays retired.
- OpenRouter free models: 20 RPM and 50 requests a day, 1,000 a day after a one-time $10
  purchase (owner decision; it would lift the `open` seat's daily cap).
- Not seated yet, free without a card: Kilo Gateway (anonymous, 200 requests an hour per IP),
  Requesty (200 a day), Cloudflare Workers AI (10,000 Neurons a day), LLM7 (100K tokens a day),
  Reka ($10 monthly credit). Each needs a `PROVIDERS` entry in `council.py`, a secret and a
  probe run: packet W2, one provider at a time.
- Free tiers log prompts (NVIDIA, Gemini free, OpenRouter stealth models, Kilo auto, Requesty).
  Seats only ever see this public repository.
