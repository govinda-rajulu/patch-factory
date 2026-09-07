#!/usr/bin/env python3
"""Generate CREDITS.md from src/targets.json.

Every patch bundle this repo builds with is someone else's work. The provider list must
therefore come from the same place the build reads, or the credits go stale the moment a
provider is added or dropped.

  python3 src/etc/credits.py           write CREDITS.md
  python3 src/etc/credits.py --check   exit 1 if it has drifted (used by CI)
"""
import io,json,re,sys
P='CREDITS.md'
TOOLS=[("morphe-desktop","https://github.com/MorpheApp/morphe-desktop","GPL-3.0","the patcher; every build calls it"),
       ("morphe-patches","https://github.com/MorpheApp/morphe-patches","GPL-3.0","upstream patch set, and the YouTube bundle used here"),
       ("APKEditor","https://github.com/REAndroid/APKEditor","Apache-2.0","merges split APKs into one installable file"),
       ("pup","https://github.com/ericchiang/pup","MIT","HTML parsing for the APKMirror lookup"),
       ("FlareSolverr","https://github.com/FlareSolverr/FlareSolverr","MIT","Cloudflare challenge solver used to reach the stores"),
       ("CloudflareBypassForScraping","https://github.com/sarperavci/CloudflareBypassForScraping","MIT","second bypass path when FlareSolverr fails"),
       ("ncipollo/release-action","https://github.com/ncipollo/release-action","MIT","publishes each release"),
       ("Obtainium","https://github.com/ImranR98/Obtainium","GPL-3.0","how the phones track these releases")]
def build():
    T=json.load(io.open('src/targets.json',encoding='utf-8'))
    rows=[]; seen=set()
    for t in sorted(T,key=lambda x:(x.get('label') or x['id']).lower()):
        if not t.get('enabled'): continue
        for c in (t.get('candidates') or [])+(t.get('extra_bundles') or []):
            host=c.get('host','github')
            if host=='gitlab':
                url="https://gitlab.com/%s/%s"%(c.get('owner','?'),c.get('repo','?'))
            else:
                url="https://github.com/%s/%s"%(c.get('owner','?'),c.get('repo','?'))
            key=(c['name'],url)
            rows.append((t.get('label') or t['id'],c['name'],url,'' if key in seen else ''))
            seen.add(key)
    lines=["# Credits",
      "",
      "Generated from `src/targets.json` by `src/etc/credits.py`; **3. Validate** fails a push that",
      "leaves it stale. Nothing in this repo is original patch work. It orchestrates other people's",
      "patches, and every one of them deserves the click.",
      "",
      "## Origin",
      "",
      "Forked from [FiorenMas/Revanced-And-Revanced-Extended-Non-Root](https://github.com/FiorenMas/Revanced-And-Revanced-Extended-Non-Root)",
      "(GPL-3.0). The APK download and split-merge logic in `src/build/utils.sh` is substantially",
      "theirs. Everything under `src/etc/`, the target model in `src/targets.json`, the gates and the",
      "generated docs are this repo's own work, also GPL-3.0.",
      "",
      "## Patch providers, per app",
      "",
      "| App | Provider | Source |",
      "|---|---|---|"]
    for app,name,url,_ in rows:
        lines.append("| %s | %s | %s |"%(app,name,url))
    lines += ["",
      "Providers publish patch bundles on their own schedule and under their own licences. This repo",
      "**does not** vendor or modify their bundles: it downloads the release they published and passes",
      "it to the patcher. If you are a provider and want your work out of this list, open an issue and",
      "it will be removed the same day.",
      "",
      "## Tooling",
      "",
      "| Project | Licence | Used for |",
      "|---|---|---|"]
    for n,u,lic,why in TOOLS:
        lines.append("| [%s](%s) | %s | %s |"%(n,u,lic,why))
    lines += ["",
      "## Licence",
      "",
      "GPL-3.0, inherited from the template. See `LICENSE`. Patch bundles and the apps themselves are",
      "not covered by it and belong to their respective owners."]
    return "\n".join(lines)+"\n"
def main():
    check='--check' in sys.argv
    new=build()
    try: cur=io.open(P,encoding='utf-8').read()
    except FileNotFoundError: cur=''
    if cur==new:
        print("CREDITS.md already current (%d credited rows)"%len([l for l in new.split('\n') if l.startswith('| ') and 'http' in l])); return 0
    if check:
        print("::error::CREDITS.md is stale. Run: python3 src/etc/credits.py"); return 1
    io.open(P,'w',encoding='utf-8',newline='\n').write(new)
    n=len([l for l in new.split('\n') if l.startswith('| ') and 'http' in l and 'Licence' not in l])
    print("wrote CREDITS.md: %d credited rows"%n); return 0
sys.exit(main())
