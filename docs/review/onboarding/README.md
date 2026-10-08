# Onboarding records

Owner rule, 8 Oct 2026 (packet W1): **every new app, provider or patch name goes through
agent review.** Two checks enforce it on any pull request that touches `src/targets.json`,
`src/patches/**`, `src/options/**` or this folder (workflow `Onboarding review`):

1. **Onboarding record** (`src/etc/onboard_check.py`, deterministic, no keys). For each new
   target, each target switched to enabled, each new provider source and each added
   include name, the file `docs/review/onboarding/<target id>.md` must exist and name it
   verbatim. `TODO` anywhere in the record fails. A name that matches `CONFIRM` needs the
   line `Owner approved: <exact name>`. A name that matches `BANNED` always fails.
2. **Agent review** (`src/council/onboard_review.py`). Council seats read the manifest the
   first check wrote and answer approve, changes or block with quotes from it. Pass needs
   at least 2 counted verdicts and fewer than half block. One comment on the pull request,
   edited on every rerun. Fork and bot pull requests fail this step: they get no keys.

Both checks run from the base commit, so a pull request cannot rewrite its own gate.
Removals are listed, never blocked. Neither check builds, merges or publishes; a green
review is not a build, a phone test or the owner's approval.

`5. Add target` (packet W2, `src/etc/app.py`) writes the record from its own inputs: provider,
each added patch name, and `Owner approved:` lines when the owner ticks approve_confirm. It
opens the pull request and starts this review; merging it is the owner's approval. A record
written by hand must still have no `TODO` left. How-to: [docs/APPS.md](../../APPS.md).

## Record template

```
# <Label> (<target id>)

Package: <package>
Source APK: <store and list URL>
Provider: <owner/repo> (licence: <SPDX>, bundle: <release asset pattern>, channel: <stable|prerelease>)

## Patches
- <exact patch name>: <why; which rule or measurement allows it>

## Risks
- <server-visible behaviour, account risk, signature checks>

## Decision
<who decided what, dated>
```

## Records here

| Record | State |
| --- | --- |
| [CANDIDATES-2026-10-08.md](CANDIDATES-2026-10-08.md) | Generated scout of the community index for Amazon Music (`com.amazon.mp3`) and LinkedIn (`com.linkedin.android`). Pick a provider there, then add the app with one "5. Add target" run. |

Records for the 15 current apps are written the first time "5. Add target" changes them.
