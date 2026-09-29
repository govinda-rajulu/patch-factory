# patch-factory state

Newest checkpoint first. Each section is a dated snapshot; verify live before acting.

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
