import os, sys, json, collections
SHEET="docs/review/UNREVIEWED.tsv"
if not os.path.exists(SHEET): print("ABORT: %s not found. Run the generator first."%SHEET); sys.exit(1)
rows=[]
for l in open(SHEET):
    if l.startswith("#") or l.startswith("DECISION"): continue
    p=l.rstrip("\n").split("\t")
    if len(p)<4: continue
    rows.append(p)
dec=collections.defaultdict(lambda: {"INCLUDE":[], "EXCLUDE":[]})
skip=0
for r in rows:
    d=r[0].strip().upper()
    if d not in ("INCLUDE","EXCLUDE"): skip+=1; continue
    dec[r[2]][d].append(r[3])
if not dec:
    print("no decisions yet: every row still says ?. Nothing written."); sys.exit(1)
print("decisions found in %d bundle(s), %d rows still undecided\n"%(len(dec),skip))
changed=0
for dirn,v in sorted(dec.items()):
    for kind,fname in (("INCLUDE","include-patches"),("EXCLUDE","exclude-patches")):
        names=v[kind]
        if not names: continue
        p="src/patches/%s/%s"%(dirn,fname)
        cur=[l.strip() for l in open(p)] if os.path.exists(p) else []
        curset={c for c in cur if c and not c.startswith("#")}
        add=[n for n in names if n not in curset]
        if not add: print("  %-30s %-16s nothing new"%(dirn,fname)); continue
        os.makedirs(os.path.dirname(p),exist_ok=True)
        body=[c for c in cur if c.strip()]+add
        open(p,"w").write("\n".join(body)+"\n")
        changed+=1
        print("  %-30s %-16s +%d: %s"%(dirn,fname,len(add),", ".join(add)[:70]))
print("\nwrote %d file(s)"%changed)
if changed==0: sys.exit(1)
