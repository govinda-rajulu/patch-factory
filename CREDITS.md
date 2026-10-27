# Credits

Generated from `src/targets.json` by `src/etc/credits.py`; **3. Validate** fails a push that
leaves it stale. Nothing in this repo is original patch work. It orchestrates other people's
patches, and every one of them deserves the click.

## Origin

Forked from [FiorenMas/Revanced-And-Revanced-Extended-Non-Root](https://github.com/FiorenMas/Revanced-And-Revanced-Extended-Non-Root)
(GPL-3.0). The APK download and split-merge logic in `src/build/utils.sh` is substantially
theirs. Everything under `src/etc/`, the target model in `src/targets.json`, the gates and the
generated docs are this repo's own work, also GPL-3.0. Reviewed 23 September 2026 at
upstream commit `733e91b6fe90dace2295ac6a27ca66481c945e7d`; its large PR168/churn, mutable
release tag, public signing material and broad CI permissions were reviewed as warnings, not
as code or APKs to copy.

## Who built it

**Govindarajulu K** owns the repository and is its architect: he set the goals, chose the
apps and providers, made every keep and drop call, and ran every packet, build check and phone
test from his Google Cloud Shell.

Anthropic's **Claude models** (Opus, Sonnet and Haiku; model selection may vary) provided
engineering assistance: code, workflows, gates, tests, packet controllers, owner probes and
review records. Govindarajulu K reviewed the work and ran the resulting checks in Google Cloud Shell.
Each packet was built, tested and rehearsed in its sandbox, checked by its review agents, and
handed to the owner as one command.

## Patch providers, per app

| App | Provider | Source |
|---|---|---|
| AdGuard | rushiranpise | https://github.com/rushiranpise/morphe-patches |
| AdGuard | hoo-dles | https://github.com/hoo-dles/morphe-patches |
| Amazon Music | rookieenough | https://github.com/RookieEnough/De-Vanced |
| ES File Explorer | ftl | https://github.com/BlazeFTL/FTL-Patches |
| ES File Explorer | rushiranpise | https://github.com/rushiranpise/morphe-patches |
| Facebook | hushfacebook | https://github.com/SysAdminDoc/HushFacebook |
| Facebook | derevanced | https://github.com/RookieEnough/De-Vanced |
| Google Photos | rushiranpise | https://github.com/rushiranpise/morphe-patches |
| Google Photos | akash | https://github.com/Akash-Sriram/morphe-google-photos |
| Instagram | piko | https://github.com/crimera/piko |
| Instagram | hushgram | https://github.com/SysAdminDoc/HushGram |
| Instagram | oxbow | https://github.com/aic0d3r/oxbow |
| Instagram | brosssh | https://github.com/brosssh/morphe-patches |
| JioHotstar | chiggi | https://github.com/durgesh0505/chiggi_morphe_patches |
| Key Mapper | legendsciber | https://github.com/legendsciber/morphe-patches |
| Key Mapper | lain | https://github.com/kiraio-moe/Lain-Patches |
| LinkedIn | heyymichii | https://github.com/heyymichii/michii-patches |
| Microsoft Edge | quantavil | https://github.com/quantavil/edge-morphe-patches |
| MX Player Pro | ftl | https://github.com/BlazeFTL/FTL-Patches |
| MX Player Pro | paresh | https://gitlab.com/Paresh-Maheshwari/paresh-patches |
| Prime Video | hoo-dles | https://github.com/hoo-dles/morphe-patches |
| Reddit | morphe | https://github.com/MorpheApp/morphe-patches |
| Reddit | adobo | https://github.com/jkennethcarino/adobo |
| Reddit | alastor | https://github.com/Alastor-Kaneki/Morphe-Patches |
| Telegram | hushtelegram | https://github.com/SysAdminDoc/HushTelegram |
| Telegram | rushiranpise | https://github.com/rushiranpise/morphe-patches |
| Truecaller | heval99 | https://github.com/heval99/Heval-Morphe-Patches |
| Truecaller | bufferk | https://github.com/bufferk/morphe-patches |
| Truecaller | paresh | https://gitlab.com/Paresh-Maheshwari/paresh-patches |
| Truecaller | binarymend | https://github.com/binarymend/morphe-patches |
| YouTube | morphe | https://github.com/MorpheApp/morphe-patches |
| YouTube Music | morphe | https://github.com/MorpheApp/morphe-patches |

Providers publish patch bundles on their own schedule and under their own licences. This repo
**does not** vendor or modify their bundles: it downloads the release they published and passes
it to the patcher. If you are a provider and want your work out of this list, open an issue and
it will be removed the same day.

## Tooling

| Project | Licence | Used for |
|---|---|---|
| [morphe-desktop](https://github.com/MorpheApp/morphe-desktop) | GPL-3.0 | the patcher; every build calls it |
| [morphe-patches](https://github.com/MorpheApp/morphe-patches) | GPL-3.0 | upstream patch set, and the YouTube bundle used here |
| [APKEditor](https://github.com/REAndroid/APKEditor) | Apache-2.0 | merges split APKs into one installable file |
| [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) | MIT | Cloudflare challenge solver used to reach the stores |
| [CloudflareBypassForScraping](https://github.com/sarperavci/CloudflareBypassForScraping) | MIT | second bypass path when FlareSolverr fails |
| [ncipollo/release-action](https://github.com/ncipollo/release-action) | MIT | publishes each release |
| [Obtainium](https://github.com/ImranR98/Obtainium) | GPL-3.0 | how the phones track these releases |
| [tdl](https://github.com/iyear/tdl) | AGPL-3.0 | optional Telegram source helper retained from the upstream workflow; review before enabling |
| [markdown-badges](https://github.com/Ileriayo/markdown-badges) | MIT | badge style referenced by the upstream README; no badge assets vendored |

## Licence

GPL-3.0, inherited from the template. See `LICENSE`. Patch bundles and the apps themselves are
not covered by it and belong to their respective owners. Morphe-derived builds also carry the
upstream [Morphe NOTICE](https://github.com/MorpheApp/morphe-patches/blob/main/NOTICE); preserve
that notice and mark modified versions. Link third-party text/assets instead of copying them
unless a specific file and license have been reviewed.
