# patch-factory: chat handover after W15i, and the W16 brief (23 Oct 2026, 21:50 IST, checked twice)

Read this after knowledge/STATE.md and docs/review/HANDOVER-2026-10-23.md (shipped in W15i).
Where they differ, this file is newer. The W16 packet commits this file as docs/review/W16-BRIEF.md.

## 1. State when this chat closed

- main = 822c5f3c at 16:15Z (bot "community: acknowledge reported index", parent 4d9bbfbd =
  #220 W15i merge 06:44Z). Read live main first; bots keep committing.
- W15i controller: RESULT OK up to cleanup. Validate passed on packet head 5625a305; merge tree
  5dc3f89f = packet tree + bot files of 9863901; Pages deployment 7272038275 success.
- Cleanup receipt 20261023T064039Z deleted: releases instagram 452.0.0.48.64 (db32d516),
  instagram 452.1.0.53.64 b...39900263275 (3572ca71), reddit 2026.42.0 (388086fa); their 3 tags;
  4 Pages records; branch packet/w15i (restore: push 5625a3058b4b6abfbe3fadebce0f620913b01610).
  16 releases kept.
- T1 after W15i: Batch Patch 39913450300 (publish=false, 17 apps) success. Check new patch
  39914680513 built ONE app (facebook) and published facebook-v584.0.0.51.56 (HushFacebook 0.17.0,
  07:07Z, with pf-publication and pf-qualified records). The owner's Cloud Shell timed out after
  cleanup, so the T1 RESULT file on Cloud Shell was never read; the API facts above stand in.
- Shelf (17 tags at 07:44Z; unchanged at 16:15Z): no reddit release at all. facebook 583 still beside 584 (next cleanup
  removes it). instagram 452.1 b...39903699347 is a HushGram fallback (piko "Disable story auto
  flipping" broken on 452.1). adguard 4.14.68 tag dates from 14 Oct; es-file from 20 Oct.
- Keys: Kilo saved; Z.AI saved 23 Oct (glm-4.5-flash HTTP 200; glm-4.7-flash 429 code 1305 =
  overloaded, not a bad key). The HANDOVER line "Kilo and Z.AI keys added" is now true.
- Open bot issues: #154 council desk; #182 Selection watch NEEDS YOU (instagram/piko
  "Hide hidden requests": add or skip); #213 provider watch OK 24/24; #218 tooling watch
  (pup unmaintained since 2016, htmlq candidate; usque 4.2.0 behind 4.2.1; fiorenmas fork has new
  commits with store-download fixes to port); #221 community watch (275 -> 276 providers, 22 events).

## 2. Wrong calls this chat: 50 (48 at W15i handover, then 2)

- 49: said the automatic check would publish Reddit 41 after 42 was deleted. It builds only apps
  whose upstream changed; Reddit 41 was not new, so Reddit has no release.
- 50: never checked the official Morphe bundle for Reddit. MorpheApp/morphe-patches v1.48.0 (stable,
  22 Oct) has Reddit: about 31 patches (README on main), versions 2026.42.0 / 41.0 / 40.0
  experimental, 24.0 and 10.0 stable. v1.48.0 notes: "Reddit: Add experimental support for
  2026.42.0" plus 8 new Reddit patches (Copy text, Customize post layout, Download location, ...). We kept Adobo alone (stops at 41)
  and deleted the 42 build for it. targets.json note "adobo covers reddit alone" is false; tooling
  watch labels morphe-patches "YouTube, YouTube Music" (missing Reddit).

Lesson candidates for W16 (number them after the newest in docs/council/LESSONS.md, L077):
- Check the official bundle (MorpheApp) before choosing or keeping a community provider.
- Never delete a shelf build until its replacement is published and verified.
- Check new patch only builds changed apps; a retirement or provider switch needs an explicit
  Batch Patch dispatch for that app.

## 3. Owner's ask (23 Oct 21:37), in his words condensed

Morphe alone covers YouTube, YouTube Music, Reddit: why is it not used for Reddit? Community watch
shows no use. Repo and Pages are full of filler, jargon and wrong details; "What's new" is not
informative; unclear how build, watch and apps differ from before. Patcher and app sourcing must get
faster. Fix as much as possible in the next batch; dev branch or main, either is fine; start from
scratch if needed. Self-sufficient soon. Relax AI token budgets within official docs; let agents
review the repo and file issues for owner triage. Strong groundwork first, then top-level things.
Laser-targeted fixes.

## 4. Diagnosis (evidence read 23 Oct)

- Engine works: 17/17 apps built today; signing, store chain, Obtainium pin are fine. Do not
  rewrite it. The rot is the layer on top.
- Too many observers, no deciders: 18 workflows; four watch issues (tooling, provider, selection,
  community) plus council desk. Community watch only diffs the 276-provider index and prints counts
  ("configured-app events: 5"); it never ranks providers or recommends a switch.
- Time: Check new patch 39914680513 took ~11 min to build 1 app; ~6 min was 17 shadow jobs
  re-downloading every app's APK ("Resolve exact patcher-input APK (shadow only)"). Only facebook's
  prepared APK was used by its build. Batch of 17 takes ~11 min.
- Words: release notes say "Applied patch names unchanged; this does not prove unchanged patch code
  or defaults", "Repository source changed; see the exact source comparison". Issues carry
  disclaimer blocks ("What this watch does not check", "Transport hashes are not independent
  publisher authenticity"). True-ish, useless to the owner.
- Wrong facts found: Reddit note, tooling-watch role for morphe-patches. Expect more: audit all
  targets.json notes, Pages text, README, issue templates.

## 5. W16 plan (dev branch dev/w16, packets merged into it, dev -> main when T1 is green)

1. Audit: every workflow: trigger, last-30-day runtime (API), what it writes, who reads it. Cut or
   merge anything with no reader. Write docs/review/AUDIT-W16.md in plain words.
2. Reddit: Morphe official primary (2026.42.0 is experimental: if it fails, step down to 41.0),
   Adobo fallback. Onboarding record
   per docs/council/ONBOARD.md; check names against bundles.json/list-patches, not web search.
   Fix every wrong note and label. Publish with an explicit Batch Patch reddit run.
3. One build lane: shadow resolver becomes the real lane or is removed; skip unchanged apps in
   seconds; cache patcher JAR and source APKs by version. Target: Check new patch under 5 min.
4. Words: release notes = app version old -> new, bundle old -> new, patches added/removed by name,
   provider changelog lines, install note. Nothing else. Pages: one plain card per app (version,
   patches, provider, last built, install link). Disclaimers live once on an About page.
5. Watches: tooling + provider + selection + community -> one daily "Needs you" issue, empty days
   say "nothing". Community watch becomes a provider ranker per app (official first, patch count,
   supported versions, freshness) and opens an issue only when a better provider exists.
6. AI: council budgets raised within each provider's documented free limits (Kilo, Z.AI, Groq,
   OpenRouter, NVIDIA, Mistral, Cohere, Gemini; check each official docs page, not OmniRoute).
   Weekly repo review files each finding as its own issue (label review) for owner triage.
7. Then: record rejected AI vendors (section 6); W15g signing split (docs/review/SIGNING-SPLIT.md,
   needs a phone test).

Still open from earlier (OPEN-WORK 23 Oct): docs/review/onboarding/facebook.md still names 583;
Instagram piko breakage on 452.1; five apps with one store only (ytmusic, adguard, photos,
truecaller-combo on APKMirror; keymapper on APKPure); Google Play helper (ggplay_dl) never called;
combo planner; zizmor; persona PRs; openskip mirror of knowledge/handbook/PACKET-LESSONS.md needs
openskip's own PR; Cloudflare Workers AI key optional; port fiorenmas store fixes; pup -> htmlq.

Upstream changes to respect in W16: morphe-patches v1.48.0 moved to "Patcher 2.0" (check every
community bundle still loads with the patcher we take); morphe-desktop v1.19.0 (22 Oct) is the
newest patcher and HushFacebook 0.17.0 needs >= 1.19.0; morphe-patches v1.49.0-dev.1 is out
(23 Oct, YouTube only). Verify against the live release pages, not this note.

## 6. AI vendors checked 23 Oct (record in docs/council/PROVIDERS.md)

Added: Kilo Gateway (https://ai-gateway.kilo.ai/api/v1, KILO_API_KEY, kilo-auto/free answered,
16 free models of 401); Z.AI (https://api.z.ai/api/paas/v4, ZAI_API_KEY, GLM-4.7-Flash and
GLM-4.5-Flash free per docs.z.ai pricing).
Rejected: Qwen/Alibaba (one-time 1M tokens per model for 90 days, Singapore region; OAuth free tier
ended 15 Apr 2026); Moonshot Kimi direct ($1 top-up needed); DeepSeek direct (paid only); Cerebras
(card needed); GitHub Models (retired); Chutes (no free tier); Kiro (terms ban proxies); MiniMax
direct (free amount not confirmed). The NVIDIA key already serves kimi-k2.6, minimax-m3,
minimax-m2.7, glm-5.2, qwen3.5-397b, deepseek-v4-pro/flash, mistral-medium-3.5.
Candidates not tried: xKiro, BazaarLink, Kilo without a key. OmniRoute = reference only (stale).
Bots: CodeQL default setup on (owner); CodeRabbit not installed (overlaps council, noisy on bot
PRs); Dependabot as is (its pip entry is pointless: ggplay_dl unpinned and unused).

## 7. Owner decisions in force

A1 paid unlocks automatic only on offline apps. E1 Photos AMOLED belongs to Akash-Sriram.
L061 never suppress a signal. One release per app. Facebook = HushFacebook 0.17.0 on 584.0.0.51.56.
Reddit 2026.42.0 Adobo build deleted (23 Oct). Model checks routine, grouped (Sunday desk probe).
Dev branch for W16 is fine (23 Oct). Owner runs only paid unlocks and phone tests.

## 8. Owner to-do

- Phone: install Facebook 584 over the current app. Keep the patched Reddit 42 for now (W16 brings
  Morphe 42; no downgrade to 41 needed). Re-import Obtainium JSON if not done.
- Optional: Actions -> Batch Patch -> targets reddit (fills the empty shelf with Adobo 41).
- New chat: attach this file and a fresh main bundle (command in the prompt).
