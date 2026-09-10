#!/usr/bin/env python3
"""Regenerate the README's live-state section from src/targets.json.

The README carried a hand-written state block dated 5 September and a hand-written
app list, so both drifted from the repo within a day. Everything between the markers
is generated. Run with --check in CI to fail a push that leaves them stale.
"""
import io,json,os,re,subprocess,sys
R='README.md'
OPEN='<!-- STATE:GENERATED - edit src/targets.json, not this block -->'
CLOSE='<!-- /STATE:GENERATED -->'
def sh(c):
    return subprocess.run(c,shell=True,capture_output=True,text=True,stdin=subprocess.DEVNULL).stdout.strip()
def build():
    T=json.load(io.open('src/targets.json',encoding='utf-8'))
    en=[t for t in T if t.get('enabled')]
    poll=[t for t in en if t.get('poll')]
    rows=[]
    for t in sorted(en,key=lambda x:(x.get('label') or x['id']).lower()):
        prov=[c['name'] for c in (t.get('candidates') or [])]+[e['name'] for e in (t.get('extra_bundles') or [])]
        rows.append('| %s | `%s` | `%s` | %s | %s | %s |'%(
            t.get('label') or t['id'], t['id'], t.get('tag_prefix') or t['id'],
            t.get('source') or 'apkmirror', ' + '.join(prov),
            'yes' if t.get('poll') else 'no'))
    cron=sh("grep -oE 'cron: \"[^\"]+\"' .github/workflows/ci.yml | head -1 | sed 's/cron: //; s/\"//g'") or 'unknown'
    q=sh("grep -vc '^#' src/patches/QUARANTINE 2>/dev/null") or '0'
    caps=sorted({t.get('max_patch_age_days',60) for t in T})
    tools=sh("grep -vc '^#' src/build/TOOLING.sha256 2>/dev/null") or '0'
    b=[OPEN,'',
       '## Current state',
       '',
       'Generated from `src/targets.json` by `src/etc/readmegen.py`. **3. Validate** fails a push',
       'that leaves this block stale, so it cannot drift.',
       '',
       '- **%d apps**, all enabled, %d polled by the scheduled build (`%s` UTC).'%(len(en),len(poll),cron),
       '- Patch-age warning: %s days. Age is advisory; requested/applied checks and build verification decide.'%(', '.join(str(c) for c in caps)),
       '- %s build tool(s) pinned by sha256 in `src/build/TOOLING.sha256`; a byte mismatch aborts the build.'%tools,
       '- %s patch(es) quarantined in `src/patches/QUARANTINE`, held out of every include list by CI.'%q.strip(),
       '',
       '| App | id | tag prefix | store | patch providers | polled |',
       '|---|---|---|---|---|---|']+rows+['',
       '### Build gates and separate validation checks','',
       '1. `bancheck.sh` blocks a BANNED patch reaching an include list; CONFIRM warns; EXCEPTIONS is dated.',
       '2. `quarantine.sh` keeps a patch that broke a real build out of every include list.',
       '3. `selections.sh` aborts if one patch name is requested under two bundles of one target.',
       '4. `build.sh` compares requested against applied **by name** and refuses to release on a gap.',
       '5. The package name is verified twice: on the downloaded APK, and against what the patcher filtered.',
       '6. `check_sdk.sh` rejects an excessive or unreadable `min_sdk_ceiling` measurement.',
       '7. `tooling.sh` verifies pup and APKEditor; morphe-desktop intentionally tracks latest.',
       '8. `readmegen.py --check` and `pagegen.py --check` fail a push that leaves docs stale.',
       '9. `shellcheck` at severity=error over every script in `src/build` and `src/etc`.',
       '',CLOSE]
    return '\n'.join(b)
def main():
    check='--check' in sys.argv
    s=io.open(R,encoding='utf-8').read()
    new=build()
    if OPEN in s and CLOSE in s:
        a=s.index(OPEN); b=s.index(CLOSE)+len(CLOSE)
        if s[a:b]==new:
            print("README state block already current"); return 0
        if check:
            print("::error::README.md state block is stale. Run: python3 src/etc/readmegen.py"); return 1
        s=s[:a]+new+s[b:]
    else:
        if check:
            print("::error::README.md has no generated state block. Run: python3 src/etc/readmegen.py"); return 1
        m=re.search(r'\n## State, .*?\Z',s,re.S)
        if m: s=s[:m.start()]+'\n'+new+'\n'
        else: s=s.rstrip('\n')+'\n\n'+new+'\n'
    io.open(R,'w',encoding='utf-8',newline='\n').write(s)
    print("wrote README state block: %d apps"%len([l for l in new.split('\n') if l.startswith('| ') and '` |' in l]))
    return 0
sys.exit(main())
