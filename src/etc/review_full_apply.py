import json, os, re, subprocess, sys, collections
SHEET="docs/review/PATCHES.tsv"
if not os.path.exists(SHEET): print("ABORT: %s not found"%SHEET); sys.exit(1)
rows=[]
for l in open(SHEET):
    if l.startswith("#") or l.startswith("DECISION"): continue
    p=l.rstrip("\n").split("\t")
    if len(p)<8: continue
    rows.append(p)
bad=[r for r in rows if r[0].strip().upper() not in ("IN","OUT","?")]
if bad:
    print("ABORT: %d row(s) have a DECISION that is not IN, OUT or ?:"%len(bad))
    for r in bad[:5]: print("   %r  %s / %s"%(r[0],r[2],r[4]))
    sys.exit(1)

# group by bundle
by=collections.defaultdict(lambda: {"IN":[], "OUT":[], "mode":None, "target":None})
for r in rows:
    dec=r[0].strip().upper(); dirn=r[3]; name=r[4]; mode=r[7]
    by[dirn]["mode"]=mode; by[dirn]["target"]=r[2]
    by[dirn]["IN" if dec=="IN" else "OUT"].append(name)

def rd(p): return [l.rstrip("\n") for l in open(p)] if os.path.exists(p) else []
plan=[]
for dirn,v in sorted(by.items()):
    excl = v["mode"]=="EXCL"
    fn = "include-patches" if excl else "exclude-patches"
    want = v["IN"] if excl else v["OUT"]
    path = "src/patches/%s/%s"%(dirn,fn)
    cur=[l.strip() for l in rd(path) if l.strip() and not l.startswith("#")]
    if excl and not want:
        print("ABORT: %s would end up with an EMPTY include list on an exclusive target."%dirn)
        print("       build.sh refuses to publish when applied != listed, so that target would never build.")
        sys.exit(1)
    if sorted(cur)!=sorted(want): plan.append((path,cur,want,dirn,v["target"],fn))
if not plan:
    print("no changes: the sheet already matches the repo"); sys.exit(1)
print("%d file(s) will change\n"%len(plan))
for path,cur,want,dirn,tid,fn in plan:
    add=[x for x in want if x not in cur]; rem=[x for x in cur if x not in want]
    print("--- %-46s %-16s %d -> %d" % (path,fn,len(cur),len(want)))
    for x in add: print("      + %s"%x)
    for x in rem: print("      - %s"%x)
for path,cur,want,dirn,tid,fn in plan:
    os.makedirs(os.path.dirname(path),exist_ok=True)
    open(path,"w").write("\n".join(want)+"\n")
print("\nwrote %d file(s)"%len(plan))
