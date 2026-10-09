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
| [CLEANUP-2026-10-09T180442Z.json](CLEANUP-2026-10-09T180442Z.json) | 9 Oct 18:04 UTC, `cleanup.py apply` token `33c8fa6aee71414a` (W9 tool): the plan was 1 release, 1 tag, 1 Pages record, 1 branch. Deleted: release and tag `key-mapper-v4.2.1-b20260907`. Stopped at the Pages record (HTTP 422: still active); `packet/w9` was not tried. Fixed in W10. |
| [CLEANUP-2026-10-09T185533Z.json](CLEANUP-2026-10-09T185533Z.json) | 9 Oct 18:55 UTC, token `3a47ff61760a324a` (W10 tool): RESULT OK. Deleted the retired standalone `truecaller-v26.10.6` release and tag (one Truecaller: `tc-combo`), 2 Pages records (each marked inactive first) and branches `packet/w9` and `packet/w10`. |
| [DEPLOYMENTS-2026-10-09T135307Z.tsv](DEPLOYMENTS-2026-10-09T135307Z.tsv) | 9 Oct 13:53 UTC: all 221 `github-pages` deployment records (id, environment, created, commit), newest first. The owner kept the first 5 rows and deleted the other 216. |

Two earlier receipts stay on the owner box only: `cleanup-receipt-20261009.json` (W5, 4
releases and 96 tags) and `cleanup-receipt-20261009T091933Z.json` (W6, 22 releases and 22
tags); their counts are in `../SESSION-2026-10-08.md` and `../SESSION-2026-10-09.md`.
