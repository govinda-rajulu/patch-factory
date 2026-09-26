# Provider delta review packet: 14-26 September 2026

Consolidates watcher issues #50, #71 and #83 into one review surface. This file
changes nothing: every row is UNREVIEWED until the owner classifies it, and an
added name here is not a selection. Classification column is a mechanical
substring check against `src/patches/BANNED` and `src/patches/CONFIRM` run on
26 September 2026; it is an aid, not a decision.

## Needs a decision before the next mxplayer build

| Target | Delta | Name | List state | Classification |
| --- | --- | --- | --- | --- |
| mxplayer/ftl (#50) | removed | Hide Settings Page UseLess Buttons | **still in include-patches** | applied-count gate will fail if upstream stays removed |
| mxplayer/ftl (#50) | added | Hide Me tab promo items | not selected | no rule hit |
| mxplayer/ftl (#50) | added | Hide local tiles banner | not selected | no rule hit |
| mxplayer/ftl (#50) | added | Skip welcome screen | not selected | no rule hit; possibly a rename of the removed Skip Splash Screen |
| mxplayer/ftl (#50) | removed | Hide top tiles | not in lists | none |
| mxplayer/ftl (#50) | removed | Skip Splash Screen | not in lists | see Skip welcome screen above |

Open issue #49 (MX Player build failure) may already be this applied-count
failure. Check its run's `list-patches` output before editing either list.
Removing a vanished name from include-patches is a selection change and needs
the normal one-target PR with evidence, not a drive-by edit.

## Preserved exclusion (no action, recorded so it is not re-litigated)

| Target | Delta | Name | Position |
| --- | --- | --- | --- |
| youtube/morphe (#50, #71, #83) | added | Remember live stream playback position | **Stays excluded.** Owner exclusion from PR47 stands; the watcher re-reports it because upstream renamed it. The older spelling `Remember livestream playback position` was removed upstream at the same time. |

## Review queue (no rule hits, not in any selection list)

| Target | Issue | Added | Removed |
| --- | --- | --- | --- |
| youtube/morphe | #71, #83 | Channel search; Force fullscreen landscape | (older spelling, above) |
| photos/rushiranpise | #71, #83 | Custom branding | - |
| instagram/piko | #50, #71, #83 | Customize navigation bar | Hide navigation buttons (not in lists) |
| reddit/adobo | #71, #83 | Hide crosspost | - |

## Watch integrity notes

- Paresh GitLab baselines are missing for truecaller (10 names) and mxplayer
  (1 name), reported as "baseline missing", not "all added". Fetch the two
  baseline name lists once, by hand, from the GitLab bundle before the next
  watch comparison is trusted for those two providers.
- Issue #26 (GitLab primary explore report) stays open on purpose: the primary
  GitLab path it exercised is now rejected by design (PF-WIRE-002). A triage
  comment draft exists in the owner packet; closing is the owner's call.
