# Outside-repo review, 22 Oct 2026 (packet W15f)

Owner asked: review 12 public repositories and "GitHub living agents", add what fits. Five
research agents read each repository's README, LICENSE and GitHub API record on 22 Oct; the
assistant checked the claims that change code here against our own files. Star counts and dates
are that day's snapshot.

## Verdicts

| Repository | What it is | License | Verdict | Where it lands |
|---|---|---|---|---|
| cloudflare/security-audit-skill | multi-phase source-grounded security audit skill | MIT | PORT | docs/council/checklists/WARDEN.md (supply chain, CI isolation, sign/publish digest) |
| affaan-m/ECC | agents, skills, hooks for coding harnesses | MIT | PORT | MECHANIC.md (verification loop, >80% confidence rule as "would bet on it") |
| cursor/plugins | Cursor plugin marketplace (Team Kit, Thermos) | MIT per plugin | PORT | council voice evidence gate; diff-scoped review idea |
| DietrichGebert/ponytail | "smallest complete change" agent rules | MIT | PORT | council voice and MECHANIC.md wording |
| github/gh-aw (living agents) | Markdown agentic workflows, safe outputs, firewall | MIT, preview | PORT | staged mode (PF_COUNCIL_STAGED), in-process host allowlist |
| akitaonrails/ai-memory, vectorize-io/hindsight | agent memory (Git markdown; Postgres + LLM) | MIT | PORT | lesson recall now reaches every tag (11 lessons were never read) |
| paperclipai/paperclip | control plane for agent "companies" | MIT | SKIP now | budgets, shifts, quorum already exist; needs a server |
| anthropics/knowledge-work-plugins | Claude role plugins (triage, digest, memory) | Apache-2.0 | LATER | triage and digest templates for the Runner seat |
| tashfeenahmed/freellmapi | self-hosted free-LLM router (Node, SQLite) | MIT | SKIP dependency | owner may add free Cerebras / Cloudflare Workers AI keys as fallbacks |
| headroomlabs-ai/headroom | context compression library and proxy | Apache-2.0, beta | SKIP now | telemetry beacon on by default; our packs are code and markdown, little to gain |
| mksglu/context-mode | MCP server keeping tool output out of context | ELv2 | SKIP | licence is not open source; idea (compute locally, send results) already used |
| pbakaus/impeccable | frontend design skill and detector CLI | Apache-2.0 | LATER | optional owner-run check of docs/index.html; not in CI (npx download) |
| Copilot coding agent, Claude Code / Codex actions | hosted or paid agents | various | SKIP | no free inference; their controls already mirrored (allowlisted writes, canary, scrub) |
| google-github-actions/run-gemini-cli | Gemini CLI in Actions | Apache-2.0 | SKIP | the gemini seat already uses the free Gemini API |

## Already in place (no change needed)

The council already had the core "living agent" guards the review looked for: an allowlist of
GitHub writes (council.py GH_ALLOWED), a canary token against prompt injection, key scrubbing,
quoted-line verification, uncited answers dropped, redirects kept on the same host, untrusted
text inside JSON-escaped DATA blocks, one seat at a time on a schedule (L039).

## Shipped in W15f

1. Lesson recall: council.py TAG_PATHS; a contract test pins that every LESSONS tag reaches a
   seat (L073).
2. Shift checklists: seats.json `shift.checklist` for Warden and Mechanic.
3. Council voice: "Report a finding only if you would bet on it ... Zero findings is a good answer."
4. Host allowlist in council.http: https to provider hosts and api.github.com only.
5. Staged mode: repository variable PF_COUNCIL_STAGED=1 previews every council write in the run
   summary and posts nothing.

## Not covered

Not adopted as code: none of the repositories runs inside our workflows. openskip (impeccable,
cursor plugin quality gates) and brain (ai-memory) get their own reviews in their own chats.
A seat split into read-only and write jobs (gh-aw safe outputs) is a larger change, kept for later.
