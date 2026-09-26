# App icon provenance record (26 September 2026)

Status: **no official app artwork ships**. The page uses generated letter monograms, which are
decoration, not logos. This file is the durable record for REQ-027 / R08 so the decision cannot
silently drop again between sessions.

## The gate

An app mark may ship only when all four are recorded here per brand:

1. Source: the exact asset and where it came from (press kit, official repo, or a
   license-cleared set).
2. License/terms: the text that permits redistribution, and whether modification is allowed.
3. Local bundle: the asset lives in `docs/assets/` with its license in `docs/assets/NOTICE.txt`;
   no CDN or hotlink.
4. Owner approval of the per-brand diff.

Anything without all four stays a letter monogram. A refused or removed mark stays generic
forever; it is never replaced by a lookalike.

## Per-brand position

| App | Mark availability | Position |
| --- | --- | --- |
| Microsoft Edge | Microsoft brand assets are request-gated; simple-icons distributes the mark but Microsoft terms require review | **Blocked** until Microsoft terms are read and recorded |
| YouTube, Photos | Google marks carry usage restrictions beyond icon-set licenses | Candidate; Google brand terms must be recorded first |
| AdGuard, Truecaller, Instagram, Facebook, Reddit, Telegram, Prime Video, Hotstar | Marks exist in license-cleared icon sets (e.g. simple-icons, CC0) | Candidate; per-brand source + license still to be recorded |
| ES File Explorer, MX Player, KeyMapper | No known license-cleared mark located | Unavailable; monogram stays |

Note: an earlier chat estimated "7 cleared via simple-icons CC0" but the per-brand record was
never written down, so that estimate is not evidence. This table replaces it: nothing is
"cleared" until rows 1-4 above are filled per brand.

## What generic assets do ship now

Manrope (OFL) and Heroicons (MIT), bundled locally with `docs/assets/NOTICE.txt` (PR61).
Those cover typography and UI symbols only; they are not app logos and must not be presented
as such.
