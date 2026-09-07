#!/usr/bin/env python3
"""Generate the target dropdown in .github/workflows/manual-patch.yml from src/targets.json.

The option list was hand-maintained, so it drifted: it still offered `truecaller`, a target
removed weeks ago, and a dispatch for it would fail after the runner had already started.
Every enabled target appears, nothing else does.

  python3 src/etc/dropgen.py           rewrite the option list
  python3 src/etc/dropgen.py --check   exit 1 if it has drifted (used by CI)
"""
import io,json,re,sys
W='.github/workflows/manual-patch.yml'
def wanted():
    T=json.load(io.open('src/targets.json',encoding='utf-8'))
    return [t['id'] for t in T if t.get('enabled')]
def main():
    check='--check' in sys.argv
    s=io.open(W,encoding='utf-8').read()
    ids=wanted()
    if not ids:
        print("::error::no enabled targets in src/targets.json"); return 4
    m=re.search(r'(^\s*default:\s*\')([a-z0-9-]+)(\'\s*\n\s*type:\s*choice\s*\n(\s*)options:\s*\n)((?:\s*-\s*\'[a-z0-9-]+\'\s*\n)+)',s,re.M)
    if not m:
        print("::error::cannot find the target dropdown in %s"%W); return 4
    ind=m.group(4)+'  '
    block=''.join("%s- '%s'\n"%(ind,i) for i in ids)
    dflt=m.group(2) if m.group(2) in ids else ids[0]
    cur=[x.strip().strip("'") for x in re.findall(r"-\s*'([a-z0-9-]+)'",m.group(5))]
    if cur==ids and m.group(2)==dflt:
        print("dropdown already current (%d targets)"%len(ids)); return 0
    if check:
        extra=[x for x in cur if x not in ids]; miss=[x for x in ids if x not in cur]
        if extra: print("::error::%s offers targets that do not exist: %s"%(W,', '.join(extra)))
        if miss:  print("::error::%s is missing enabled targets: %s"%(W,', '.join(miss)))
        if m.group(2)!=dflt: print("::error::%s default '%s' is not an enabled target"%(W,m.group(2)))
        print("Run: python3 src/etc/dropgen.py")
        return 1
    s=s[:m.start()]+m.group(1)+dflt+m.group(3)+block+s[m.end():]
    io.open(W,'w',encoding='utf-8',newline='\n').write(s)
    print("dropdown: %d targets, default '%s'"%(len(ids),dflt))
    for x in cur:
        if x not in ids: print("   removed dead option: %s"%x)
    for x in ids:
        if x not in cur: print("   added: %s"%x)
    chk=[y.strip().strip("'") for y in re.findall(r"-\s*'([a-z0-9-]+)'",re.search(r'options:\s*\n((?:\s*-\s*\'[a-z0-9-]+\'\s*\n)+)',s).group(1))]
    assert chk==ids, ('dropdown does not match targets.json after the write',chk,ids)
    return 0
sys.exit(main())
