# App icon provenance record (26 September 2026, reviewed 27 October 2026)

Public policy (current; owner decision 6 Oct 2026, reaffirmed 27 Oct 2026): app cards show the app's **official icon**, from its official store listing (Google Play CDN) or official site, or an open-licensed official mark. Icons are identification aids, not endorsements: bundled locally (the page never hotlinks third-party images), trademark of their owners, removed on request from a mark's owner. Badges are CSS/text labels. The dated sections below are history; the current inventory is in the 28 October 2026 (W16w) section at the end.

Status (6 October 2026): **brand tiles ship for 11 apps**, each with all four gate items below
recorded; every other card keeps its letter monogram. 26 Oct 2026: 11 app tiles ship
(docs/assets/logos/, the LOGOS set in docs/portal.js), the later ones from the owner-supplied
table below; ES File is not among them and still shows its monogram. This file is the durable record for
REQ-027 / R08 so the decision cannot silently drop again between sessions.

## Shipped tiles (6 October 2026)

Owner approval: given in chat on 6 October 2026 ("use official site and wikimedia and any
open-source places"). Sources, licences and hashes: `docs/assets/NOTICE.txt`. The page loads
only these local files; a missing file falls back to the monogram.

| Target | Source | Licence on source page |
| --- | --- | --- |
| `youtube` | [File:YouTube full-color icon (2017).svg](https://commons.wikimedia.org/wiki/File:YouTube_full-color_icon_(2017).svg) | Public domain, trademarked |
| `ytmusic` | [File:Youtube Music icon.svg](https://commons.wikimedia.org/wiki/File:Youtube_Music_icon.svg) | Public domain, trademarked |
| `facebook` | [File:2023 Facebook icon.svg](https://commons.wikimedia.org/wiki/File:2023_Facebook_icon.svg) | Public domain, trademarked |
| `instagram` | [File:Instagram logo 2016.svg](https://commons.wikimedia.org/wiki/File:Instagram_logo_2016.svg) | Public domain, trademarked |
| `telegram` | [File:Telegram logo.svg](https://commons.wikimedia.org/wiki/File:Telegram_logo.svg) | Public domain, trademarked |
| `photos` | [File:Google Photos icon (2020).svg](https://commons.wikimedia.org/wiki/File:Google_Photos_icon_(2020-2025).svg) | Public domain, trademarked |
| `primevideo` | [File:Amazon Prime Video logo (2024).svg](https://commons.wikimedia.org/wiki/File:Amazon_Prime_Video_logo_(2024).svg) | Public domain, trademarked |
| `adguard` | [File:AdGuard Logo.png](https://commons.wikimedia.org/wiki/File:AdGuard_Logo.png) | Public domain, trademarked |
| `keymapper` | GitHub keymapperorg/KeyMapper, branch develop, app/src/main/ic_launcher-playstore.png | GPL-3.0 repository; app mark |
| `reddit` | [File:Snoo.svg](https://commons.wikimedia.org/wiki/File:Snoo.svg) | Public domain, trademarked |
| `truecaller-combo` | [File:TrueCaller Icon.png](https://commons.wikimedia.org/wiki/File:TrueCaller_Icon.png) | CC BY-SA 4.0 |

Still a monogram on 6 October: ES File Explorer (no open-licensed official mark found), MX Player
and JioHotstar (only wide wordmarks or a retired Disney+ Hotstar mark on Commons), Morphe MicroG RE
(Morphe branding is not open-licensed: **Blocked**). The section below supersedes this for the
first three. The 26 September table below is history.

## Official source links for public users

These links identify the upstream app pages. They are documentation links only; the portal does not
hotlink third-party artwork. The safest fallback for an app mark without recorded redistribution terms
is the portal's letter monogram.

| App | Official page |
| --- | --- |
| Amazon Music | [Google Play](https://play.google.com/store/apps/details?id=com.amazon.mp3) |
| LinkedIn | [Google Play](https://play.google.com/store/apps/details?id=com.linkedin.android) |
| JioHotstar | [Google Play](https://play.google.com/store/apps/details?id=in.startv.hotstar) |
| MX Player | [Google Play](https://play.google.com/store/apps/details?id=com.mxtech.videoplayer.ad) |
| MicroG RE | [MorpheApp/MicroG-RE](https://github.com/MorpheApp/MicroG-RE) |
| Obtainium | [ImranR98/Obtainium](https://github.com/ImranR98/Obtainium) |

## Withdrawn owner-supplied store icons (not shipped)

These owner-supplied store icons are withdrawn from the public bundle because redistribution
permission was not recorded. The rows remain only as provenance history; the portal uses monograms. The packet controller fetched each file on the owner's machine; a tile ships only if
its file passed the PNG gate (PNG signature, 16 to 512 px, under 64 KB). Its hash is in
`docs/assets/NOTICE.txt`; a tile that failed keeps its monogram and is named in the PR.

| Target | Source the owner supplied | Licence |
| --- | --- | --- |
| `microg` (upstream companion card, `docs/assets/microg.png`) | MicroG RE icon from APKMirror's upload area, uploaded by the owner in chat, 8 Oct 2026; stored locally so the page never loads a third-party image | None recorded; identification only |
| `amazonmusic` | Google Play icon for Amazon Music (`com.amazon.mp3`), uploaded by the owner in chat, 8 Oct 2026 | None; trademark, identification only |
| `linkedin` | Google Play icon for LinkedIn (`com.linkedin.android`), uploaded by the owner in chat, 8 Oct 2026 | None; trademark, identification only |
| `hotstar` | Google Play icon for JioHotstar (`in.startv.hotstar`), play-lh.googleusercontent.com `02xiO0pt...` | None; trademark, identification only |
| `mxplayer` | Google Play icon for MX Player, play-lh.googleusercontent.com `pL-FlnQw...` | None; trademark, identification only |
| `esfile` | Uptodown icon for ES File Explorer, img.utdstc.com `icon/826/725/82672572...` (not bundled as of 26 Oct 2026: no docs/assets/logos/esfile.png) | None; trademark, identification only |

## 26 September 2026 record

Status then: no official app artwork shipped.

## The gate

Written 26 Sep. Since 6 Oct (section above) the owner also ships store icons he supplied, with the
licence item recorded as "None; trademark, identification only"; that is his exception to item 2.

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

As of 26 Sep; superseded where the two sections above ship a tile (11 tiles on 27 Oct 2026, ES File
still a monogram).

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

## 27 October 2026 (W16v): owner decision restored

W16u (27 Oct, wrong call 95) withdrew five owner-approved tiles (Amazon Music, LinkedIn, JioHotstar,
MX Player, Edge) as unlicensed, against the owner's 6 Oct decision; the owner restated it on 27 Oct
("take online pics of app icons from official sources"). W16v restores the five files byte for byte
from git history (sha256 in `docs/assets/NOTICE.txt`) and puts them back in the LOGOS set.

Current inventory: **16 tiles** (adguard, amazonmusic, edge, facebook, hotstar, instagram, keymapper,
linkedin, mxplayer, photos, primevideo, reddit, telegram, truecaller-combo, youtube, ytmusic). ES File
Explorer keeps its monogram until its fetched icon passes the gate. This section supersedes the
"Withdrawn" heading above and the "Blocked" (Edge) and "Unavailable" (MX Player, Key Mapper) rows of the
26 September per-brand table.

## 27 October 2026 refresh queue (owner-supplied official URLs)

The owner supplied these official icon URLs on 27 Oct 2026. Probe P2 (W16v combo) fetches each on the
owner's Cloud Shell (https, hosts play-lh.googleusercontent.com and img.utdstc.com only, Google Play
size suffix `=w240-h480`, 2 MB cap, PNG/JPEG/WebP magic, sha256 and size recorded in `icons/icons.json`).
W16w records the result after the visual check and PNG gate (PNG, 16 to 512 px, under 64 KB);
hotstar and mxplayer came from the same URLs as the shipped tiles.

| Target | Official source |
| --- | --- |
| `amazonmusic` | https://play-lh.googleusercontent.com/9v2z1-7g8pWbxek8IW3Q9gGsAqD-YkTvy_rmyd4Cfb-OkpVR2T6jt-Ev2eKDcvx72njhCQ_4fEd9qg8-T9AaDA |
| `hotstar` | https://play-lh.googleusercontent.com/02xiO0ptbXjD8NR3sbS2StP1P9aytDN56dDR15zqM_i66Vwq5W_hD-98CoFxvRVoUS4uV_xMSv-iQh3nQFeDeQ |
| `mxplayer` | https://play-lh.googleusercontent.com/pL-FlnQwdyKetEhT_Uzre61MnGKhMgLC7wnV12KgC_wrQbU0UbSkYs4T5fQQWL_QLZZ48fl1mBmN-cNbc1wSZA |
| `linkedin` | https://play-lh.googleusercontent.com/oij55bxj3e-4JrhGntpki0lnQyE8yQn8X5FPEzZ0t7cLppeiSINynEk7n9COoh7QSaCOZ_yiPO31NVaW4SDbWg |
| `reddit` | https://play-lh.googleusercontent.com/8FVS0kvM60JwqZWRNzBIlwrZZxJa8vpli8IWaaTo8QXRe1PHmCNJ8UpWoXkGPV3jKEaTY2OVAeYoisOnGJXY |
| `ccleaner` (disabled target) | https://play-lh.googleusercontent.com/4TzP6UEY4IJCNntREn5fm1eojCC1MeBvR5B2Hl2-IICBAtU8HT5HrM1wcruwtLbVCQbfezTbonVbv-pgf8-UUg |
| `esfile` | https://img.utdstc.com/icon/826/725/82672572ac96972a9e4e56717258c0651d296e707ae49309ce6bf81630ce3159 |
| `edge` | https://play-lh.googleusercontent.com/4Z1Nt1I9HUDevt5VJ7BmgpqSTUpsC0Ei1K-IiXSmkH5Dzorz_isDzq4qdpb75RA1SfOV7v6csav-atWBur1wJQM |
| `photos` | https://play-lh.googleusercontent.com/kErBTF4VcGwhtKbCr80Bs2R1lNZiYkHbKcf1i3ZF6dg_5LqDAlCI4wU-nzwvo7PAbxeBXM_tv1hc11gr4aIIW-Q |

Conversion (W16v review): JPEG or WebP fetches are converted to PNG and resized before the gate; the original bytes and sha256 stay in `icons/icons.json` for provenance.

## 28 October 2026 (W16v): refresh shipped

Probe P2 fetched 8 of the 9 owner URLs (ES File on Uptodown answered an HTTP error; its tile stays a monogram). Hotstar and MX Player came back byte for byte the shipped tiles. Amazon Music, Edge, LinkedIn, Google Photos and Reddit now ship the 240 px Play icons (PNG, under 64 KB, checked by eye); sizes and sha256 in docs/assets/NOTICE.txt. CCleaner is a disabled target and gets no tile.

## 28 October 2026 (W16w): ES File and CCleaner

Probe P2 of 27 Oct 19:17 UTC fetched all nine owner URLs. ES File ships as a PNG converted from Uptodown's 100 px JPEG; CCleaner ships the Play 240 px PNG unchanged (the store image carries a "2026" badge) and shows once the target is enabled. Both checked by eye; sizes and sha256 in docs/assets/NOTICE.txt.
