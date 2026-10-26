<!-- Written by an assistant research agent on 25 Oct 2026 (W16k groundwork); kept verbatim in packet W16m.  Describes 25 Oct before W16k; since then Facebook Unlock app icons is taken (DECISIONS.json, facebook-hushfacebook include-patches). -->
# Agent/bot guidance audit — `govinda-rajulu/patch-factory`

**Window:** 2026-10-23T00:00Z through 2026-10-25 (latest public API records retrieved).  
**Population collected:** PR comments/reviews/inline comments and named check runs for PRs **#239, #241, #244, #246, #247**; all issue records returned by the requested `issues?state=all&since=...` sweep plus comments for the failure issues (#225, #229, #237, #248–#250), #233 (Needs you), #154 (Council desk), and the adjacent issue records in the window.  Review comments and inline reviews were empty for the five PRs.  The requested check-run API objects expose `output.title`, `output.summary`, and `output.text` as null for these jobs; their useful agent prose is posted as the corresponding PR issue comment.

## One-screen summary

**Keep visible:** concrete code/safety findings: login/signature/integrity bypasses; duplicate patch names across bundles; a paid unlock for an app *not* in the owner allow-list; missing provider licence/source records; and a named build/check failure. Those are actionable and either match `AGENTS.md` rules 1/3/4 or a reproducible build result.

**Hide/collapse:** the same paid-unlock warning repeated by five to seven seats after the owner had approved the name; generic “owner policy only lists …” blocks produced from an old base snapshot; seat/model/provider plumbing (MCP, 403/413/520, busy, missing, cut, quota-like unavailable); and the generated “finding(s) dropped: quote not found” bookkeeping. One compact infrastructure line per run is enough.

**Normalized unique-point counts (the rows below):** **REAL 13 · FALSE 7 · INFRA 12 · STALE 4 · DUPLICATE 6 = 42.** Repeated seat copies are counted under DUPLICATE, not again under the underlying point. “FALSE” means the warning conflicts with a documented owner decision; “STALE” means the decision/rule snapshot or guide used by the message was superseded.

## Classification ledger

Quotes are exact excerpts (at most 30 words).  “Patch/app” names the affected target, bundle, or workflow.

### REAL — keep, but consolidate repeated copies (13)

