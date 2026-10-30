# Owner decisions, 30 October 2026 (W16y)

These are the owner's decisions recorded on 30 October 2026. W16y is split into
**W16y-a** (this packet) and **W16y-b** (provider gate, digest, pin check, Council
report and Telegram survey).

## Decisions for the operating watches

- Run a weekly pin check, but only for apps whose patches rely on the pin.
- Keep Amazon Music's paid patches and keep the target in `paid_ok_targets`.
- Turn the Obtainium signer pin off for Android 10, with the first-install note; filing the upstream issue is optional.
- Use a 50% coverage floor versus the last primary build for fallbacks. Combined non-Hush fallbacks may run on one app version; Hush is never mixed with non-Hush.
- Label fallback releases everywhere: banner, metadata, portal badge and status tag. Do not label prereleases as fallbacks because Obtainium skips prereleases.
- Leave the near-version rule unchanged.
- Treat patch age as a 180-day warning only, shown on portal cards.
- Send watched providers a monthly digest; never auto-adopt their changes.
- Retention is a weekly preview followed by owner-token apply. Keep the three newest releases per app; when none of them is a primary build, also keep the newest primary (so a fallback run leaves 1 primary plus the 2 newest fallbacks at least); never delete the newest and never delete anything under seven days. Pages keep three. The first apply is after Monday, 2 November 2026.
- The Council model report runs weekly. Model swaps happen by pull request only.
- The switch audit is warn-only.

## Telegram and new providers

- Survey Telegram first. Hush may become Telegram primary if the non-Hush groups remain far below it. Hush API keys are interactive-only and must never be stored.
- New providers may be auto-discovered and scanned for permission differences, new domains, code red flags, ClamAV findings and, optionally, a VirusTotal hash lookup using an owner key. A green test build makes a ready PR; the owner taps merge.

## Owner actions completed on 30 October

- Secret scanning and push protection are on.
- `TDL_BACKUP` was deleted. It was a Telegram TDL session backup from the original template and had been unused since W15.
- The merged CCleaner branch was deleted.
- The old Cloud Shell username remains in history; rewriting it would break 43 release tags.
- Keystores in early history are public template keys, not the live signer. Their fingerprints are `860dac27…`, `d1bb6d4f…` and `b1901f35…`; the live signer is `08480f66…`.
- The Council portal audit's “CI_CERT exposed” finding was re-rated: the public signer fingerprint is exposed by design.

## Packet split

**W16y-a (this packet):** history and documentation cleanup, dead selection utility removal,
Android 9/10 signer guidance, ignore rules and the W16x wrong-call record.

**W16y-b:** provider gate, monthly digest, weekly pin check, weekly Council report and the
Telegram survey.
