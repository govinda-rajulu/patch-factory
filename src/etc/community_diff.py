import json, os, sys, collections
OLD="src/community/bundles.json"; NEW=sys.argv[1]
if not os.path.exists(NEW): print("ABORT: %s missing"%NEW); sys.exit(1)
def load(p):
    if not os.path.exists(p): return None
    return json.load(open(p))
def flat(d):
    if not d: return {}
    compat=d.get("compatibilities") or []
    def pk(k):
        if isinstance(compat,list) and isinstance(k,int) and 0<=k<len(compat):
            v=compat[k]; return v if isinstance(v,list) else [v]
        if isinstance(compat,dict):
            v=compat.get(str(k)); return (v if isinstance(v,list) else [v]) if v else []
        return []
    out=collections.defaultdict(set)
    for b in (d.get("bundles") or []):
        r=str(b.get("repo",""))
        for p in (b.get("patches") or []):
            for pkg in pk(p.get("compatiblePackagesKey")):
                out[(r,pkg)].add(p.get("name"))
    return out
o,n=flat(load(OLD)),flat(load(NEW))
mypkgs={x["package"] for x in json.load(open("src/targets.json")) if x.get("enabled") is not False}
if not o:
    print("no previous snapshot: this run establishes the baseline. %d bundle/app pairs recorded."%len(n)); sys.exit(0)
newpairs=[k for k in n if k not in o]
gone=[k for k in o if k not in n]
addp=[(k,sorted(n[k]-o[k])) for k in n if k in o and n[k]-o[k]]
def mark(pkg): return "  <-- YOUR APP" if pkg in mypkgs else ""
print("=== new bundle/app pairs: %d ==="%len(newpairs))
for r,pkg in sorted(newpairs)[:25]: print("  %-34s %s%s"%(r,pkg,mark(pkg)))
print("\n=== NEW PATCHES in bundles you already track: %d pair(s) ==="%len(addp))
for (r,pkg),ps in sorted(addp):
    print("  %-34s %s%s"%(r,pkg,mark(pkg)))
    for x in ps[:8]: print("        + %s"%x)
print("\n=== pairs that disappeared: %d ==="%len(gone))
for r,pkg in sorted(gone)[:15]: print("  %-34s %s%s"%(r,pkg,mark(pkg)))
mine_new=[(k,ps) for k,ps in addp if k[1] in mypkgs]+[(k,["(new bundle)"]) for k in newpairs if k[1] in mypkgs]
print("\nAFFECTING YOUR APPS: %d"%len(mine_new))
