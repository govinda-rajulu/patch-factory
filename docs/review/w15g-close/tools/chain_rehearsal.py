#!/usr/bin/env python3
import base64, hashlib, json, os, shutil, subprocess, sys, textwrap, zipfile
from pathlib import Path

HERE = Path(os.environ.get('PF_CHAIN_WORK', '/tmp/pf-chain-rehearsal'))  # scratch folder (runs/ is recreated)
SRC = Path(os.environ.get('PF_REPO', '.')).resolve()  # repository checkout to rehearse
RUN = '123456'; ATTEMPT = '2'; IDENT = 'keymapper'
CERT = b'0' + bytes(range(1, 160)); PIN = hashlib.sha256(CERT).hexdigest()
BASE_ENV = {'GITHUB_RUN_ID': RUN, 'GITHUB_RUN_ATTEMPT': ATTEMPT,
            'GITHUB_REPOSITORY': 'fixture/repo', 'GITHUB_REF': 'refs/heads/main'}
APKNAME = 'key-mapper-v4.2.1-arm64-v8a.apk'


def cmd(args, cwd, env=None, check=False):
    e = os.environ.copy(); e.update(env or {})
    e['PYTHONUNBUFFERED'] = '1'; e['GIT_TERMINAL_PROMPT'] = '0'
    p = subprocess.run(args, cwd=cwd, env=e, text=True, capture_output=True)
    if check and p.returncode:
        raise RuntimeError('%s rc=%d\n%s\n%s' % (' '.join(map(str,args)), p.returncode, p.stdout[-3000:], p.stderr[-3000:]))
    return p


def write_zip(path, min_size=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, 'w') as z:
        # Like Play APKs in the 31 Oct smokes: a directory entry and the root source-stamp file.
        rows=[('assets/',b''),('AndroidManifest.xml',b'fixture manifest'),('classes.dex',b'd' * (1100000 if min_size else 100)),('resources.arsc',b'resources'),('stamp-cert-sha256',b'stamp digest')]
        for name,data in rows:
            info=zipfile.ZipInfo(name); info.compress_type=zipfile.ZIP_STORED
            offset=z.fp.tell()+30+len(name.encode())
            pad=(-offset)%4
            info.extra=(0xCAFE).to_bytes(2,'little')+pad.to_bytes(2,'little')+b'\0'*pad
            z.writestr(info,data)


def executable(path, text):
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text); path.chmod(0o755)


