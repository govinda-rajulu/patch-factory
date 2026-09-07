#!/usr/bin/env python3
"""Classify a patcher list-patches dump against this repo's own rules.

Not a judgement engine. It applies BANNED and CONFIRM, which are lowercase substring rules,
plus a keyword set for the categories those files do not cover, and writes a decision sheet.
Nothing is added to an include list: a patch reaching an APK is Govind's call, always.

  python3 src/etc/classify.py docs/review/PATCHES-youtube.txt youtube-morphe
"""
import io,os,re,sys
def rd(p): return [l.rstrip('\n') for l in io.open(p,encoding='utf-8')] if os.path.exists(p) else []
def lower(xs): return [x.strip().lower() for x in xs if x.strip()]
DUMP=sys.argv[1] if len(sys.argv)>1 else 'docs/review/PATCHES-youtube.txt'
DIR=sys.argv[2] if len(sys.argv)>2 else 'youtube-morphe'
if not os.path.exists(DUMP): print("::error::%s missing"%DUMP); sys.exit(1)
BAN=lower(rd('src/patches/BANNED')); CON=lower(rd('src/patches/CONFIRM'))
if not BAN: print("::error::src/patches/BANNED is empty"); sys.exit(1)
INC=[l.split('|')[0].strip() for l in rd('src/patches/%s/include-patches'%DIR) if l.strip()]
EXC=[l.strip() for l in rd('src/patches/%s/exclude-patches'%DIR) if l.strip()]
# extra keyword classes for what BANNED/CONFIRM do not name
RISK={'spoof':'spoofs something a server can see',
      'potoken':'token generation, breaks when upstream changes',
      'gmscore':'needs a microG-style companion app installed',
      'package name':'changes app identity',
      'signature':'touches signing',
      'certificate':'touches signing or pinning',
      'advertising id':'server-visible identifier',
      'debug':'ships a debug surface',
      'developer option':'ships a developer surface',
      'employee':'ships an internal surface'}
recs=[];cur=None
for l in rd(DUMP):
    m=re.match(r'^Name:\s*(.+?)\s*$',l)
    if m: cur={'name':m.group(1),'enabled':None}; recs.append(cur); continue
    if cur is None: continue
    m=re.match(r'^Enabled:\s*(true|false)\s*$',l)
    if m and cur['enabled'] is None: cur['enabled']=(m.group(1)=='true')
recs=[r for r in recs if r['enabled'] is not None]
if not recs: print("::error::parsed 0 patch records from %s"%DUMP); sys.exit(1)
def why(n):
    low=n.lower()
    for k in BAN:
        if k in low: return 'BANNED','matches BANNED rule %r'%k
    for k in CON:
        if k in low: return 'CONFIRM','matches CONFIRM rule %r'%k
    for k,r in RISK.items():
        if k in low: return 'RISKY',r
    return 'CLEAN',''
rows=[];counts={}
for r in recs:
    st='in include' if r['name'] in INC else ('in exclude' if r['name'] in EXC else 'UNREVIEWED')
    cls,rsn=why(r['name'])
    rows.append((st,'on' if r['enabled'] else 'off',cls,r['name'],rsn))
    counts[cls]=counts.get(cls,0)+1
OUT='docs/review/DECISIONS-%s.tsv'%DIR
# Never clobber a decision already made: column 1 is the human's, so it is read back and kept.
PRIOR={}
for l in rd(OUT):
    if l.startswith('#') or l.startswith('decision\t'): continue
    p=l.split('\t')
    if len(p)>=5 and p[0].strip(): PRIOR[p[4]]=p[0].strip()
if PRIOR: print("   kept %d decision(s) you had already made in %s"%(len(PRIOR),OUT))
rows=[(PRIOR.get(d,''),a,b,c,d,e) for a,b,c,d,e in rows]
hdr=('# Edit column 1 to IN or OUT. Nothing here is applied automatically.\n'
     '# %d patches, %d already in the include list, %d in the exclude list.\n'%(len(recs),len(INC),len(EXC))
     +'decision\tstate\tdefault\tclass\tpatch\treason\n')
body=''.join('%s\t%s\t%s\t%s\t%s\t%s\n'%r for r in
             sorted(rows,key=lambda x:(x[1]!='UNREVIEWED',x[3],x[4])))
io.open(OUT,'w',encoding='utf-8',newline='\n').write(hdr+body)
un=[r for r in rows if r[1]=='UNREVIEWED']
print("   %s: %d patches, %d unreviewed"%(DUMP,len(recs),len(un)))
for cls in ('BANNED','CONFIRM','RISKY','CLEAN'):
    n=len([r for r in un if r[3]==cls])
    if n: print("      %-8s %3d unreviewed"%(cls,n))
print("   wrote %s"%OUT)
for r in un:
    if r[3] in ('BANNED','RISKY'): print("      %-8s %-46s %s"%(r[3],r[4][:46],r[5]))
