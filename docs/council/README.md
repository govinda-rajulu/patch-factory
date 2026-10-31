# Agent council

An advisory review panel of free model seats. It reviews pull requests and votes on new
patches and providers, then posts one comment. **It never writes code, config, releases or
settings, and nothing waits on it**: builds, merges and releases run exactly as before.
The owner decides; the council saves the owner reading time and catches what one reader misses.

Code: [src/council/council.py](../../src/council/council.py) (standard library only).
Seats: [src/council/seats.json](../../src/council/seats.json). Workflow: `.github/workflows/council.yml`.
Keys, free limits, seat budgets and the small-to-heavy lanes: [SETUP.md](SETUP.md). What each
provider accepts: [PROVIDERS.md](PROVIDERS.md). Agent runners and MCP plan: [RUNNERS.md](RUNNERS.md).

## Seats

Nine seats on eight providers, all on free tiers where seated (since 7 Oct 2026). Each seat
uses the first model on its list that the provider still serves, because free catalogues change
without notice.

| Seat | Provider | Key |
|---|---|---|
| gpt | NVIDIA | `NVIDIA_API_KEY` |
| gemini | Google AI Studio | `GEMINI_API_KEY` |
| nemotron | NVIDIA | `NVIDIA_API_KEY` |
| open | OpenRouter | `OPENROUTER_API_KEY` |
| codestral | Mistral | `MISTRAL_API_KEY` |
| command | Cohere | `COHERE_API_KEY` |
| kilo | Kilo Gateway | `KILO_API_KEY` |
| zai | Z.AI | `ZAI_API_KEY` |
| groq | Groq (25,000-character ask/probe budget) | `GROQ_API_KEY` |

The nine-seat, eight-provider roster is read from `src/council/seats.json`; the provider key mapping is in
`src/council/council.py`. The workflow skips a seat without its key and reports no error. A
retired, busy or unreachable model falls through the seat's own models and then its configured
backups on other providers when a key is available. An authentication or other terminal error
still stops that seat. GitHub Models retired on 30 July 2026, so no seat uses it.

## Jobs

- **PR review** (automatic on same-repository pull requests, not forks or Dependabot): each review seat reviews the
  diff against AGENTS.md, OWNER.md and the matching lessons. Findings are merged by file and
  line and shown with how many seats agree. The council posts one comment per PR and edits it on each push.
- **Question** (Actions, Council, mode `question`): one patch or provider for one target.
  Rules run first, then the seats vote, then one table is posted on the chosen issue.
- **Ask** (mode `ask`, input `question`, optional `target`): one factual question, answered
  `yes`, `no` or `unknown` from generated repository facts (target config, include and
  exclude lists, rule lists, committed provider name baselines). Each answer must cite the
  exact fact keys it used; an answer citing any other key is dropped. Use this, not a vote,
  for "is X excluded?" questions.
- **Audit** (mode `audit`, inputs `shard` and `issue`): one shard of the repository from
  `src/council/shards.json`, read at the dispatched commit and reviewed in parts of at most
  70000 characters with [AUDIT.md](AUDIT.md). Seats run concurrently across providers while
  calls sharing one provider remain serialized and paced. One comment per shard on the chosen issue,
  edited on a rerun. If the time or ten-part cap leaves work, the next run starts with the exact
  `Not reviewed` part numbers recorded in that desk comment. Running every shard on one issue is a whole-repository audit.
  Since W14 (11 Oct 2026) each seat is trained by [AGENT-SPEC.md](AGENT-SPEC.md) and also
  reads the newest `knowledge/STATE.md` entry and the current OPEN-WORK checkpoint. A finding may
  carry a one-line `replacement`; it applies only when the quoted line occurs once and the file
  still parses (Python and JSON in the council step; shell and JavaScript in the next step,
  which has no keys). Applied fixes are listed under "Proposed fixes" and kept as the run
  artifact `council-fixes`. Nothing is committed or pushed: a fix enters only by packet.
- **Triage** (mode `triage`, input `issue`): every other open issue, 6 per call, judged `close`,
  `keep` or `owner` with [TRIAGE.md](TRIAGE.md). A verdict must cite a run id, an issue or PR
  number, or a repository path; uncited verdicts are dropped. One table on the chosen issue.
  It closes nothing; the owner or a packet does.
- **Probe** (mode `probe`): shows which seats answer and which model each picked. Posts nothing.
- **Desk rotation** (schedule): twice a day one audit shard; Monday morning is triage and Sunday
  morning the model probe instead; all on
  the Council desk issue named in seats.json. Each comment is edited in place, never repeated.
  Sunday afternoon (the existing 15:17 UTC audit slot) is the weekly repo review slot: after
  quote verification, it creates at most eight issues titled `review: ...`, each with the
  `review` label, a stable `<!-- pf-review:<fingerprint> -->` marker, evidence and the triage
  instruction. It searches open and closed issues before creating anything, so reruns and old
  findings are deduplicated. Findings beyond eight stay in the desk comment; no issue is closed
  or edited automatically. Other audit slots, shifts and manual runs only update the desk.

Since 7 Oct 2026 (packet V1) every reply is asked for in JSON mode, reasoning seats run with low
effort and room to answer, a 404 moves to the seat's next model, a refused reply gets one repair
turn, and every review or audit finding must quote a line that really is in the cited file
(else it is dropped and counted). Seats may list `jobs` in seats.json; Groq takes probe and ask only; its 25,000-character budget is too small for the trained audit prompt, so it is not a default audit seat.

## Outcomes

| Situation | Outcome |
|---|---|
| Patch matches `BANNED` | `reject` by rule. No model is asked. |
| Patch matches `CONFIRM` | `ask_owner` whatever the seats say; their reasons are still shown. |
| Every valid vote agrees (at least 3 valid) | `recommend` that vote |
| Two thirds agree and nobody votes the opposite (adopt vs reject) | `lean` that vote, dissent shown |
| Fewer than 3 valid votes, or a real split | `hold`: nothing changes and nothing is blocked |

A split returns `hold` ("no advice yet"). It cannot stall work because the council does not gate anything.

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

**Blast radius.** The script can call only the GitHub endpoints in `GH_ALLOWED`
(src/council/council.py): read a pull request, an issue, issue lists, comments, the `review` label
and the Actions run list; create the label, an issue (weekly review) and comments; edit a comment. Anything else is refused
in code and tested.

## How it evolves without breaking anything

- A seat may propose a lesson inside its vote. It is shown, never applied.
- The owner approves a lesson in the issue; a reviewed packet appends it to LESSONS.md.
- LESSONS.md is append-only. Validation pins a hash of every existing entry and fails if one
  is edited or removed; a wrong lesson is superseded by a newer dated entry.
- PROMPT.md, REVIEW.md, ASK.md, AUDIT.md, OWNER.md, seats.json and shards.json change only in
  owner-approved PRs.

## Privacy

This repository is public. Nothing here or in a council comment may contain keys, tokens,
signing material, personal accounts, private chats, or anything unrelated to this project.
Keys live only in repository secrets and reach only the council and onboarding-review steps that call models. Free tiers may use
prompts to improve models; everything sent is already public in this repository.

## Onboarding review (8 Oct 2026, packet W1)

`src/council/onboard_review.py` reuses the seats and transport above for one more job: the
`Onboarding review` workflow's agent step. It reads only the manifest that
`src/etc/onboard_check.py` wrote from the pull request, answers with quoted findings
(prompt: `ONBOARD.md`), and passes with at least 2 counted verdicts and fewer than half block.
Rules: `docs/review/onboarding/README.md`.