def install_tools(root, min_sdk):
    sdk = root / 'android-home' / 'build-tools' / '35.0.0'; sdk.mkdir(parents=True, exist_ok=True)
    b = base64.b64encode(CERT).decode()
    aapt = """#!/usr/bin/env python3
import os
print(\"package: name='io.github.sds100.keymapper' versionCode='42' versionName='4.2.1'\")
print(\"sdkVersion:'%s'\" % os.environ.get('FAKE_MIN_SDK','__SDK__'))
print(\"targetSdkVersion:'35'\")
""".replace('__SDK__', str(min_sdk))
    executable(sdk / 'aapt2', aapt)
    log = root / 'tool-calls.jsonl'
    logger = """import json, os, sys
with open(os.environ['FAKE_TOOL_LOG'], 'a') as f:
 f.write(json.dumps({'tool':TOOL,'argv':sys.argv[1:],'env':{k:os.environ.get(k) for k in ('KEYSTORE_PASS','KEYSTORE_ALIAS')}})+'\\n')
"""
    apksigner = "#!/usr/bin/env python3\nTOOL='apksigner'\n" + logger + r'''
import shutil, zipfile
if sys.argv[1] == 'sign':
    args=sys.argv[2:]; out=args[args.index('--out')+1]; source=args[-1]; shutil.copyfile(source,out)
    with zipfile.ZipFile(source) as old, zipfile.ZipFile(out+'.d','w') as new:
        for item in old.infolist():
            if not (item.filename.endswith('/') or item.filename == 'stamp-cert-sha256'): new.writestr(item, old.read(item.filename))
    os.replace(out+'.d', out)
    with zipfile.ZipFile(out,'a',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('META-INF/MANIFEST.MF',b'Manifest-Version: 1.0\n')
        z.writestr('META-INF/CERT.SF',b'Signature-Version: 1.0\n')
        z.writestr('META-INF/CERT.RSA',b'fixture certificate block')
    raise SystemExit(0)
if sys.argv[1] == 'verify':
    print('Number of signers: 1')
    print('Signer #1 certificate SHA-256 digest: '+os.environ.get('FAKE_CERT',''' + repr(PIN) + r'''))
    schemes=dict(x.split('=',1) for x in os.environ.get('FAKE_SCHEMES','v1=false,v2=true,v3=false,v3.1=false,v3.2=false,v4=false').split(','))
    for s in ('v1','v2','v3','v3.1','v3.2','v4'):
        print('Verified using %s scheme (APK Signature Scheme %s): %s' % (s,s,schemes.get(s,'false')))
    raise SystemExit(0)
raise SystemExit(7)
'''
    executable(sdk / 'apksigner', apksigner)
    executable(sdk / 'zipalign', "#!/usr/bin/env python3\nTOOL='zipalign'\n" + logger + "raise SystemExit(int(os.environ.get('FAKE_ZIPALIGN_EXIT','0')))\n")
    keytool = "#!/usr/bin/env python3\nimport base64,os,sys\nTOOL='keytool'\n" + logger + "sys.stdout.buffer.write(base64.b64decode(os.environ['FAKE_CERT_B64']))\n"
    executable(root / 'fake-bin' / 'keytool', keytool)
    return {'ANDROID_HOME': str(root / 'android-home'), 'PATH': str(root / 'fake-bin') + os.pathsep + os.environ.get('PATH',''),
            'FAKE_TOOL_LOG': str(log), 'FAKE_CERT_B64': b, 'FAKE_CERT': PIN,
            'FAKE_MIN_SDK': str(min_sdk), 'FAKE_ZIPALIGN_EXIT': '0',
            'FAKE_SCHEMES': ('v1=true,v2=true,v3=true,v3.1=false,v3.2=false,v4=false' if min_sdk < 24 else
                             'v1=false,v2=true,v3=false,v3.1=false,v3.2=false,v4=false')}


def clone(path, source=None):
    source = source or SRC
    args=['git','clone','-q',str(source),str(path)]
    if source == SRC: args[2:2] = ['--branch','packet/w15g']
    cmd(args, HERE, check=True)


