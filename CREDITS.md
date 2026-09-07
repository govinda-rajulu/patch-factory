# Credits

Generated from `src/targets.json` by `src/etc/credits.py`; **3. Validate** fails a push that
leaves it stale. Nothing in this repo is original patch work. It orchestrates other people's
patches, and every one of them deserves the click.

## Origin

Forked from [FiorenMas/Revanced-And-Revanced-Extended-Non-Root](https://github.com/FiorenMas/Revanced-And-Revanced-Extended-Non-Root)
(GPL-3.0). The APK download and split-merge logic in `src/build/utils.sh` is substantially
theirs. Everything under `src/etc/`, the target model in `src/targets.json`, the gates and the
generated docs are this repo's own work, also GPL-3.0.

## Patch providers, per app

| App | Provider | Source |
|---|---|---|
| AdGuard | rushiranpise | https://github.com/rushiranpise/morphe-patches |
| AdGuard | hoo-dles | https://github.com/hoo-dles/morphe-patches |
| ES File Explorer | ftl | https://github.com/BlazeFTL/FTL-Patches |
| Facebook | derevanced | https://github.com/RookieEnough/De-Vanced |
| Google Photos | rushiranpise | https://github.com/rushiranpise/morphe-patches |
| Instagram | piko | https://github.com/crimera/piko |
| Instagram | brosssh | https://github.com/brosssh/morphe-patches |
| JioHotstar | chiggi | https://github.com/durgesh0505/chiggi_morphe_patches |
| Key Mapper | lain | https://github.com/kiraio-moe/Lain-Patches |
| Microsoft Edge | quantavil | https://github.com/quantavil/edge-morphe-patches |
| MX Player Pro | ftl | https://github.com/BlazeFTL/FTL-Patches |
| MX Player Pro | paresh | https://gitlab.com/Paresh-Maheshwari/paresh-patches |
| Prime Video | hoo-dles | https://github.com/hoo-dles/morphe-patches |
| Reddit | adobo | https://github.com/jkennethcarino/adobo |
| Telegram | rushiranpise | https://github.com/rushiranpise/morphe-patches |
| Truecaller (combo) | bufferk | https://github.com/bufferk/morphe-patches |
| Truecaller (combo) | paresh | https://gitlab.com/Paresh-Maheshwari/paresh-patches |
| Truecaller (combo) | binarymend | https://github.com/binarymend/morphe-patches |
| YouTube | morphe | https://github.com/MorpheApp/morphe-patches |

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
| [pup](https://github.com/ericchiang/pup) | MIT | HTML parsing for the APKMirror lookup |
| [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) | MIT | Cloudflare challenge solver used to reach the stores |
| [CloudflareBypassForScraping](https://github.com/sarperavci/CloudflareBypassForScraping) | MIT | second bypass path when FlareSolverr fails |
| [ncipollo/release-action](https://github.com/ncipollo/release-action) | MIT | publishes each release |
| [Obtainium](https://github.com/ImranR98/Obtainium) | GPL-3.0 | how the phones track these releases |

## Licence

GPL-3.0, inherited from the template. See `LICENSE`. Patch bundles and the apps themselves are
not covered by it and belong to their respective owners.
