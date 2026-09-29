# Agent council

An advisory review panel of free model seats. It reviews pull requests and votes on new
patches and providers, then posts one comment. **It never writes code, config, releases or
settings, and nothing waits on it**: builds, merges and releases run exactly as before.
The owner decides; the council saves the owner reading time and catches what one reader misses.

Code: [src/council/council.py](../../src/council/council.py) (standard library only).
Seats: [src/council/seats.json](../../src/council/seats.json). Workflow: `.github/workflows/council.yml`.

## Seats

Six seats from six model families, all on free tiers. Each seat uses the first model on its
list that the provider still serves, because free catalogues change without notice.

| Seat | Provider | Key |
|---|---|---|
| gpt, mistral, nemotron, minimax | NVIDIA build | `NVIDIA_API_KEY` |
| gemini | Google AI Studio | `GEMINI_API_KEY` |
| open | OpenRouter free models | `OPENROUTER_API_KEY` |

A seat without its key is skipped, never an error. A model the provider reports retired
(410) or not served falls through to the next one on the seat's list. Since 29 Sep 2026 so
does a busy or unreachable model (429, 5xx or timeout); only the seat's last model is
retried, which keeps a slow provider inside the job's time limit. An authentication or other
error still stops the seat. GitHub Models retired on 30 Jul 2026, so no seat uses it.

## Jobs

- **PR review** (automatic on every pull request from this repository): each seat reviews the
  diff against AGENTS.md, OWNER.md and the matching lessons. Findings are merged by file and
  line and shown with how many seats agree. One comment per PR, edited on each push.
- **Question** (Actions, Council, mode `question`): one patch or provider for one target.
  Rules run first, then the seats vote, then one table is posted on the chosen issue.
- **Ask** (mode `ask`, input `question`, optional `target`): one factual question, answered
  `yes`, `no` or `unknown` from generated repository facts (target config, include and
  exclude lists, rule lists, committed provider name baselines). Each answer must cite the
  exact fact keys it used; an answer citing any other key is dropped. Use this, not a vote,
  for "is X excluded?" questions.
- **Probe** (mode `probe`): shows which seats answer and which model each picked. Posts nothing.

## Outcomes

| Situation | Outcome |
|---|---|
| Patch matches `BANNED` | `reject` by rule. No model is asked. |
| Patch matches `CONFIRM` | `ask_owner` whatever the seats say; their reasons are still shown. |
| Every valid vote agrees (at least 3 valid) | `recommend` that vote |
| Two thirds agree and nobody votes the opposite (adopt vs reject) | `lean` that vote, dissent shown |
| Fewer than 3 valid votes, or a real split | `hold`: nothing changes and nothing is blocked |

Splits never stall anything, because the council gates nothing. `hold` means "no advice yet".

A vote whose reasons cite no file path, rule list, trusted document or supplied fact key is
dropped before counting (status `DROPPED_UNCITED`) and the comment says how many were dropped.
In the 28 Sep 2026 injection test one seat voted `adopt` with only "Owner override" as its
reason; with this rule its vote no longer counts. Ask mode reports `agree`, `majority` (two
thirds, no yes-versus-no split) or `split`, and `unknown` below three valid answers.

## Defences

**Prompt injection.** Diffs, PR titles, provider patch names and notes are untrusted. They
reach seats only as JSON strings inside labelled DATA blocks, with control characters
removed and hard length caps. Each run embeds a random canary; a seat that echoes it, or
answers outside the strict JSON schema, is discarded. Seats have no tools and no tokens.
The workflow checks out the **base** commit, so a pull request cannot change the council code
that reviews it. Fork and bot PRs never receive keys. Comment text is sanitised: no mentions,
links, images, HTML or code fences from a model reach GitHub.

**Context growth.** Every pack is built deterministically: the AGENTS.md hard limits, OWNER.md,
at most eight lessons chosen by tag, and only the facts for this target or diff. A seat whose
pack exceeds its budget abstains. Nothing is truncated silently.

**Blast radius.** The script can call only four GitHub endpoints: read a PR, read an issue,
list comments, and post or edit its own comment. Anything else is refused in code and tested.

## How it evolves without breaking anything

- A seat may propose a lesson inside its vote. It is shown, never applied.
- The owner approves a lesson in the issue; a reviewed packet appends it to LESSONS.md.
- LESSONS.md is append-only. Validation pins a hash of every existing entry and fails if one
  is edited or removed; a wrong lesson is superseded by a newer dated entry.
- PROMPT.md, REVIEW.md, OWNER.md and seats.json change only in owner-approved PRs.

## Privacy

This repository is public. Nothing here or in a council comment may contain keys, tokens,
signing material, personal accounts, private chats, or anything unrelated to this project.
Keys live only in repository secrets and reach only the council step. Free tiers may use
prompts to improve models; everything sent is already public in this repository.