def fixture_patch(case, winner, min_sdk, fallback=False, coe=False):
    root = HERE / 'runs' / case / 'patch'; shutil.rmtree(root.parent, ignore_errors=True); clone(root)
    # The key and target edits are fixture-only, committed so every fresh job has one source SHA.
    (root/'src/build/ci-signer.json').write_text(json.dumps({'certificate_sha256':PIN})+'\n')
    ts = json.loads((root/'src/targets.json').read_text())
    t = next(t for t in ts if t['id']==IDENT)
    if fallback:
        next(c for c in t['candidates'] if c['name']=='lain')['overrides']={'min_sdk_ceiling':29}
        (root/'src/targets.json').write_text(json.dumps(ts, indent=2, ensure_ascii=False)+'\n')
    (root/'.requested').write_text('lain\tUnlock Premium\n')
    (root/'morphe-desktop-fixture.jar').write_bytes(b'fixture')
    (root/'APKEditor.jar').write_bytes(b'fixture')
    (root/('09-%s.mpp' % winner)).write_bytes(b'fixture bundle')
    (root/'download').mkdir(); write_zip(root/'download/key-mapper.apk', False)
    (root/'release').mkdir(); write_zip(root/'release'/APKNAME, True)
    for n,v in {'.version':'4.2.1','.tagprefix':'key-mapper','.tagsuffix':'-b20261031'+RUN.zfill(20)+ATTEMPT.zfill(6),
                '.provider':'lain','.patchver':'1.0','.applied':'- Unlock Premium\n'}.items():
        (root/'release'/n).write_text(v+'\n' if not v.endswith('\n') else v)
    # The patch controller's fallback attempt carries build_attempts.view() bytes.
    cmd(['git','add','src/build/ci-signer.json','src/targets.json'],root,check=True)
    cmd(['git','-c','user.name=fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture signer and target'],root,check=True)
    if fallback:
        original=(root/'src/targets.json').read_text()
        # Restore the checkout's original and let the real helper write its winner view.
        cmd(['python3','-c',"import build_attempts; from pathlib import Path; p=Path('src/targets.json'); o=p.read_text(); build_attempts.view(Path('.'),'keymapper','lain',o)"],root,env={'PYTHONPATH':str(root/'src/build')},check=True)
    env=dict(BASE_ENV, **install_tools(root,min_sdk));
    if coe: env['COE']='true'
    # Real Patch commands: capture, unsigned identity, and sealed receipt draft.
    cmd(['python3','src/build/artifact_identity.py','capture-inputs',IDENT,winner],root,env,check=True)
    cmd(['python3','src/build/artifact_identity.py','verify-unsigned',IDENT],root,env,check=True)
    cmd(['python3','src/build/shadow_inputs.py','draft',IDENT],root,env,check=True)
    return root, env


def copy_contents(src, dst):
    dst.mkdir(parents=True,exist_ok=True)
    for p in src.iterdir():
        q=dst/p.name
        if p.is_dir(): shutil.copytree(p,q,symlinks=True)
        else: shutil.copy2(p,q)


def upload_patch(root, case):
    a=HERE/'runs'/case/'patch-artifact'; shutil.rmtree(a,ignore_errors=True); a.mkdir()
    for rel in ('release','build-evidence','shadow-evidence'):
        shutil.copytree(root/rel,a/rel,symlinks=True)
    (a/'src').mkdir(); shutil.copy2(root/'src/targets.json',a/'src/targets.json')
    return a


def sign_job(case, patch_root, patch_env, mutate=None, wrong_attempt=False, bad_cert=False, extra=False):
    root=HERE/'runs'/case/'sign'; shutil.rmtree(root,ignore_errors=True); clone(root, patch_root)
    env=dict(patch_env); env.update(install_tools(root,int(patch_env['FAKE_MIN_SDK'])))
    if wrong_attempt: env['GITHUB_RUN_ATTEMPT']='3'
    artifact=upload_patch(patch_root,case)
    if mutate=='apk':
        with (artifact/'release'/APKNAME).open('ab') as f: f.write(b'tamper')
    if mutate=='targets':
        (artifact/'src/targets.json').write_text((artifact/'src/targets.json').read_text()+'\n# edited\n')
    if extra: (artifact/'extra.txt').write_text('unexpected')
    handoff=root/'handoff'; shutil.copytree(artifact,handoff,symlinks=True)
    place=cmd(['python3','src/build/sign_apk.py','place',IDENT],root,env)
    if place.returncode: return root,env,'place',place
    hand=cmd(['python3','src/build/sign_apk.py','handoff',IDENT],root,env)
    if hand.returncode: return root,env,'handoff',hand
    if mutate or wrong_attempt: return root,env,'unexpected-pass',hand
    (root/'src/ks.keystore').write_bytes(b'fixture keystore')
    env['KEYSTORE_PASS']='fixture-password'; env['KEYSTORE_ALIAS']='fixture-alias'
    if bad_cert:
        env['FAKE_CERT_B64']=base64.b64encode(b'0'+bytes(range(2,161))).decode()
        env['FAKE_CERT']=hashlib.sha256(b'0'+bytes(range(2,161))).hexdigest()
    sg=cmd(['python3','src/build/sign_apk.py','sign',IDENT],root,env)
    if sg.returncode: return root,env,'sign',sg
    vr=dict(env); vr.pop('KEYSTORE_PASS',None); vr.pop('KEYSTORE_ALIAS',None)
    vrp=cmd(['python3','src/build/sign_apk.py','verify',IDENT],root,vr)
    if vrp.returncode: return root,env,'verify',vrp
    rc=cmd(['python3','src/build/release_contract.py',IDENT],root,vr)
    if rc.returncode: return root,env,'release-contract',rc
    return root,env,'PASS',rc


