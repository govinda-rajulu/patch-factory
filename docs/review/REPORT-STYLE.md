# How bots write issues and comments

Owner ask, 22 Oct 2026 (packet W15e): "easy for you or me or anyone to read and understand".
Helper: `src/etc/readable.py`. Every bot issue body and comment in this repository follows it.

1. **Title with one status word**: `# Selection watch: OK`, `NEEDS YOU`, `CHANGED`, `FAILED`.
2. **"Needs you:" line** right under it: `nothing`, or how many items, listed first.
3. **Summary table**: one row per section, with counts, not lists.
4. **Sections by urgency**: needs-you first, then changes, then reference. Each section is a
   table; long lists fold into `<details>`. Nothing is cut: folded is still there (L061).
5. **One standing issue per watch**, edited in place. A rerun adds a short comment with only
   what changed since the last run (`readable.changed_lines`). Old per-run issues close as
   "superseded by #N".
6. **Agents**: findings that name no rule, file fact or check are dropped and counted
   (council.py `VAGUE`). High and medium findings, and any seen by two seats, show in the table;
   low and nit fold. Blocking seats stay visible; approving seats' reasons fold.

| Surface | Writer | Since W15e |
|---|---|---|
| #182 Selection watch | `src/etc/selection_watch.py` | tables, grouped held reasons, change-only comment |
| provider watch (standing) | `src/etc/provider_watch.py` | changed rows first, unchanged folded, old per-run issues closed |
| community report | `src/etc/community_model.py`, `community_watch.py` | grouped tables, OTHER_APPS folded, older reports closed |
| #27 Nightly watch | `src/etc/nightly_body.py`, `watch_issue.sh` | check table, per-folder table, change-only comment |
| #154 Council desk, PR reviews | `src/council/council.py` | severity counts, vague dropped, minor folded |
| Onboarding review | `src/council/onboard_review.py` | blocks visible, approvals folded |
