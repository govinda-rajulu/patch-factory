# patch-factory roadmap

Updated 26 October 2026 (W16m, chat handover). This is a short planning view, not a second source of
truth. `src/targets.json`, the workflow files, `src/council/seats.json` and the newest
[STATE.md](STATE.md) checkpoint win over this file. Owner rules and the live queue are in
[AGENTS.md](../AGENTS.md) and [OPEN-WORK.md](../docs/review/OPEN-WORK.md).

## Current system to preserve

- The generated README inventory covers 17 enabled apps (CCleaner is listed but disabled). Providers, fallbacks, stores and poll
  flags come from `src/targets.json`; run the generators instead of hand-editing their outputs.
- Scheduled automations and IST times come from `.github/workflows/` through
  [`schedules.py`](../src/etc/schedules.py) and [SCHEDULES.md](../docs/SCHEDULES.md). The old
  keepalive cron is gone; `keepalive.yml` is manual only.
- `Needs you` runs daily at 10:29 IST. It joins the five watch reports and accepts the owner's
  `take` (or `keep`), `drop` and `hold` by item id, group id or `all`, and `yes all` (src/etc/needs_you.py). Provider `take` runs Explore; review effects are
  recorded on the review issue; other decisions go to the watch-state ledger.
- Status page data includes stale Actions-cache pruning. It keeps the newest cache in each
  conservative key-prefix group and removes only old, unused non-newest caches.
- The council has nine seats on eight providers, with personas and shifts defined in
  `src/council/seats.json` (solo shifts run only on request since W16k). Keep [PERSONAS.md](../docs/council/PERSONAS.md), [SETUP.md](../docs/council/SETUP.md)
  and the roster aligned with that file.

## Now: owner work

Follow the newest [OPEN-WORK.md](../docs/review/OPEN-WORK.md) checkpoint. The current first items
(26 Oct) are W17 owner-only Add app and W18 combo planner
([W17-BRIEF.md](../docs/review/W17-BRIEF.md)), the W15g signing split, owner decisions in Needs
you, phone checks and one manual run of the read-only MCP scout (store services already start on
demand, W16g L087). The MCP plan is [MCP-PLAN.md](../docs/review/MCP-PLAN.md); it adds no schedule and must not
replace deterministic store scraping or feed model output into a build.

## Security and maintenance lanes

- Keep the read-only security review focused on `.github/workflows/`, `.github/actions/`, the
  fetchers under `src/build/` and the council code and prompts. Do not refer to the removed
  `src/build/helper/ggplay_dl/` helper or the nonexistent `src/council/AI-AND-LLM.md` file.
- Keep the generated README, Pages catalog, Obtainium imports, credits and schedule table under
  their existing generator checks. A source change is incomplete until its generated outputs and
  the full suite agree.
- Keep one owner-reviewed packet in flight. No workflow, signing, release, target or patch change
  belongs in this roadmap without an approved packet.

## Parking lot

- Weekly read-only provider research through the existing Community watch lane, only after the
  MCP pilot is proven. Candidates go to Needs you; deterministic `list-patches` remains the
  authority.
- Council and agent-runner improvements that have an owner-approved packet and a concrete test.