PUBLISH_WRAPPER = r'''
import copy, hashlib, json, os, pathlib, sys
sys.path.insert(0, str(pathlib.Path.cwd()/'src/build'))
import release_contract, shadow_inputs
release_contract.release_notes.inventory=lambda: []
sys.argv=['release_contract.py','keymapper','--github-output']
os.environ['GITHUB_OUTPUT']=str(pathlib.Path('github-output'))
release_contract.main()
root=pathlib.Path.cwd(); report=json.loads((root/'build-evidence/keymapper.json').read_text())
class API:
 repo='fixture/repo'
 def __init__(self):
  tag='key-mapper-v4.2.1'+(root/'release/.tagsuffix').read_text().strip()
  self.commit=report['inputs']['source_commit']; self.rows=[{'id':321,'name':pathlib.Path(report['output']['path']).name,'state':'uploaded','size':report['output']['bytes'],'digest':'sha256:'+report['output']['sha256']}]
  self.release={'id':123,'tag_name':tag,'draft':False,'prerelease':False,'published_at':'2026-10-31T08:00:00Z'}; self.documents={}
 def jobs(self):
  out=[]
  for i,(role,steps) in enumerate(shadow_inputs.SPLIT_JOBS,1):
   out.append({'id':87+i,'run_id':123456,'run_attempt':2,'head_sha':self.commit,'name':'build (keymapper) / '+role+' keymapper','status':'completed','conclusion':'success','steps':[{'name':s,'status':'completed','conclusion':'success'} for s in steps]})
  return out
 def get(self,path,limit=None):
  if '/actions/runs/' in path and '/jobs?' in path:return {'total_count':3,'jobs':self.jobs()}
  if '/actions/runs/' in path:return {'id':123456,'run_attempt':2,'head_sha':self.commit,'head_branch':'main','repository':{'full_name':self.repo},'status':'completed','conclusion':'success'}
  if '/git/ref/tags/' in path:return {'object':{'type':'commit','sha':self.commit}}
  if '/releases/tags/' in path:return self.release
  if '/assets?' in path:
   page=int(path.rsplit('page=',1)[1]); return copy.deepcopy(self.rows[(page-1)*100:page*100])
  raise AssertionError(path)
 def asset(self,a): return copy.deepcopy(self.documents[a['name']])
 def upload(self,path,tag):
  b=pathlib.Path(path).read_bytes(); n=pathlib.Path(path).name
  self.rows.append({'id':999,'name':n,'state':'uploaded','size':len(b),'digest':'sha256:'+hashlib.sha256(b).hexdigest()})
  self.documents[n]=json.loads(b)
api=API()
shadow_inputs.publish_receipt(root,'keymapper',dict(os.environ),api,api.upload)
'''


def publish_job(case, sign_root, sign_env):
    root=HERE/'runs'/case/'publish'; shutil.rmtree(root,ignore_errors=True); clone(root, sign_root)
    env=dict(sign_env); env.update(install_tools(root,int(sign_env['FAKE_MIN_SDK'])))
    artifact=HERE/'runs'/case/'signed-artifact'; shutil.rmtree(artifact,ignore_errors=True); artifact.mkdir()
    for rel in ('release','build-evidence','shadow-evidence'):
        shutil.copytree(sign_root/rel,artifact/rel,symlinks=True)
    (artifact/'src').mkdir(); shutil.copy2(sign_root/'src/targets.json',artifact/'src/targets.json')
    shutil.copytree(artifact,root/'handoff',symlinks=True)
    p=cmd(['python3','src/build/sign_apk.py','place',IDENT],root,env)
    if p.returncode:return False,'place',p
    out=cmd(['python3','-c',PUBLISH_WRAPPER],root,env)
    return out.returncode==0,('PASS' if out.returncode==0 else 'publish'),out


