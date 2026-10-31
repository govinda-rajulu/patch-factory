# Removed selection utilities (30 October 2026)

These utilities were removed in W16y-a after the owner checked the caller search on 30
October 2026. They are retained in git history and can be restored with the commands below.

| Path | Last commit | What it did | What replaced it | Why removed |
| --- | --- | --- | --- | --- |
| `src/etc/apply_choices.py` | `4395454` | Compatibility wrapper that called `selection_writer.main('chooser')` and converted the writer's expected errors into an `ABORT` message. It was the command-line entry point for applying the temporary chooser files. | Needs you #233 records owner choices; those choices flow into `src/patches/DECISIONS.json`, and Selection watch applies the resulting decisions. | Owner decision, 30 October: no caller remains. The chooser path could write include lists without `DECISIONS.json`, so the bots would ask the same questions again. |
| `src/etc/chooser.py` | `06ed5c1` | Read `/tmp/pf/iss.json`, collected provider patch rows, and wrote editable `/tmp/pf/choose/*.txt` files with `+`, `-` and blank current-state markers. It annotated banned, exception and confirmation names for a human edit. | Needs you #233 -> `src/patches/DECISIONS.json` -> Selection watch; provider changes are reviewed through the current watch flow instead of temporary chooser files. | Owner decision, 30 October: no caller remains. Its output was not connected to `DECISIONS.json`, so applying it could make the bots re-ask the same choices. |
| `src/etc/community_diff.py` | `fa10ed4` | Compared the previous `src/community/bundles.json` snapshot with a new JSON index. It flattened compatible package names and reported new, changed and disappeared bundle/app pairs, highlighting configured apps. | Community watch owns the index diff and its saved report; Selection watch handles selected patch decisions. | Owner decision, 30 October: no caller remains; the Community watch is the maintained index-diff path. |

To restore any file, use its recorded last commit:

```sh
git show 4395454:src/etc/apply_choices.py > src/etc/apply_choices.py
git show 06ed5c1:src/etc/chooser.py > src/etc/chooser.py
git show fa10ed4:src/etc/community_diff.py > src/etc/community_diff.py
```

The dead `chooser` branch in `src/etc/selection_writer.py` was removed with these files.
The `full` and `unreviewed` selection-sheet modes remain.

# Removed unused files (31 October 2026, packet W16z)

Owner plan of 31 October (W16z housekeeping). Callers were searched on main `572d7d2b` before the removal.

| Path | Last commit | Blob | Why removed |
| --- | --- | --- | --- |
| `src/options/arandomhooman.json` | `18211bc29a811bb275746da993c57b4fadd5187e` | `0637a088a01e8ddab3bf3fa98dbe804cbde1a0dc` | Two bytes (`[]`); no target or candidate names `arandomhooman` as its `options`. |
| `src/options/bufferk.json` | `18211bc29a811bb275746da993c57b4fadd5187e` | `0637a088a01e8ddab3bf3fa98dbe804cbde1a0dc` | Two bytes (`[]`); the Truecaller `bufferk` fallback uses `options: combo`, which stays. |
| `docs/review/providers/hushtelegram-org.telegram.messenger.names` | `36ef8c7cc8ac2678e885746b4e1251896a01003b` | `632ee4c474dd24f85b02bc3a53987f584673f271` | Not one of the 35 provider-watch baselines (`provider_watch.inventory(targets, watch_sources=True)`); byte-identical to the live `extra-sysadmindoc-hushtelegram-org.telegram.messenger.names`, which stays. |

To restore:

```sh
git show 18211bc29a811bb275746da993c57b4fadd5187e:src/options/arandomhooman.json > src/options/arandomhooman.json
git show 18211bc29a811bb275746da993c57b4fadd5187e:src/options/bufferk.json > src/options/bufferk.json
git show 36ef8c7cc8ac2678e885746b4e1251896a01003b:docs/review/providers/hushtelegram-org.telegram.messenger.names > docs/review/providers/hushtelegram-org.telegram.messenger.names
```

The HushTelegram selection directory and `src/options/hushtelegram.json` stay on purpose (owner, 30 October: kept unreferenced).
