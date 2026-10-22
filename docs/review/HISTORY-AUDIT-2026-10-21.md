# History audit, 21 October 2026 (packet W15d)

Owner ask (21 Oct): look back through the repository's past for anything dropped or missed.
An agent read every checkpoint, session, audit and lesson; each "dropped" claim below was then
checked against the file it names before a disposition was written (L068). Agent claims that
did not survive that check are marked REFUTED.

## Dropped items, checked

| Item (first seen) | Checked against | Disposition |
| --- | --- | --- |
| ci.yml resolve `continue-on-error` (OPEN-WORK 7 Oct) | `.github/workflows/ci.yml` resolve job | By design: its comment says a resolver failure is UNKNOWN evidence and the report lists the rest as UNKNOWN, never unchanged. Kept; closed. |
| Manual Patch `shadow_plan_required` default false (AUDIT-COUNCIL 6 Oct) | `manual-patch.yml` input | By design: a manual build has no daily Plan; the input exists to tell the two apart. Closed. |
| Nightly watch job timeout (AUDIT-COUNCIL 6 Oct) | `watch.yml` line 17 | REFUTED: `timeout-minutes: 45` since commit 2e2bc7e (W2, 8 Oct). Closed. |
| Watch artifact integrity check (AUDIT-COUNCIL 6 Oct) | `watch.yml` upload step | Nothing downloads that artifact automatically; the report is read on the issue. No consumer, so no check to add. Closed. |
| Regenerate `UNREVIEWED.tsv` (OPEN-WORK 9 Oct, W9) | `docs/review/UNREVIEWED.tsv` (6 Sep, 102 `?` rows) | Superseded: since W15b the Selection watch adopt rule (src/patches/ADOPT.json) decides new names and the standing issue lists the held ones with their reason. Retire or regenerate it in W15f, where the combo planner reads every provider. Carried to OPEN-WORK. |
| Close or carry `PROVIDER-DELTAS-2026-09.md` (OPEN-WORK 9 Oct) | that file, docs/review/providers/ | Closed by a correction note at its top (this packet): its last open note is resolved. |
| Paresh GitLab Truecaller and MX baselines (AUDIT-5S 27 Sep) | `docs/review/providers/paresh-*.names` | Done in W11 (2ea1690, 9 Oct): truecaller 10 names, mxplayer 1. Closed. |
| CodeRabbit advisory review (ROADMAP 1 Oct) | repository root, knowledge/handbook/AGENT-TOOLING.md | Not set up: it needs the owner to install the CodeRabbit GitHub app; then a `.coderabbit.yaml` (advisory, never required). Owner option, carried. |

## Owner rules still not enforced by code

Recorded so they are not lost; each waits on the owner or on data the repository cannot read.

- Amazon Music paid names: throwaway account only, never the main account (no phone or account gate exists).
- Facebook cleanup only after the 583 phone install; a split is dropped only after a phone test.
- HushGram as Instagram primary only after HushGram 0.1 and a HushFacebook phone test.
- TDL_BACKUP secret deletion, the Actions pull request setting, branch protection: GitHub
  settings no code here can read.
- pf-vault before backups (owner creates the repository and token first).
- Official app artwork needs a provenance review (ICON-PROVENANCE.md).

## Still open (carried in OPEN-WORK, oldest first)

PR53 disposition (26 Sep); F05/F06 fingerprints (26 Sep); ES File logo (6 Oct); portal SRI
(6 Oct); agent runner pilot (7 Oct); CLUTTER sections 1, 3 and 4 (7 Oct); TDL_BACKUP delete
(7 Oct, owner); Amazon Music keep or disable (9 Oct); Obtainium re-import (17 Oct, owner);
Facebook 583 install then cleanup (17 Oct, owner); council served-model probe (17 Oct);
combos, Truecaller measured, pf-vault (20 Oct); signing isolation, tool pins, AUDIT 4, speed,
community summary (21 Oct).

## Lessons that keep coming back

L005 (four states: configured, applied, published, phone-tested), L013 (missing is UNKNOWN),
L029 and L035 (a failure must show its reason), L034 (rehearse the exact controller), L036
(merged is not built), L056 (a plan in a doc is not work), L061 (never suppress), L066 (a
fail-closed rule is checked on every path).

## What this audit could not cover

Issue and pull request states (the audit read repository files only); owner-side phone tests,
cleanup applies, Obtainium and secret deletion have no receipts in the repository.