def case_positive(name,winner,min_sdk,fallback=False,coe=False,publish=True):
    try:
        pr, pe=fixture_patch(name,winner,min_sdk,fallback,coe)
        sr,se,stage,res=sign_job(name,pr,pe)
        if stage!='PASS': return False,stage,res
        if not publish: return True,'PASS',res
        ok,stage,res=publish_job(name,sr,se)
        return ok,stage,res
    except Exception as e:
        return False,'exception',e


def case_negative(name,kind):
    try:
        pr,pe=fixture_patch(name,'lain' if kind=='fallback' else 'legendsciber',28,kind=='fallback')
        sr,se,stage,res=sign_job(name,pr,pe,mutate={'tamper':'apk','targets':'targets'}.get(kind),wrong_attempt=kind=='attempt',bad_cert=kind=='cert',extra=kind=='extra')
        want='place' if kind in ('targets','extra') else 'handoff' if kind in ('tamper','attempt') else 'sign'
        if kind == 'cert':
            log=sr/'tool-calls.jsonl'
            calls=[json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []
            if any(c.get('tool') == 'apksigner' and c.get('argv',[None])[0] == 'sign' for c in calls):
                return False,'cert-apksigner-ran',res
        return stage==want,stage,res
    except Exception as e:
        return False,'exception',e


def main():
    shutil.rmtree(HERE/'runs',ignore_errors=True); (HERE/'runs').mkdir()
    cases=[('primary-sdk28',lambda:case_positive('primary-sdk28','legendsciber',28)),
           ('legacy-sdk21',lambda:case_positive('legacy-sdk21','legendsciber',21)),
           ('fallback-view',lambda:case_positive('fallback-view','lain',28,True)),
           ('coe-nonpublishing',lambda:case_positive('coe-nonpublishing','legendsciber',28,False,True,False)),
           ('tamper-apk',lambda:case_negative('tamper-apk','tamper')),
           ('wrong-run-attempt',lambda:case_negative('wrong-run-attempt','attempt')),
           ('edited-carried-targets',lambda:case_negative('edited-carried-targets','targets')),
           ('keystore-cert-mismatch',lambda:case_negative('keystore-cert-mismatch','cert')),
           ('extra-artifact-file',lambda:case_negative('extra-artifact-file','extra'))]
    passed=0
    for name,fn in cases:
        expected='STOP' if name in {'tamper-apk','wrong-run-attempt','edited-carried-targets','keystore-cert-mismatch','extra-artifact-file'} else 'PASS'
        try: ok,stage,res=fn()
        except Exception as e: ok,stage,res=False,'exception',e
        if expected=='STOP':
            got='STOP' if ok else ('PASS' if stage == 'PASS' else stage.upper())
            ok=(got=='STOP')
        else:
            got='PASS' if ok and stage == 'PASS' else stage.upper()
            ok=(got=='PASS')
        if ok: passed+=1
        print('CASE %s EXPECT %s GOT %s' % (name,expected,got))
        if not ok:
            detail = ((getattr(res,'stdout','') or '')[-1200:] + '\n' + (getattr(res,'stderr','') or '')[-3000:] if hasattr(res,'stdout') else str(res))
            (HERE/'runs'/name/'failure.txt').write_text(str(detail))
    print('CHAIN %s %d/%d' % ('OK' if passed==len(cases) else 'FAIL',passed,len(cases)))
    return 0 if passed==len(cases) else 1
if __name__=='__main__':sys.exit(main())
