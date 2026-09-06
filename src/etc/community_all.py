import json, os, re, sys, collections
IDX="src/community/bundles.json"
d=json.load(open(IDX))
compat=d.get("compatibilities") or []
P=re.compile(r'^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+$')
def names(v,out=None):
    if out is None: out=[]
    if isinstance(v,str):
        if P.match(v): out.append(v)
    elif isinstance(v,dict):
        for k in ("packageName","name","package"):
            if isinstance(v.get(k),str) and P.match(v[k]): out.append(v[k]); return out
        for x in v.values(): names(x,out)
    elif isinstance(v,(list,tuple)):
        for x in v: names(x,out)
    return out
PN={}
if isinstance(compat,dict):
    for k,v in compat.items(): PN[str(k)]=names(v)
else:
    for i,v in enumerate(compat): PN[str(i)]=names(v)

bypkg=collections.defaultdict(list)
for b in (d.get("bundles") or []):
    seen=collections.defaultdict(int)
    for p in (b.get("patches") or []):
        for pkg in PN.get(str(p.get("compatiblePackagesKey")),[]): seen[pkg]+=1
    for pkg,n in seen.items(): bypkg[pkg].append((b,n))

t=json.load(open("src/targets.json"))
def norm(x): return re.sub(r'[^a-z0-9]','',str(x or "").lower()).replace("morphepatches","").replace("patches","")
print("EVERY community provider for EVERY app you build, wired or not")
print("="*88)
tot_missing=0
for x in sorted(t,key=lambda z:z["id"]):
    if x.get("enabled") is False: continue
    pkg=x["package"]
    wired=set()
    for c in (x.get("candidates") or [])+(x.get("extra_bundles") or []):
        for tok in (c.get("owner"),c.get("name"),c.get("project_id")):
            if tok: wired.add(norm(tok))
    offers=sorted(bypkg.get(pkg) or [], key=lambda z:-z[1])
    print("\n%-18s %s   (%d bundle(s) in the index)" % (x["id"],pkg,len(offers)))
    if not offers: print("     index has none: your provider is upstream or unlisted"); continue
    for b,n in offers:
        repo=str(b.get("repo","")); owner=repo.split("/")[0] if "/" in repo else repo
        hit = norm(owner) in wired or norm(b.get("author")) in wired or any(w and (w in norm(owner) or norm(owner) in w) for w in wired if w)
        src=b.get("source","github")
        print("     %-7s %-42s %3d patches  %s" % ("WIRED" if hit else "MISSING", src+":"+repo, n, ""))
        if not hit: tot_missing+=1
print("\n"+"="*88)
print("unwired provider/app pairs:",tot_missing)
