import csv, os, sys, collections
SHEET="docs/review/PATCHES.tsv"
if not os.path.exists(SHEET): print("ABORT: %s not found"%SHEET); sys.exit(1)
rows=[]
with open(SHEET,newline='',encoding='utf-8') as fh:
    for r in csv.reader(fh,delimiter='\t',quotechar='"'):
        if not r or r[0].startswith('#') or r[0]=='DECISION': continue
        if len(r)<8: continue
        rows.append([c.strip() for c in r])
print("read %d rows"%len(rows))
bad=[r for r in rows if r[0].upper() not in ("IN","OUT","?")]
if bad:
    print("ABORT: %d bad DECISION value(s)"%len(bad))
    for r in bad[:5]: print("   %r  %s / %s"%(r[0],r[2],r[4]))
    sys.exit(1)
LIVE=set()
if os.path.exists("src/targets.json"):
    import json as _j
    for t in _j.load(open("src/targets.json")):
        if t.get("enabled") is False: continue
        for c in (t.get("candidates") or [])+(t.get("extra_bundles") or []):
            if c.get("patch_dir"): LIVE.add(c["patch_dir"])
stale=sorted({r[3] for r in rows if LIVE and r[3] not in LIVE})
if stale:
    print("\nskipping %d bundle(s) no longer in targets.json: %s"%(len(stale),", ".join(stale)))
    rows=[r for r in rows if r[3] in LIVE]
by=collections.defaultdict(lambda: {"IN":[], "OUT":[], "mode":None, "target":None})
for r in rows:
    d=r[0].upper()
    by[r[3]]["mode"]=r[7]; by[r[3]]["target"]=r[2]
    by[r[3]]["IN" if d=="IN" else "OUT"].append(r[4])
EXC=set()
XP="src/patches/EXCEPTIONS"
if os.path.exists(XP):
    for l in open(XP):
        if l.strip() and not l.startswith("#"):
            p=l.split("|")
            if len(p)>=2: EXC.add((p[0].strip(),p[1].strip()))
def excused(r): return (r[3],r[4]) in EXC
banned=[r for r in rows if r[6].startswith("BANNED") and r[0].upper()=="IN" and not excused(r)]
ok=[r for r in rows if r[6].startswith("BANNED") and r[0].upper()=="IN" and excused(r)]
if ok:
    print("\ndocumented exceptions honoured (same rule bancheck.sh uses):")
    for r in ok: print("   %-18s %-34s %s"%(r[2],r[4][:34],r[3]))
conf  =[r for r in rows if r[6].startswith("CONFIRM") and r[0].upper()=="IN"]
if conf:
    print("\nnote: %d patch(es) marked IN are on your CONFIRM list (awaiting-decision, not blocked):"%len(conf))
    for r in conf: print("   %-18s %-40s %s"%(r[2],r[4][:40],r[6]))
if banned:
    print("\nABORT: %d patch(es) marked IN are on your BANNED list:"%len(banned))
    for r in banned: print("   %-18s %-40s %s"%(r[2],r[4][:40],r[6]))
    print("   bancheck.sh runs in 3. Validate and WILL fail the push on these.")
    print("   Fix the sheet, or set BANNED_OK=1 to override deliberately. Nothing written.")
    if os.environ.get("BANNED_OK")!="1": sys.exit(2)
plan=[]
for dirn,v in sorted(by.items()):
    excl=v["mode"]=="EXCL"
    fn="include-patches" if excl else "exclude-patches"
    want=v["IN"] if excl else v["OUT"]
    path="src/patches/%s/%s"%(dirn,fn)
    cur=[l.strip() for l in open(path)] if os.path.exists(path) else []
    cur=[c for c in cur if c and not c.startswith("#")]
    if excl and not want:
        print("ABORT: %s (%s) would have an EMPTY include list on an exclusive target."%(dirn,v["target"]))
        print("       build.sh refuses to publish when applied != listed, so %s would never build again."%v["target"])
        print("       Either mark at least one patch IN, or drop this bundle from src/targets.json. Nothing written.")
        sys.exit(1)
    if sorted(cur)!=sorted(want): plan.append((path,cur,want,fn))
if not plan: print("\nno changes: sheet already matches the repo"); sys.exit(1)
print("\n%d file(s) will change"%len(plan))
for path,cur,want,fn in plan:
    add=[x for x in want if x not in cur]; rem=[x for x in cur if x not in want]
    print("--- %-48s %d -> %d"%(path,len(cur),len(want)))
    for x in add: print("      + %s"%x)
    for x in rem: print("      - %s"%x)
for path,cur,want,fn in plan:
    os.makedirs(os.path.dirname(path),exist_ok=True)
    open(path,"w").write("\n".join(want)+"\n")
print("\nwrote %d file(s)"%len(plan))
