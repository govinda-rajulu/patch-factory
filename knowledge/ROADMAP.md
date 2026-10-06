# patch-factory roadmap

Written 1 Oct 2026. One lane in flight at a time. New ideas go to the parking lot with a date.
Tool verdicts and agent rules: [handbook/AGENT-TOOLING.md](handbook/AGENT-TOOLING.md).
AGENTS.md hard limits, STATE.md and `docs/review/OPEN-WORK.md` win over this file.

## Now: the open build work

See the newest checkpoint in [STATE.md](STATE.md) (6 Oct 2026, packet R). The 1 Oct list that
stood here (Facebook #118/#119, Dependabot #103, YouTube #114) is closed or superseded.

## Lane 1: settings, no code (owner, in the browser)

- CodeRabbit on this repository, advisory only, with path instructions for workflows and
  signing. Never a required check (it passes when rate-limited).
- Council seats: the PR110 review got 4 of 6 (mistral 404, gpt unavailable). Probe, then fix
  `seats.json` in an owner-approved PR. Candidate extra seats: Groq, Cerebras, Mistral free mode,
  Cloudflare Workers AI. Each is a new secret the owner adds; keys never go in chat.

## Lane 2: security audit (read-only)

- Method: [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill),
  pinned. Scope: `.github/workflows/**` and `.github/actions/**` (secrets, signing, untrusted
  input), the fetchers (`src/build/fetch_bundle.sh`, `ggplay_dl`, store fetchers) and
  `src/council/` (`AI-AND-LLM.md` classes).
- Output: `docs/review/SECURITY-AUDIT-<date>/` with `findings.json` and `REPORT.md`, plus an
  OPEN-WORK entry. Fixes to protected files stay owner-reviewed packets.
- The executor holds no secrets. Read-only means no dispatch and no issue writes.

## Lane 3: fewer owner touches, same guardrails

- Morning report: one pinned issue that folds the per-run failure issues (#118 and #119 are the
  same Facebook failure twice) into one daily line per target.
- Limited worker: may touch only what AGENTS.md "What you may propose" allows
  (`include-patches`, `extra_bundles`, `note`), enforced by a path guard. BANNED and CONFIRM
  still apply; CONFIRM means the owner decides. No workflows, signing or releases.

## Parking lot

- 1 Oct 2026: council `ask` mode answering the morning report's questions.
- 1 Oct 2026: competing drafts, only if the limited worker proves useful.