| # | Source | Author / seat / model | Exact quote | Patch/app | Why REAL |
|---|---|---|---|---|---|
| R1 | [PR #241 review comment](https://github.com/govinda-rajulu/patch-factory/pull/241#issuecomment-6394520990) | `github-actions[bot]`; nemotron | “login‑bypass patch (GMS sign‑in bypass) for Truecaller” | `truecaller-combo`, Truecaller | `AGENTS.md` rule 1 bans login/licence bypasses visible to a server. |
| R2 | [PR #241 review comment](https://github.com/govinda-rajulu/patch-factory/pull/241#issuecomment-6394520990) | `github-actions[bot]`; open | “Neutralize third-party SDKs” | Truecaller | Ad-network neutralization is a server-visible safety issue under rule 1; no owner exception is recorded. |
| R3 | [PR #241 review comment](https://github.com/govinda-rajulu/patch-factory/pull/241#issuecomment-6394520990) | `github-actions[bot]`; open | “Remove Ads” | Truecaller | The record describes a disallowed ad-network change; it is actionable if the patch is shipped. |
| R4 | [PR #241 review comment](https://github.com/govinda-rajulu/patch-factory/pull/241#issuecomment-6394520990) | `github-actions[bot]`; nemotron/open | “Disable telemetry” | `truecaller-combo` | Same patch name was reported in two bundles; rule 4 says one name cannot appear under two bundles of one target. |
| R5 | [PR #243 review comment](https://github.com/govinda-rajulu/patch-factory/pull/243#issuecomment-6394849173) | `github-actions[bot]`; nemotron | “View live anonymously” | Instagram | Account-activity suppression is an account/server-visible spoof under rule 1. |
| R6 | [PR #243 review comment](https://github.com/govinda-rajulu/patch-factory/pull/243#issuecomment-6394849173) | `github-actions[bot]`; nemotron | “Bypass channel restrictions” | Telegram | A server-enforced restriction bypass is rule-1 material; owner subsequently confirmed the fallback was built without it ([owner follow-up](https://github.com/govinda-rajulu/patch-factory/issues/235#issuecomment-6395421200)). |
| R7 | [PR #243 review comment](https://github.com/govinda-rajulu/patch-factory/pull/243#issuecomment-6394849173) | `github-actions[bot]`; nemotron | “Use SMS for verification codes” | Truecaller | The review reasonably treated altered verification flow as a login/licence-bypass risk. |
| R8 | [PR #247 review comment](https://github.com/govinda-rajulu/patch-factory/pull/247#issuecomment-6397454134) | `github-actions[bot]`; kilo | “Unlock app icons” | Facebook | Facebook is not in `paid_ok_targets`; a server-visible paid-feature unlock remains blocked. |
| R9 | [PR #247 review comment](https://github.com/govinda-rajulu/patch-factory/pull/247#issuecomment-6397454134) | `github-actions[bot]`; nemotron | “AMOLED dark theme” | Photos | The manifest showed the name in an added exclude and added include for the same target; rule 4 is a deterministic conflict even though the owner later recorded a drop. |
| R10 | [PR #247 review comment](https://github.com/govinda-rajulu/patch-factory/pull/247#issuecomment-6397454134) | `github-actions[bot]`; nemotron | “Hide Instants” | Instagram | Same name in two bundles violates rule 4; the owner’s later `take` does not permit two copies. |
| R11 | [PR #247 review comment](https://github.com/govinda-rajulu/patch-factory/pull/247#issuecomment-6397454134) | `github-actions[bot]`; kilo | “licence: none declared” | Photos/Akash provider | Rule 3 requires a new provider record with source, bundle, and licence. |
| R12 | [PR #246 bot comment](https://github.com/govinda-rajulu/patch-factory/pull/246#issuecomment-6395334619) | `github-actions[bot]`; Rule merge | “check failed: Patch instagram.” | Instagram build | A named patch-build failure is a real gate result; owner may override only after inspecting the run. |
| R13 | [Needs you update](https://github.com/govinda-rajulu/patch-factory/issues/233#issuecomment-6395350259) | `github-actions[bot]`; Selection/Needs you | “stay off by the BANNED rule” | ES File names | This correctly reflects `src/patches/BANNED`; it should be one grouped owner line, not repeated per provider. |

### FALSE — remove the block/ignore language, retain one policy note (7)

| # | Source | Author / seat / model | Exact quote | Patch/app | Why FALSE; owner decision/rule |
|---|---|---|---|---|---|
| F1 | [PR #239 review comment](https://github.com/govinda-rajulu/patch-factory/pull/239#issuecomment-6385801183) | `github-actions[bot]`; gemini | “premium unlocks for server-side apps (Telegram and Truecaller) … prohibited” | Telegram / Truecaller | W16g owner decision tested and approved `Unlock Premium` and `Enable Premium`; both were added to `paid_ok_targets`. |
| F2 | [PR #239 review comment](https://github.com/govinda-rajulu/patch-factory/pull/239#issuecomment-6385801183) | `github-actions[bot]`; nemotron | “Enable Premium” | Truecaller | Same owner approval; the warning is no longer a block. |
| F3 | [PR #239 review comment](https://github.com/govinda-rajulu/patch-factory/pull/239#issuecomment-6385801183) | `github-actions[bot]`; open/command | “Unlock Premium” | Telegram | Same owner approval; account risk may be a single low note, not a refusal. |
| F4 | [PR #241 review comment](https://github.com/govinda-rajulu/patch-factory/pull/241#issuecomment-6394520990) | `github-actions[bot]`; gemini | “Truecaller Premium” | Truecaller | The message contradicted the owner’s W16g approval of the premium patch. The separate GMS sign-in bypass finding remains REAL. |
| F5 | [PR #247 review comment](https://github.com/govinda-rajulu/patch-factory/pull/247#issuecomment-6397454134) | `github-actions[bot]`; gemini | “Unlock Unlimited” | Amazon Music | `amazonmusic` is in the owner’s current `paid_ok_targets` and `DECISIONS.json` records `Unlock Unlimited` as `take`. |
| F6 | [PR #247 review comment](https://github.com/govinda-rajulu/patch-factory/pull/247#issuecomment-6397454134) | `github-actions[bot]`; nemotron | “Unlimited track skipping” | Amazon Music | Same owner `take`; the “not on whitelist” reason is wrong. |
| F7 | [PR #247 review comment](https://github.com/govinda-rajulu/patch-factory/pull/247#issuecomment-6397454134) | `github-actions[bot]`; kilo | “Amazon Music is not in paid_unlock_ok_offline_apps” | Amazon Music | Same false premise, plus the cited PR #160 decision is stale. Keep the current policy source, not historical prose. |

### INFRA — report once per run, not as code guidance (12)

| # | Source | Author / seat / model | Exact quote | Patch/app | Why INFRA |
|---|---|---|---|---|---|
| I1 | [Issue #250](https://github.com/govinda-rajulu/patch-factory/issues/250) | `github-actions[bot]` | “Read-only GitHub MCP scout (failure)” | MCP scout | MCP/tool failure; it says nothing about a patch. |
| I2 | [Issue #249](https://github.com/govinda-rajulu/patch-factory/issues/249) | `github-actions[bot]` | “Enforce report result (coverage listed separately) (failure)” | Nightly watch | Report-enforcement failure, not a code recommendation. |
| I3 | [Issue #248](https://github.com/govinda-rajulu/patch-factory/issues/248) | `github-actions[bot]` | “Collect complete index comparison and website history (failure)” | Community watch | Data collection failure; do not turn it into a patch block. |
| I4 | [Issue #237](https://github.com/govinda-rajulu/patch-factory/issues/237#issuecomment-6384801487) | `github-actions[bot]` | “Step 6: Fetch bundle (failure)” | `aic0d3r/oxbow` / Instagram | Provider fetch failure; rerun or mark unreadable. |
| I5 | [Issue #237](https://github.com/govinda-rajulu/patch-factory/issues/237#issuecomment-6384801738) | `github-actions[bot]` | “Step 6: Fetch bundle (failure)” | `legendsciber/morphe-patches` / Keymapper | Same infrastructure class, separate failed job. |
| I6 | [Council desk #154](https://github.com/govinda-rajulu/patch-factory/issues/154#issuecomment-6034521546) | `github-actions[bot]`; council seats | “UNAVAILABLE provider returned 403” | Council model seats | Provider transport/auth failure, not repository evidence. The same comment also records 413 and 520. |
| I7 | [Council desk #154](https://github.com/govinda-rajulu/patch-factory/issues/154#issuecomment-6034521546) | `github-actions[bot]`; nemotron/open seats | “UNAVAILABLE no listed model answered” | Model seats | Missing/busy/cut models are seat plumbing; collapse to a per-run count. |
| I8 | [Council desk #154](https://github.com/govinda-rajulu/patch-factory/issues/154#issuecomment-6034521546) | `github-actions[bot]`; open seat | “INVALID_CANARY” | Council model seat | Transport/validation failure; it must not look like a code finding. |
| I9 | [Needs you update](https://github.com/govinda-rajulu/patch-factory/issues/233#issuecomment-6395350259) | `github-actions[bot]`; nightly/provider feeds | “Patch names only; supported-version, option and effective-default changes are NOT compared.” | Provider/nightly reports | Coverage limitation; report as one explicit data-quality limitation, not as a patch recommendation. |
| I10 | [Issue #229](https://github.com/govinda-rajulu/patch-factory/issues/229#issuecomment-6382635200) | `github-actions[bot]` | “Step 5: Edit Needs you only when its body changed (failure)” | Needs you renderer | Workflow/edit idempotency failure; not a patch finding. |
| I11 | [Issue #225](https://github.com/govinda-rajulu/patch-factory/issues/225) | `github-actions[bot]` | “7. Nightly watch: failure” | Nightly watch | Older failure in the requested window; keep as one retry/coverage event. |
| I12 | [Issue #227](https://github.com/govinda-rajulu/patch-factory/issues/227#issuecomment-6373733892) | `github-actions[bot]` | “Missing parts mean INCOMPLETE” | Community watch | Incomplete multi-part report; do not infer patch decisions from it. |

### STALE — policy/guide snapshot or historical citation is wrong now (4)

| # | Source | Author / seat / model | Exact quote | Patch/app | What changed |
|---|---|---|---|---|---|
| S1 | [PR #239 review comment](https://github.com/govinda-rajulu/patch-factory/pull/239#issuecomment-6385801183) | gemini/command | “Truecaller is not in the paid_unlock_ok_offline_apps list” | Truecaller | W16g (24 Oct) widened the owner list to include `truecaller-combo` and approved `Enable Premium`. |
| S2 | [PR #239 review comment](https://github.com/govinda-rajulu/patch-factory/pull/239#issuecomment-6385801183) | gemini/command | “owner_policy.paid_unlock_ok_offline_apps does not include telegram” | Telegram | W16g widened the list and approved `Unlock Premium`. |
| S3 | [PR #247 review comment](https://github.com/govinda-rajulu/patch-factory/pull/247#issuecomment-6397454134) | gemini/nemotron | “Amazon Music … is not included in the owner policy” | Amazon Music | The current policy and W16j owner decision include `amazonmusic`; the agent’s base snapshot or historical PR #160 citation was stale. |
| S4 | [PR #247 review comment](https://github.com/govinda-rajulu/patch-factory/pull/247#issuecomment-6397454134) | all onboarding seats | “Agent review required by AGENTS.md” | Onboarding review | The requirement itself is current, but the message is misleading when paired with a stale paid-policy snapshot. Render the policy commit/hash and effective owner decisions beside the citation. |

### DUPLICATE — collapse to one canonical finding (6)

| # | Source(s) | Repeated point | Fix |
|---|---|---|---|
| D1 | [PR #239](https://github.com/govinda-rajulu/patch-factory/pull/239#issuecomment-6385801183) | Telegram `Unlock Premium` and Truecaller `Enable Premium` were repeated by gemini, nemotron, open, and command. | Deduplicate by normalized `(target, patch-name, rule, policy-version)` before rendering. |
| D2 | [PR #241](https://github.com/govinda-rajulu/patch-factory/pull/241#issuecomment-6394520990) | `Disable telemetry` / `Disable Telemetry` was repeated by multiple seats. | Normalize case/punctuation for duplicate reporting, but retain one exact manifest quote. |
| D3 | [PR #247](https://github.com/govinda-rajulu/patch-factory/pull/247#issuecomment-6397454134) | Amazon paid-unlock block repeated by gemini, nemotron, codestral, kilo, and command. | Emit one policy result: `amazonmusic` approved; retain only unrelated Facebook paid-unlock finding. |
| D4 | [PR #239/#241/#247](https://github.com/govinda-rajulu/patch-factory/pull/247#issuecomment-6397454134) | “finding(s) dropped: quote not found …” bookkeeping. | Fold validator counters into a compact footer; do not present them as agent advice. |
| D5 | [Council desk #154](https://github.com/govinda-rajulu/patch-factory/issues/154#issuecomment-6034521546) | 403/413/520, busy, missing, and cut-seat variants. | One `INFRA: n seats unavailable; retry/backups used` line with structured counts. |
| D6 | [Needs you #233](https://github.com/govinda-rajulu/patch-factory/issues/233#issuecomment-6394819223) and [latest](https://github.com/govinda-rajulu/patch-factory/issues/233#issuecomment-6395350259) | Repeated `Selection run`, `Nightly run`, `Provider run`, and grouped take/drop/hold explanations. | Keep one current Needs you snapshot; suppress unchanged reruns. |

## Where the messages originate and concrete fixes

### 1. Paid-policy false blocks (F1–F7, S1–S3)

- **Source:** `src/etc/onboard_check.py:81-92`, `owner_policy(base)`, explicitly reads `src/patches/ADOPT.json` from the **BASE** checkout; `src/council/onboard_review.py:58-59` loads `docs/council/ONBOARD.md`; the prompt’s paid exception is in `docs/council/ONBOARD.md` under rule 1.
- **Why it went wrong:** PR #239/#241 seats saw a base snapshot before W16g’s owner decision; PR #247 seats still emitted the old “Amazon not allowed” premise despite current `ADOPT.json`/`DECISIONS.json`.
- **Fix:** have the manifest carry both `owner_policy.base` and an immutable `owner_decisions.effective_at_head` overlay from the PR head; require the prompt to say “policy at base” vs “owner decision at head.” For a paid name on `paid_ok_targets`, emit at most one low account-risk note, never `block`. Add regression fixtures for `keymapper: Premium`, `truecaller-combo: Enable Premium`, `telegram: Unlock Premium`, and `amazonmusic: Unlock Unlimited`.

### 2. Real onboarding findings (R1–R12)

- **Source:** `docs/council/ONBOARD.md` rules 1–4 and `src/council/onboard_review.py:62-71` (`not_shipped`) plus `:74-114` (`check_answer`).
- **Fix:** preserve the deterministic manifest evidence and render only one finding per normalized `(target, name, rule)`. Keep the actual manifest quote; do not let a model invent a quote. For R12, link the failed patch job and report its concrete test output rather than “check failed” alone.

### 3. Needs you / hold/drop/skip noise (R13, D6)

- **Source:** `src/etc/needs_you.py:55-69` decision/group grammar, `:184-205` held-row parsing, `:285-289` owner-facing descriptions, `:575-593` decision-memory behavior; `src/etc/selection_watch.py:102-136` (`classify`) and `:431-445` (`remember`).
- **Fix:** show only new or changed owner decisions. Keep BANNED/CONFIRM/universal/paid-outside-allow-list as grouped rule outcomes; suppress unchanged “Take = …; drop = …; hold = …” boilerplate. Render `skip` as “owner already dropped” and include the decision ID once.

### 4. Infrastructure/model failures (I1–I9, D5)

- **Source:** `src/council/council.py:122-135` exception classes; `:370-429` model discovery/pacing/retry; `:667-731` seat fallback/status rendering. MCP output is generated by `.github/workflows/mcp-scout.yml:43-98` and normalized by `src/etc/mcp_scout_check.py:27-63`. Nightly failure handling is `src/etc/nightly_report.py:27-63,115-121`; community report/supersede logic is `src/etc/community_watch.py:286-298`.
- **Fix:** never let an INFRA status enter the model-finding table. Add a single structured footer (`MCP failed`, `nightly failed`, `community failed`, `seats unavailable: missing/busy/cut/refused`) with run URL and retry status. Do not repeat per-seat provider codes; retain details in the run artifact.

### 5. Guide citations and “nothing changed”/superseded reports (S4, D4/D6)

- **Source:** `src/council/onboard_review.py:173-204` (`render`, including dropped-finding lines); `src/etc/community_watch.py:286-298` (`supersede`); `src/etc/selection_watch.py:486-553` (no-change/apply reporting).
- **Fix:** cite the exact rule file and policy commit/hash, not only `AGENTS.md`; stop posting a new comment when the normalized body is unchanged; fold validator “dropped” counters under a details footer.

## Check-run inventory (requested names)

The check-run API objects were retrieved by each PR head SHA. For the named checks below, output fields were null (no title/summary/text), so there is no missing hidden prose to classify; the issue comments are the public agent reports.

- **PR #247 head `ee9b761…`:** [Agent review](https://github.com/govinda-rajulu/patch-factory/actions/runs/40191087312/job/121162090012) failure; [Onboarding record](https://github.com/govinda-rajulu/patch-factory/actions/runs/40191087312/job/121162057084) success; [Validate targets/scripts](https://github.com/govinda-rajulu/patch-factory/actions/runs/40191087301/job/121162056955) success.
- **PR #244 head `7ddeea9…`:** [Agent review](https://github.com/govinda-rajulu/patch-factory/actions/runs/40174013520/job/121110746691) failure; [Onboarding record](https://github.com/govinda-rajulu/patch-factory/actions/runs/40174013520/job/121110710555) success; [Validate targets/scripts](https://github.com/govinda-rajulu/patch-factory/actions/runs/40174013538/job/121110709977) success.
- **PR #241 head `eaafe5e…`:** [Agent review](https://github.com/govinda-rajulu/patch-factory/actions/runs/40169777924/job/121098118668) failure; [Onboarding record](https://github.com/govinda-rajulu/patch-factory/actions/runs/40169777924/job/121098090741) success; [Validate targets/scripts](https://github.com/govinda-rajulu/patch-factory/actions/runs/40169777924/job/121098090297) success.
- **PR #239 head `f398ff9…`:** [Agent review](https://github.com/govinda-rajulu/patch-factory/actions/runs/40107774631/job/120912963528) failure; [Onboarding record](https://github.com/govinda-rajulu/patch-factory/actions/runs/40107774631/job/120912929162) success; [Validate targets/scripts](https://github.com/govinda-rajulu/patch-factory/actions/runs/40107774606/job/120912928457) success.
- **PR #246 head `7895f6e…`:** no check run with the exact names “Agent review (required for onboarding)” or “Onboarding record”; [Validate targets/scripts](https://github.com/govinda-rajulu/patch-factory/actions/runs/40176186808/job/121117265294) success. Its public Rule merge comment is [here](https://github.com/govinda-rajulu/patch-factory/pull/246#issuecomment-6395334619).

## Collection/processing coverage

- **Collection:** complete for the assigned source classes and requested window: all five selected PR comment/review/inline-comment endpoints, named check-run endpoints, the all-state issue sweep, #233, #154, and the failure issues (#225, #229, #237, #248–#250), plus community/tooling/nightly/provider issue comments retrieved. Empty inline-review arrays and null named-check outputs are recorded above. Stable URLs/IDs are preserved in every ledger row.
- **Processing:** complete for all collected messages that matched the requested action/failure rubric. Non-matching prose (ordinary community tables, approvals, and owner-only “done” comments) was excluded by rule; it was not silently treated as agent guidance.
