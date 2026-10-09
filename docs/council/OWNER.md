# Owner

The owner architects this project and makes every decision below. He has no coding
background: he cannot catch a wrong edit by reading it, so gates and tests are the only
quality control. Treat every claim as unverified until a command or test output shows it.

## What he wants from this repo

- New patched builds of his configured apps **only when a provider publishes something new**.
- Apps his own phones install through Obtainium, with no server-visible patch that risks an account.
- Less reading: short, decided recommendations with evidence, not option lists.

## How to answer him

- Action first, shortest form. Explain only when asked.
- Own a mistake in one line and keep a count. Never defend a call; re-derive it.
- Recommend one option and say why. Offer alternatives only if they change the outcome.
- Anything he runs must be a whole command he can paste, or say plainly that there is nothing to run.
- If his pushback seems to reject a correct analysis, the delivery was probably wrong. Remove a step.

## Decisions only the owner makes

Council votes are recommendations. These stay with the owner:

- Adding, removing or promoting a provider or bundle; changing a channel, pin, ceiling or source.
- Adding a patch to, or removing it from, any include/exclude file; every `CONFIRM` decision.
- Enabling a target, retiring one, or rebuilding a retired one.
- Dispatching a build, publishing, deleting a release/tag/branch/artifact, cleanup of any kind.
- Signing, secrets, repository settings, merging a PR.

## Standing decisions to preserve

Read the current files; these are pointers, not copies.

- YouTube excludes exactly **Remember live stream playback position** (PR47). GmsCore support,
  PoToken provider and Spoof video streams are owner-approved there.
- ES File and MX Player exclude APK Junk Cleanup, Remove Duplicate Graphics and Remove Languages
  in each ftl bundle (`docs/review/RESOURCE-DECISION-2026-09-19.md`).
- Remove Debug Info is quarantined: mitigated, not proved fixed upstream.
- SonyLIV/ZEE5 and standalone Truecaller are retired. Since 9 Oct 2026 the only Truecaller is `tc-combo`; the standalone `truecaller-v26.10.6` release is removed by cleanup.
  `src/patches/_attic` stays.
- Extras are not fallback candidates. Provider age is advisory, never a kill switch.
- Configured, applied, approved and published are four different states. Approval is not completion.

## Risk posture

- A patch a server can see does not ship.
- Prefer an issue to a speculative change: an issue costs a read, a bad build costs a reinstall and maybe an account.
- No "zero risk", "all safe" or device-compatibility claims without device evidence.
