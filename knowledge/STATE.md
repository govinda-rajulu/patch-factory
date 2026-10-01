# patch-factory state

Newest checkpoint first. Each section is a dated snapshot; verify live before acting.

## 1 Oct 2026, packet P

- **main**: PR122 (roadmap docs) on `2b58d78b`, then packet P: `De-Vanced Settings` dropped
  from Facebook's include list. Cause and limits: `docs/review/FACEBOOK-580-2026-09-29.md`.
- **Same controller (`pf-packet-p-v1`), each step behind its own gate**: merge Dependabot #103
  (setup-java 6.0.1, refs only); close the Facebook run records whose only failure is Patch apk
  (#109, #115 to #121 when written) as covered by #105; close #98, #101, #104 on the published
  Prime Video 3.0.470.357; close #106; close #99 on a green Nightly after 29 Sep. The run's
  ledger line in `~/work/run-ledger.txt` says which steps ran.
- **Left open**: #105 until a green Facebook build; #114 (its 29 Sep YouTube failure is
  undiagnosed); #102; Edge apkpure refusal; F05/F06; YouTube's two new patch names.

## 1 Oct 2026, 01:30 IST (planning only, no code)

- **main** `2b58d78b` (PR113 packet O), unchanged.
- **Scheduled runs on 30 Sep**: Facebook failed at Patch apk twice (#118, #119). YouTube
  21.39.522 was republished by run 36716967959 with two newly applied patch names (Playback
  buffer, Restore original titles); owner to confirm they were expected.
- **New**: [ROADMAP.md](ROADMAP.md) and [handbook/AGENT-TOOLING.md](handbook/AGENT-TOOLING.md)
  (1 Oct tool review). No workflow, selection or code change.

## 29 Sep 2026, 13:50 IST

- **main** `6af68340` (tree `90d7786a`): PR112 (the 13:45 checkpoint below and lessons 4 to 6
  in `LESSONS.md`) on PR110 `f2a31fee` (this folder) on PR111 packet N `5301b5c8`, which
  sits on PR108 packet M and PR107 packet L.
- **Facebook variant lead, unproven**: the 580 input was version code 475019268, but
  `docs/review/FACEBOOK-580-2026-09-29.md` records 475019344 as the ARM64 build the new
  patches target. Same version name, different build. The `FdsContextColor580Fingerprint`
  failure may come from the variant, not the patch selection. Check the variant before
  changing patches.
- **Next**: (1) Facebook: confirm the downloaded variant and which selected patch depends
  on the AMOLED theme patch. (2) Edge: why the shadow apkpure bundle fetch refuses in 23 s
  while real Edge builds publish. (3) With owner OK, close #98, #101, #104 on the Prime
  build; #105 after Facebook builds; #99 after the next Nightly. Then #102, #103, F05/F06,
  PR53.
- **Notes**: packet O's controller prints its real base in MAIN_MOVED (the 13:45 cosmetic
  item). Scheduled runs started about five hours late on 29 Sep; a manual dispatch (owner
  OK) gets evidence quickly. The 29 Sep packet ledger is `~/work/pf-archive/LEDGER.txt`;
  later scripts use `~/work/run-ledger.txt` per WORKING-AGREEMENT.md.

## 29 Sep 2026, 13:45 IST (end of the packet N session)

- **main**: PR111 packet N merged as `5301b5c8` (tree `fd6d4d01`): session record, OPEN-WORK,
  review desk house rules 5 to 7, lesson L036. Then PR110 merged (this `knowledge/` folder).
- **Run 36534562050 shadow reasons**, read from the saved job log (owner copy:
  Cloud Shell `~/work/pf-archive/run-36534562050-reasons.txt`):
  - **Edge**: `source inputs failure: existing store fetcher refused (exit 1 after 23s,
    source apkpure, type bundle)`. The shadow resolver was offered a bundle and refused it.
    Open question: should the shadow path accept bundles? Real Edge builds are a separate path.
  - **Facebook input**: 580.0.0.51.74, code 475019268, 90,549,610 bytes. Right version name,
    unproven build: `docs/review/FACEBOOK-580-2026-09-29.md` names code 475019344 (ARM64) as
    the target of the new patches, so this may be a different variant (see 13:50 above).
    The patch-time failure (`FdsContextColor580Fingerprint` in the AMOLED theme patch, pulled
    in by one of the four chosen patches) is still open. Nothing was published; the phone
    stays on 490.
  - **Prime Video input**: 3.0.470.357, code 470000357. Built; not phone-tested.
  - **AdGuard**: 4.14.68, pinned to rushiranpise as intended.
  - Also observed: esfile 4.4.3.7, hotstar 26.06.08.2, instagram 439.0.0.37.89, keymapper
    4.2.1, mxplayer 1.93.4, photos 7.92.0.977185651, reddit 2026.38.0, telegram 12.10.1,
    truecaller-combo 26.10.6, youtube 21.39.522.
- **Next**: find which chosen Facebook patch depends on AMOLED; decide on bundle handling for
  Edge; close #98, #101 and #104 with the Prime build as evidence (owner OK needed). Then the
  rest of `docs/review/OPEN-WORK.md`.
- **Council**: the PR110 review got 4 of 6 seats (mistral 404, gpt unavailable). Check seats.
- **Cosmetic**: packet N's MAIN_MOVED message still names `93fc2b98`; fix in the next packet.
- **Cloud Shell cleanup done**: packet L v2 and M clones removed, their controllers deleted,
  ledger line in `~/work/pf-archive/LEDGER.txt`; the stopped L v1 folder and the ~1000 MB
  artifact zips are kept (owner decides later).

## 29 Sep 2026, 12:30 IST

- **main** `1b8e42c3` (tree `1ae504b4`): PR108 packet M merged 06:53Z (council lessons
  L028 to L035 and `docs/review/SESSION-2026-09-29.md`). Its parent `90e12e57` is PR107
  packet L (poll pin, Prime Video `release=NNN`, Facebook 580, nightly name check, council
  j4, shadow reasons). Full detail: `docs/review/SESSION-2026-09-29.md`.
- **Next**: first post-merge evidence (Prime Video build, Facebook 580 build, Edge's printed
  reason, AdGuard not rebuilding on prereleases). Then close #98, #101, #104, #105 with that
  evidence and #99 after the next Nightly. Then #102 (provider watch blind to universal
  patches), Dependabot #103, F05/F06 full fingerprints, PR53.
- **Council**: six free seats, advisory comments only; GitHub Models is retired (its endpoint
  answers a bare "OK"; never seat it). Free model catalogues churn; check the provider's
  deprecation page before debugging transport.
- No issue writes, dispatch, cleanup, settings, signing or selection change without fresh
  owner approval.

### Owner-side material that is deliberately not in git

- Signing backups: owner-held copies (restore untested). Never commit or request them.
- Cloud Shell `~/work/pf-archive/` (moved 29 Sep, index `INDEX-20260929T065453Z.txt`):
  executed controllers, their RESULT files and work folders, `pf-backup-*.tar.gz`, the
  original MX APK, and `pf-evidence-review-gaj8a7s5` (about 1000 MB of downloaded Actions
  artifact zips; some may be the only copies of builds whose releases were deleted).
  Binaries never go into git; deleting them is an owner decision.

## Before 29 Sep 2026

See `docs/review/HANDOVER-2026-09-26.md`, `docs/review/OPEN-WORK.md` and
[archive/skills/PATCH-FACTORY-BUILDS.md](archive/skills/PATCH-FACTORY-BUILDS.md).
