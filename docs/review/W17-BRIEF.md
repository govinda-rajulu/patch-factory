# W17 brief: owner-only "Add app" from Pages (plan, 26 Oct 2026)

Owner idea, 25 Oct 2026 22:13 IST: an option on the page to search and add a new app, with only the
owner able to use it; candidates are found and kept for his decision; nothing breaks or merges until
every check is green; the built app shows on Pages by itself. "So I have only few works to do."
Not started. This is the plan the next chat builds from; change it with the owner first.

Naming (26 Oct, wrong call 69): on 25 Oct the records already used "W17" for the **combo planner**
(SESSION-2026-10-25 "Open after W16j"; earlier "W15f combo planner", 21 Oct), and the W16l records
then gave W17 to this Add app flow without noticing. From here on W17 is this brief and the combo
planner is **W18** (section "W18 combo planner" below). Older records keep their old labels.
Both need the same provider finder (step 2 of the flow): build it once in W17 so W18 reuses it.

## What exists today

- `5. Add target` (workflow_dispatch, src/etc/app.py add) writes the target, patch folders, options,
  onboarding record and card line (W16l: the patch names), then opens a bot pull request.
- `Explore` lists a provider's patches for one package into an issue (list-patches).
- Needs you holds paid or unsure names for the owner; DECISIONS.json remembers his calls.
- A bot-created pull request does not trigger checks by itself (L069). `5. Add target` therefore
  dispatches `3. Validate` on its branch and `Onboarding review` for the pull request. No smoke
  build runs, so today the owner merges by hand after a manual provider-named smoke. CCleaner
  (#254) went this way and needed three controller runs.

## Who can use it

- Pages stays public and read-only. It holds no token and calls no write API.
- Planned: a Pages "Add an app" link that opens the GitHub dispatch form of one workflow. It does
  not exist yet; today's portal is read-only with no dispatch (docs/portal.js). GitHub only lets
  people with write access run it, so only the owner can. Anyone else sees the form but cannot run it.

## Flow (one form, then hands off)

1. Form fields: app name or package; optional store link; optional group (default tools); optional
   provider (blank = choose automatically).
2. Find providers: official Morphe bundle first, then src/community/bundles.json entries for the
   package; rank by newest app version that fits the phone (arm64, Android 10, the W16k picker),
   then most patches. Keep the top 3: one primary, the rest fallbacks. The controller refuses more
   than 2 SMOKE entries per app at its gate (SMOKES_PER_APP, W16k: Manual Patch keeps one running and
   one pending run per app), so smoke the primary and the first fallback; a third provider is not
   written as a fallback until its own named smoke passes in a later run.
3. List patches live (list-patches) for each kept provider. Default-on names are chosen; BANNED
   never; CONFIRM and paid names go to Needs you unless the app is in paid_ok_targets with an
   Owner approved line.
4. (To build.) Check the provider's open issues for the package and version (L100): the GitHub
   issues API of the provider repository, searched by package and app name. Write a "Provider issues:" line (none, the
   issue links, or "unable to check" when the API fails; never "none" on a failure) into the
   onboarding record.
5. Write the target with app.py add (record, card line, group, logo rule from ICON-PROVENANCE),
   open the pull request.
6. Test builds with the provider named (app/provider): pass only when that provider wins (L098).
   A failing name is listed (keep-going) and held, not shipped.
7. Merge only when Validate, the Onboarding record and every named smoke are green. Then publish
   that one app; Pages and the Obtainium import pick it up from the merge.
8. Anything that cannot pass waits in Needs you with the reason, and the app stays disabled.

## Open design questions (decide before code)

- Smoke builds on a bot pull request (L069): Validate and Onboarding review are already dispatched
  by `5. Add target`; the provider-named smokes are not. Dispatch them from the add workflow too, or
  use a token that triggers workflows (owner decision: no new secrets without him).
- Who merges and publishes: today only the owner merges, and publishing is his call. Auto-merge
  after green is a change to the house rule "no automatic merge", and an automatic publish of the
  new app (the idea asks for Pages to show it by itself) needs his explicit yes too.
- Logos: a new app has no brand tile (CCleaner); monogram until ICON-PROVENANCE admits one.

## Controller defaults for the W17 packet (change with the owner)

- Smokes: the add flow's own rehearsal plus one real provider-named smoke; RUN_T1 off unless the
  owner asks (W17 changes no build path).
- Publish: none by the controller; the owner's answer to "who merges and publishes" decides.

## Acceptance

- A dispatch by a non-owner is refused by GitHub (documented, not simulated).
- Rehearsal with the fake GitHub: happy path, the named provider loses to a fallback (must STOP,
  L098; not an advisory smoke), a paid name waits, a broken
  provider bundle (CCleaner 25 Oct) ends disabled with the reason, a rerun does nothing twice.
- First real use: CCleaner after MightyMichs fixes issue #18.

## W18 combo planner (owner idea, W16j; not designed yet)

For each app: every provider that fits the phone, names deduplicated by description, one build per
combination in parallel, keep the highest app version with the most patches. Needs one app version
that every bundle in the combo supports and a phone test per combo. First data from 21 Oct: MX Player
2.2.4 with FTL plus MightyMich "Unlock MX Player Pro"; ES File plus rushiranpise "Unlock VIP Lifetime"
(shipped as an extra in W16h). Also from 21 Oct: must-have names per app and a "missing this build"
line on the shelf. Tied to ceiling memory for LinkedIn step-downs (W16c audit: the only open cause of
LinkedIn red runs).

## After W17

W18 combo planner (above), then W15g signing split ([SIGNING-SPLIT.md](SIGNING-SPLIT.md)). The owner
may reorder.
