# Retention receipts

Deletion receipts for releases, tags, Pages deployment records and branches. Each file is the
owner's own record of one cleanup, copied here byte for byte. Never edit one; a later cleanup
adds a new file. Policy and tool: `src/etc/cleanup.py` (preview, then apply with the token);
boundaries: [RECOVERY.md](../../../RECOVERY.md#cleanup-boundaries).

| File | What it records |
| --- | --- |
| [CLEANUP-2026-09-26.json](CLEANUP-2026-09-26.json) | 26 Sep: 47 old releases and 27 branches deleted by owner approval; tags kept. |
| [CLEANUP-2026-10-07.json](CLEANUP-2026-10-07.json) | 7 Oct: 45 old releases deleted by owner choice; tags kept. |
| [CLEANUP-2026-10-09T134805Z.json](CLEANUP-2026-10-09T134805Z.json) | 9 Oct 13:48 UTC, `cleanup.py apply` token `825ae1379cb2eec9`: 3 releases and their 3 tags deleted (instagram 1, youtube-morphe 1, yt-music 1), with every asset name, size and sha256. |
| [DEPLOYMENTS-2026-10-09T135307Z.tsv](DEPLOYMENTS-2026-10-09T135307Z.tsv) | 9 Oct 13:53 UTC: all 221 `github-pages` deployment records (id, environment, created, commit), newest first. The owner kept the first 5 rows and deleted the other 216. |

Two earlier receipts stay on the owner box only: `cleanup-receipt-20261009.json` (W5, 4
releases and 96 tags) and `cleanup-receipt-20261009T091933Z.json` (W6, 22 releases and 22
tags); their counts are in `../SESSION-2026-10-08.md` and `../SESSION-2026-10-09.md`.
