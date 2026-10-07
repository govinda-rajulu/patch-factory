# Council audit ledger, main d2060b82 (6-7 Oct 2026)

The first whole-repository council audit (issue #152, T1 council) had 84 findings in 8 shard
comments as read then. An agent checked every one against the cited file at `d2060b82`; the
assistant then sorted them. Leads, not decisions. The other three shards did post (see LESSONS 23)
but were not in this ledger. The V1 re-audit lives on desk #154.

Totals: 33 confirmed, 6 unclear, 45 refuted. Shipped from it in V1: usque digest pin, `#` lines
skipped in selection files. Open confirmed items are listed in OPEN-WORK.md.

| verdict | sev | shard | where | issue | evidence |
|---|---|---|---|---|---|
| confirmed | medium | build-shell | `src/build/build.sh:23` | Sourcing utils.sh disables nounset | `set +u; source ./src/build/utils.sh; set -u` |
| confirmed | low | build-shell | `src/build/build.sh:145` | Resolve output parsed with sed/tail | `WINNER=$(sed -n ... <<<"$RES" / tail -1)` and equivalent VERSION/MPP parsing. |
| confirmed | low | build-shell | `src/build/selections.sh:23` | Bundle ordering relies on ls and sort | `ls ./*.mpp ... / awk ... / sort / cut -f2-` |
| confirmed | medium | build-shell | `src/build/utils.sh:154` | Comment-only include/exclude files count as valid selections | get_patches_key skips only `[[ -z "$line1" ]]`; `#` lines are not comments there. |
| confirmed | nit | build-shell | `src/build/utils.sh:158` | Build mutates selection files with sed -i | `sed -i 's/\r$//' "$patchDir/include-patches"` |
| confirmed | low | council | `docs/council/SETUP.md:57` | NVIDIA_API_KEY is shared by gpt/nemotron/kimi seats | Table lists `NVIDIA_API_KEY` and seats `gpt, nemotron, kimi`. |
| confirmed | low | council | `src/council/council.py:1053` | scrub leaves short configured key values partially visible | `if len(v) >= 8: text = text.replace(v, '[key]')` |
| confirmed | medium | docs | `AGENTS.md:112` | CONFIRM patches only warn and are not hard-gated | AGENTS says `CONFIRM means a human decides`; preflight runs bancheck/quarantine, not a CO… |
| confirmed | medium | docs | `README.md:145` | Batch workflows do not fail-fast | README states `Batch jobs do not fail-fast, so a red workflow can contain published succe… |
| confirmed | low | etc | `src/etc/apply_choices.py:8` | Broad exception catch hides details | Catches `ValueError, KeyError, OSError, IndexError` and prints only `ABORT: ` plus text. |
| confirmed | nit | etc | `src/etc/chooser.py:114` | exists() follows symlinks for selection files | Chooser uses `os.path.exists(...)` before opening selection files. |
| confirmed | low | etc | `src/etc/classify.py:83` | Risk keywords are hardcoded | `RISK={'spoof':..., 'potoken':..., ...}` is a literal keyword map. |
| confirmed | low | etc | `src/etc/nightly_report.py:68` | Run-id regex accepts leading zeros/weak identity | `re.fullmatch(r'[0-9]+',run_id or '')` accepts `0001`; no nonzero identity constraint. |
| confirmed | low | etc | `src/etc/obtainium.py:25` | Package overrides are hardcoded outside targets.json | `pkg["yt-music"] = ...`; `pkg["youtube-morphe"] = ...` are literal overrides. |
| confirmed | low | etc | `src/etc/orphans.sh:15` | ls glob runs once on literal when no patch dirs | `for d in $(ls -d src/patches/*/ 2>/dev/null ...)` with set -u; empty glob can remain lit… |
| confirmed | medium | etc | `src/etc/provider_watch.py:163` | Provider watch hardcodes -x -u and omits universal patches | Observer default is `flags=("-x", "-u")`; comment says these omit universal patches. |
| confirmed | low | etc | `src/etc/release_retention.py:134` | CI provenance depends on spoofable body marker | `CI_MARKER` is a body string; comments say candidates need human review and body markers … |
| confirmed | nit | portal | `docs/index.html:112` | Truecaller catalog note is cut off | Note ends mid-sentence: `bufferk publishes rarely (newest 1`. |
| confirmed | low | portal | `docs/index.html:253` | Catalog contains stale age-cap notes | CATALOG notes contain `Age cap is advisory since 7 Sep 2026: resolve`. |
| confirmed | medium | portal | `docs/index.html:265` | portal.js script lacks SRI | Script is loaded without an integrity attribute; no `integrity="sha384-..."` is present. |
| confirmed | medium | portal | `docs/portal.js:342` | API response cache TTL can delay critical updates | `async function read(url,ttl=30000)` caches while `Date.now()-existing.at<ttl`. |
| confirmed | low | portal | `docs/portal.js:587` | Release notes truncate at 24k chars/400 lines | Release-note rendering applies a 24k-character/400-line bound. |
| confirmed | nit | rest | `.keepalive:1` | Keepalive timestamp is outdated | Pinned content is `2026-10-01T11:11:03Z`; audit comments are dated 2026-10-07. |
| confirmed | medium | selection | `src/patches/QUARANTINE:3` | Remove Debug Info remains quarantined for ES File and MX Player; upstream issue unresolved | esfile-ftl/Remove Debug Info/2026-09-06/upstream: ... IllegalAccessException |
| confirmed | low | workflows | `.githooks/pre-commit:6` | pre-commit can be bypassed with --no-verify | Comment says `Skip with: git commit --no-verify`. |
| confirmed | medium | workflows | `.github/actions/preparing/action.yml:34` | usque proxy failure does not stop action | `... && echo "[+] ... ready" // echo "[-] usque proxy failed"` |
| confirmed | medium | workflows | `.github/workflows/ci.yml:132` | Poll-only schedules resolve only build targets | Matrix uses `(schedule && schedule != ... ) && needs.plan.outputs.matrix // ...resolution… |
| confirmed | high | workflows | `.github/workflows/ci.yml:144` | Resolve job continues on error | `continue-on-error: true` under the resolve job. |
| confirmed | medium | workflows | `.github/workflows/manual-patch.yml:103` | Manual workflow defaults shadow plan requirement false | `shadow_plan_required` input has `default: false`. |
| confirmed | low | workflows | `.github/workflows/watch.yml:52` | Watch job has no timeout | No `timeout-minutes` appears on the watch job. |
| confirmed | low | workflows | `.github/workflows/watch.yml:58` | Watch workflow has no retry mechanism | Steps are single invocations; no retry wrapper or retry strategy is present. |
| confirmed | low | workflows | `.github/workflows/watch.yml:70` | Downloaded artifacts lack an integrity-verification step | Workflow uploads report files but has no explicit digest/content verification step. |
| confirmed | low | workflows | `.github/workflows/watch.yml:76` | Downloaded artifacts lack content validation | Workflow has no explicit report schema/content validation before upload. |
| unclear | low | docs | `knowledge/handbook/SOLO-REPO-ENGINEERING.md:126` | handbook does not clean up uploaded file | This is a handbook requirement about delivered scripts, not an implementation of a named … |
| unclear | low | docs | `knowledge/handbook/SOLO-REPO-ENGINEERING.md:127` | handbook does not delete clone | This is a handbook requirement about delivered scripts, not an implementation of a named … |
| unclear | low | docs | `knowledge/handbook/SOLO-REPO-ENGINEERING.md:128` | handbook does not append run ledger | This is a handbook requirement about delivered scripts, not an implementation of a named … |
| unclear | low | docs | `knowledge/handbook/SOLO-REPO-ENGINEERING.md:129` | handbook does not move small logs | This is a handbook requirement about delivered scripts, not an implementation of a named … |
| unclear | low | workflows | `.github/workflows/watch.yml:45` | Fixed cron may not match owner timezone | Workflow has fixed `cron: "41 1 * * *"`; owner timezone is not established here. |
| unclear | nit | workflows | `.github/workflows/watch.yml:64` | Watch workflow has no cleanup step | No explicit cleanup step; Actions retention/runner cleanup is implicit. |
| refuted | nit | build-shell | `src/build/build.sh:359` | Downloaded APK package name is not checked against target | PKG_SEEN is compared: `elif [ "$PKG_SEEN" != "$PKG" ]; then ... exit 1`. |
| refuted | nit | build-shell | `src/build/resolve.sh:63` | Unknown configured provider PIN silently falls back | Pinned candidates are skipped; with no winner the script prints `RESULT: no viable provid… |
| refuted | nit | council | `src/council/shards.json` | rest shard has no description | rest shard has `"about": "Every other file not excluded above"`. |
| refuted | nit | docs | `AGENTS.md:105` | Nearest -p binding rule is unclear | AGENTS explicitly says `-e` and `-d` bind to the nearest preceding `-p`; `-d` wins. |
| refuted | nit | docs | `README.md:240` | Build-gates section is not clearly separated | README has heading `### Build gates and separate validation checks`. |
| refuted | nit | docs | `SECURITY.md:30` | Inputs/checks table lacks a clear heading | Security has `## Inputs and checks` immediately before the table. |
| refuted | nit | docs | `docs/AGENT-SETUP.md:10` | First agent task is not clearly explained | Setup gives the first task, exact prompt, rationale, and review boundary. |
| refuted | nit | docs | `docs/AGENT.md:20` | Architecture section lacks separation | Guide has `## The only architecture that is safe here`. |
| refuted | nit | docs | `docs/companions.md:50` | Companion table lacks a clear heading | `## Already available here` precedes the Companion/Current support/Boundary table. |
| refuted | nit | docs | `knowledge/LESSONS.md:10` | Standing rules section lacks separation | File contains `## Standing rules (short form; AGENTS.md is authoritative)`. |
| refuted | nit | docs | `knowledge/README.md:10` | Knowledge document does not explain file purposes | It gives ordered files with descriptions under `## Read in this order`. |
| refuted | nit | docs | `knowledge/handbook/SOLO-REPO-ENGINEERING.md:130` | handbook does not say it keeps everything for STOPPED | Cloud Shell hygiene explicitly states STOPPED keeps diagnosis, never touches unrelated pa… |
| refuted | nit | docs | `knowledge/handbook/SOLO-REPO-ENGINEERING.md:131` | handbook does not say it avoids unrelated work paths | Cloud Shell hygiene explicitly states STOPPED keeps diagnosis, never touches unrelated pa… |
| refuted | nit | docs | `knowledge/handbook/SOLO-REPO-ENGINEERING.md:132` | handbook does not say deletion requires matching sha prefix | Cloud Shell hygiene explicitly states STOPPED keeps diagnosis, never touches unrelated pa… |
| refuted | nit | docs | `knowledge/handbook/SOLO-REPO-ENGINEERING.md:133` | handbook does not say unknown files are never deleted | Cloud Shell hygiene explicitly states STOPPED keeps diagnosis, never touches unrelated pa… |
| refuted | low | etc | `src/etc/nightly_report.py:102` | 8 MiB report truncation has no warning | On limit it writes `Report exceeded 8 MiB capture limit; content not published.` and rc=2. |
| refuted | low | etc | `src/etc/nightly_report.py:126` | 15-minute timeout has no warning | Timeout path writes `Report exceeded 15-minute limit; completeness unknown.` |
| refuted | low | etc | `src/etc/nightly_report.py:136` | Missing/invalid input report is not handled | analyze() records `target coverage inventory unavailable` or `empty report` and forces UN… |
| refuted | low | etc | `src/etc/nightly_report.py:146` | Missing/invalid input report is not handled | analyze() records `target coverage inventory unavailable` or `empty report` and forces UN… |
| refuted | low | etc | `src/etc/nightly_report.py:156` | Missing/invalid report is not handled | analyze() adds `empty report`/`missing or duplicate final report result` reasons and retu… |
| refuted | low | etc | `src/etc/nightly_report.py:166` | Missing/invalid input report is not handled | analyze() records `target coverage inventory unavailable` or `empty report` and forces UN… |
| refuted | low | etc | `src/etc/nightly_report.py:176` | Missing/invalid input report is not handled | analyze() records `target coverage inventory unavailable` or `empty report` and forces UN… |
| refuted | low | etc | `src/etc/nointerp.sh:18` | Interpolation regex misses input variants | Regex allows whitespace after `${{` and scans every run block; valid expressions use the … |
| refuted | low | etc | `src/etc/poll.sh:64` | Provider fetch failures lack error handling | Empty/null date is checked; script emits provider-date error and exits with poll_state=un… |
| refuted | low | etc | `src/etc/poll.sh:85` | Empty git log silently skips config rebuild | After empty CFGD it emits `::warning::... no commit touches ...`; shallow clones also war… |
| refuted | low | etc | `src/etc/preflight.py:78` | Collision check ignores provider/options context | The gate intentionally rejects duplicate requested patch names across bundles, regardless… |
| refuted | low | etc | `src/etc/provider_watch.py:185` | Baseline path permits traversal | inventory validates provider/package with SAFE and constructs baseline as name + package … |
| refuted | low | etc | `src/etc/readmegen.py:78` | README lists nonexistent gates | Generated gate list names bancheck, quarantine, selections, build, check_sdk, tooling, re… |
| refuted | nit | etc | `src/etc/report.sh:1` | Missing pipefail | First line sets `set -uo pipefail`, which already enables pipefail. |
| refuted | low | etc | `src/etc/report.sh:33` | Authorization token array can split on spaces | RAUTH is an array and curl receives quoted `"${RAUTH[@]}"` as one header argument. |
| refuted | low | etc | `src/etc/review_sheet.py:25` | Missing JAR is not handled | Same explicit `/tmp` jar absence abort is before JAR use. |
| refuted | low | etc | `src/etc/review_sheet.py:40` | Missing JAR check | `if not jars: print("ABORT: no patcher jar in /tmp"); sys.exit(1)`. |
| refuted | low | etc | `src/etc/selection_names.py:100` | Unreadable provider list is not handled | Provider exceptions are caught and printed as `UNVERIFIED`; unverified is not counted as … |
| refuted | low | etc | `src/etc/selection_names.py:100` | Provider list unreadability is not handled | Exception path emits `provider list unreadable - UNVERIFIED`. |
| refuted | low | etc | `src/etc/selection_writer.py:100` | Missing decisions file is not handled | Missing chooser files / decision sheets raise and wrapper prints `ABORT`; absent files ar… |
| refuted | low | etc | `src/etc/watch_issue.sh:100` | Missing watch report is not handled | `[ -s "$R" ] // { echo "::error::watch report missing or empty"; exit 1; }`. |
| refuted | nit | portal | `docs/index.html:113` | Reddit catalog note is cut off | Reddit note ends with a complete sentence: `none of which this build needs`. |
| refuted | low | portal | `docs/portal.js:187` | read error handling may swallow critical network failures | `need(r.ok,...)` throws; callers display `Upstream unavailable`/error state rather than t… |
| refuted | nit | selection | `src/patches/README.md:36` | YouTube exception is not enumerated and could be overlooked | `youtube` is the exception ... gating it means enumerating all 61 patch names. Known gap,… |
| refuted | nit | selection | `src/patches/README.md:36` | Age-cap advisory note could mislead | A bundle that still applies is still good ... age is a warning, not a disqualification. |
| refuted | nit | selection | `src/patches/README.md:36` | Docs omit real suites before push | Run preflight, the Python suites, portal contracts, generator checks and shell checks bef… |
| refuted | nit | workflows | `.github/workflows/add-target.yml:53` | jq validity check before mv is redundant | `jq -e . /tmp/t.json` validates generated JSON before `mv`; this is a useful pre-write gu… |
| refuted | nit | workflows | `.github/workflows/notify-failure.yml` | Failure notifier lacks duplicate issue detection | Searches all issues and rejects duplicate exact report identity before create. |
| refuted | nit | workflows | `.github/workflows/watch.yml:48` | Concurrency group is hardcoded | `group: nightly-watch` intentionally queues rewrites of standing issue #27. |
| refuted | nit | workflows | `.github/workflows/watch.yml:82` | Issue opens even when nothing changed | `watch_issue.sh` computes fingerprint and prints `unchanged, staying quiet` when equal. |
