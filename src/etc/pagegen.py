#!/usr/bin/env python3
"""Generate the docs/index.html app catalog from src/targets.json.

The catalog used to be a hand-maintained JS array, so it drifted: it listed targets that
had been removed, and described one shipping app as "Not enabled yet" months after its
first release. targets.json is the only source of truth, so the page is generated from it.

  python3 src/etc/pagegen.py          rewrite the catalog in place
  python3 src/etc/pagegen.py --check   exit 1 if the page has drifted (used by CI)
"""
import io,json,re,sys
PAGE='docs/index.html'
OPEN='// >>> CATALOG GENERATED FROM src/targets.json - edit targets.json, not this'
CLOSE='// <<< CATALOG GENERATED'
def build():
    T=json.load(io.open('src/targets.json',encoding='utf-8'))
    rows=[]
    for t in T:
        if not t.get('enabled'): continue
        note=(t.get('note') or '').split('.')[0].strip()
        rows.append(" { prefix:%s, target:%s, name:%s, note:%s }"%(
            json.dumps(t.get('tag_prefix') or t['id']),json.dumps(t['id']),
            json.dumps(t.get('label') or t['id']),json.dumps(note)))
    return OPEN+"\nlet CATALOG = [\n"+",\n".join(rows)+"\n];\n"+CLOSE
def main():
    check='--check' in sys.argv
    s=io.open(PAGE,encoding='utf-8').read()
    new=build()
    if OPEN in s and CLOSE in s:
        a=s.index(OPEN); b=s.index(CLOSE)+len(CLOSE)
        cur=s[a:b]
        if cur==new:
            print("catalog already current (%d apps)"%new.count('prefix:')); return 0
        if check:
            print("::error::docs/index.html catalog has drifted from src/targets.json. Run: python3 src/etc/pagegen.py")
            return 1
        s=s[:a]+new+s[b:]
    else:
        m=re.search(r'^let CATALOG = \[.*?^\];\n',s,re.S|re.M)
        if not m:
            print("::error::cannot find the CATALOG array in %s"%PAGE); return 4
        if check:
            print("::error::%s has no generated-catalog markers yet. Run: python3 src/etc/pagegen.py"%PAGE); return 1
        s=s[:m.start()]+new+"\n"+s[m.end():]
    io.open(PAGE,'w',encoding='utf-8',newline='\n').write(s)
    n=new.count('prefix:')
    print("wrote %s catalog: %d apps, %d bytes total"%(PAGE,n,len(s.encode())))
    live=set(t['id'] for t in json.load(io.open('src/targets.json',encoding='utf-8')))
    for m in re.finditer(r'target:"([^"]+)"',new):
        assert m.group(1) in live, 'catalog names a target that is not in targets.json: '+m.group(1)
    return 0
sys.exit(main())
