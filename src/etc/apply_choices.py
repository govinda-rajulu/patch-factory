# Write /tmp/pf/choose/*.txt back into src/patches/. Refuses a banned include.
import os,glob
NL=chr(10); TAB=chr(9); PIPE=chr(124)
ban=[l.strip().lower() for l in open("src/patches/BANNED") if l.strip()]
exc=set()
for l in open("src/patches/EXCEPTIONS"):
    p=l.split(PIPE)
    if len(p)>=2: exc.add((p[0].strip(),p[1].strip()))
files=sorted(glob.glob("/tmp/pf/choose/*.txt"))
assert files, "no chooser files, run src/etc/chooser.py first"
plan=[]
for f in files:
    d=os.path.basename(f)[:-4]; inc=[]; ex=[]
    for l in open(f).read().split(NL):
        if not l or l.startswith("#"): continue
        parts=l.split(TAB)
        if len(parts)<2: continue
        p=parts[0][:1] if parts[0] else " "; n=parts[1].strip()
        if not n: continue
        if p=="+":
            assert not (any(k in n.lower() for k in ban) and (d,n) not in exc), \
                "BANNED patch marked + in %s: %s"%(d,n)
            inc.append(n)
        elif p=="-": ex.append(n)
    assert not (set(inc) & set(ex)), "a patch is both + and - in "+d
    plan.append((d,inc,ex))
ch=0
for d,inc,ex in plan:
    for side,vals in (("include",inc),("exclude",ex)):
        P="src/patches/%s/%s-patches"%(d,side)
        old=open(P).read() if os.path.exists(P) else ""
        new=(NL.join(vals)+NL) if vals else ""
        if new!=old:
            open(P,"w").write(new); ch+=1
            print("%-24s %-8s %d -> %d lines"%(d,side,len([x for x in old.split(NL) if x.strip()]),len(vals)))
    if not inc: print("  NOTE %s: empty include list, a gated target refuses to build"%d)
print("files changed:",ch)
