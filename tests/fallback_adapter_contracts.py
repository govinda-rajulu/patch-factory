"""Actual shell downloaders, external network/tool process fixtures, no live claims."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

import source_fallback_contracts as fixtures

ROOT=Path(__file__).resolve().parents[1]


class AdapterProcessContracts(unittest.TestCase):
    def case(self,store,kind,alternate,fail=False,missing=False):
        tmp=tempfile.TemporaryDirectory(prefix='pf-real-adapter-');self.addCleanup(tmp.cleanup)
        root=Path(tmp.name)
        shutil.copytree(ROOT/'src',root/'src',ignore=shutil.ignore_patterns('__pycache__'))
        target={'id':'fixture','enabled':True,'package':'com.reddit.frontpage','apk_name':'fixture',
                'apk_type':kind,'source':store,'min_sdk_ceiling':29}
        (root/'src/targets.json').write_text(json.dumps([target]))
        mappings={'apkpure':{'com.reddit.frontpage':{'download_url':'https://apkpure.com/reddit/com.reddit.frontpage/download'}},
                  'apkmirror':{'com.reddit.frontpage':{'list_url':'https://www.apkmirror.com/uploads/?appcategory=reddit','org':'redditinc','name':'reddit'}}}
        (root/'src/build/helper/apps.json').write_text(json.dumps(mappings))
        variant={'kind':kind, 'abis':[], 'min_sdk':29, 'apkmirror_url':None}
        if store=='apkmirror':
            variant['apkmirror_url']='https://www.apkmirror.com/apk/redditinc/reddit/reddit-2026-38-0-release/reddit-fixture-android-apk-download/'
        (root/'qualified-variant.json').write_text(json.dumps({
            'source':store,'package':target['package'],'version':'2026.38.0',
            'mapping':mappings[store][target['package']],'ceiling':29,'variant':variant}))
        # External tooling bootstrap is a fixture. Keep actual source_alternate, utils,
        # curl/wget invocation, JSON response parsing, version selection and raw hooks.
        (root/'src/build/tooling.sh').write_text('#!/bin/bash\nexit 0\n')
        (root/'APKEditor.jar').write_bytes(b'fixture editor; java process is mocked')
        pup='''#!/usr/bin/env python3
import json,os,sys
sys.stdin.read()
s=sys.argv[1]
if s=='h5.appRowTitle a.fontBlack json{}': print(json.dumps([{'text':'Reddit 2026.38.0','href':'/apk/redditinc/reddit/reddit-2026-38-0-release/'}]))
elif s=='div.variants-table': print('<div class="table-row"><span class="apkm-badge">'+('BUNDLE' if os.environ['FIXTURE_KIND']=='bundle' else 'APK')+'</span><a class="accent_color" href="/variant/">variant</a></div>')
elif s=='a.downloadButton attr{href}': print('/step/?forcebaseapk=true' if os.environ['FIXTURE_KIND']=='apk' else '/step/')
elif s=='a#download-link attr{href}': print('/binary?token=FAKE_SECRET')
elif s=='a#download_link attr{href}' and os.environ.get('FIXTURE_MISSING')!='1': print('https://download.example.invalid/binary?token=FAKE_SECRET')
'''
        with zipfile.ZipFile(root/'pup.zip','w') as z:
            i=zipfile.ZipInfo('pup');i.external_attr=0o100755<<16;z.writestr(i,pup)
        raw=root/'original.fixture'
        if kind=='bundle':
            with zipfile.ZipFile(raw,'w') as z:z.writestr('base.apk',fixtures.apk_bytes())
        else:raw.write_bytes(fixtures.apk_bytes())
        (root/'standalone.fixture').write_bytes(fixtures.apk_bytes())
        bin=root/'fakebin';bin.mkdir()
        programs={
            'curl':'''#!/usr/bin/env python3
import json,sys
if '-d' in sys.argv:
 with open('page.calls','a') as f:f.write(json.loads(sys.argv[sys.argv.index('-d')+1])['url']+'\\n')
print(json.dumps({'status':'ok','solution':{'status':200,'url':'https://example.invalid/fixture','response':'<html>fixture</html>','cookies':[],'userAgent':'fixture'}}))
''',
            'wget':'''#!/usr/bin/env python3
import os,sys,shutil
args=sys.argv[1:]
if '-O' not in args:sys.exit(0)
out=args[args.index('-O')+1]
if os.environ.get('FIXTURE_FAIL')=='1':
 open(out,'wb').write(b'partial');sys.exit(8)
shutil.copyfile('original.fixture',out)
''',
            'java':'''#!/usr/bin/env python3
import sys,shutil
with open('java.calls','a') as f:f.write('merge called\\n')
shutil.copyfile('standalone.fixture',sys.argv[sys.argv.index('-o')+1])
'''}
        for name,text in programs.items():p=bin/name;p.write_text(text);p.chmod(0o755)
        env=dict(os.environ,PATH=str(bin)+':'+os.environ['PATH'],FIXTURE_KIND=kind,
                 FIXTURE_FAIL='1' if fail else '0',FIXTURE_MISSING='1' if missing else '0')
        script='source_alternate.sh' if alternate else 'source_download.sh'
        args=['bash','src/build/'+script,'fixture','2026.38.0']+([store] if alternate else [])
        p=subprocess.run(args,cwd=root,env=env,capture_output=True,text=True,timeout=20)
        self.assertNotIn('FAKE_SECRET',p.stdout+p.stderr)
        return root,p

    def test_real_primary_apk_success_both_stores(self):
        for store in ('apkmirror','apkpure'):
            with self.subTest(store=store):
                r,p=self.case(store,'apk',False)
                self.assertEqual(p.returncode,0,p.stdout+p.stderr)
                self.assertEqual((r/'download/fixture.apk').read_bytes(),(r/'original.fixture').read_bytes())
                self.assertFalse((r/'java.calls').exists())

    def test_real_alternate_raw_apk_and_bundle_never_call_merger(self):
        for store in ('apkmirror','apkpure'):
            for kind in ('apk','bundle'):
                with self.subTest(store=store,kind=kind):
                    r,p=self.case(store,kind,True)
                    self.assertEqual(p.returncode,0,p.stdout+p.stderr)
                    rows=list((r/'download').iterdir());self.assertEqual(len(rows),1)
                    self.assertEqual(rows[0].read_bytes(),(r/'original.fixture').read_bytes())
                    self.assertFalse((r/'java.calls').exists())

    def test_real_primary_bundle_still_calls_existing_merger(self):
        for store in ('apkmirror','apkpure'):
            with self.subTest(store=store):
                r,p=self.case(store,'bundle',False)
                self.assertEqual(p.returncode,0,p.stdout+p.stderr)
                self.assertEqual((r/'java.calls').read_text(),'merge called\n')
                self.assertEqual((r/'download/fixture.apk').read_bytes(),(r/'standalone.fixture').read_bytes())

    def test_reviewed_variant_page_is_selected_not_first_table_row(self):
        r,p=self.case('apkmirror','bundle',True)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        pages=(r/'page.calls').read_text().splitlines()
        self.assertEqual(pages[:2],[
            'https://www.apkmirror.com/apk/redditinc/reddit/reddit-2026-38-0-release/',
            'https://www.apkmirror.com/apk/redditinc/reddit/reddit-2026-38-0-release/reddit-fixture-android-apk-download/'])
        self.assertNotIn('https://www.apkmirror.com/variant/',pages)

    def test_real_alternate_transfer_failures_do_not_merge_or_succeed(self):
        for store in ('apkmirror','apkpure'):
            with self.subTest(store=store):
                r,p=self.case(store,'bundle',True,fail=True)
                self.assertEqual(p.returncode,1,p.stdout+p.stderr)
                self.assertFalse((r/'java.calls').exists())
                self.assertNotIn('Successfully downloaded',p.stdout)

    def test_reddit_missing_link_is_a_failure_before_transfer(self):
        r,p=self.case('apkpure','bundle',True,missing=True)
        self.assertEqual(p.returncode,1,p.stdout+p.stderr)
        self.assertIn('missing-download-link',p.stdout)
        self.assertFalse(list((r/'download').iterdir()));self.assertFalse((r/'java.calls').exists())

    def test_full_fallback_cli_with_process_boundary_tool_fixtures(self):
        import source_fallback as fb
        for kind, signer_exit in (('apk', 0), ('bundle', 0), ('bundle', 1)):
            with self.subTest(kind=kind, signer_exit=signer_exit):
                r, initial = self.case('apkmirror', kind, True)
                self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)
                targets = json.loads((r/'src/targets.json').read_text())
                targets[0]['source'] = 'apkpure'
                (r/'src/targets.json').write_text(json.dumps(targets))
                raw = r/'original.fixture'
                admitted = {'source': 'apkmirror', 'version_name': '2026.38.0',
                            'version_code': '2038000', 'container': fb.file_record(raw),
                            'certificate_sha256': fixtures.CERT,
                            'mapping': {'list_url': 'https://www.apkmirror.com/uploads/?appcategory=reddit',
                                        'org': 'redditinc', 'name': 'reddit'},
                            'evidence': 'docs/review/source-qualifications/fixture.json'}
                admitted['variant']={'kind':kind, 'abis':[], 'min_sdk':29,
                    'apkmirror_url':'https://www.apkmirror.com/apk/redditinc/reddit/reddit-2026-38-0-release/reddit-fixture-android-apk-download/'}
                policy = {'schema': 1, 'targets': {'fixture': {
                    'package': 'com.reddit.frontpage', 'primary': 'apkpure',
                    'blocked_reason': 'synthetic fixture only', 'admissions': [admitted]}}}
                (r/fb.POLICY).write_text(json.dumps(policy))
                ev = {'schema': 1, 'target': 'fixture', 'package': 'com.reddit.frontpage',
                      'source': 'apkmirror', 'version_name': '2026.38.0', 'version_code': '2038000',
                      'container': admitted['container'], 'certificate_sha256': fixtures.CERT,
                      'publisher_anchor_reviewed': True, 'variant_compatibility_reviewed': True}
                ev['variant']=admitted['variant']
                e = r/admitted['evidence']; e.parent.mkdir(parents=True,exist_ok=True); e.write_text(json.dumps(ev))
                # Fake binaries are explicit process fixtures, not actual Android verification.
                bin = r/'fakebin'
                (r/'src/build/tooling.sh').write_text(
                    '#!/bin/bash\ncp ' + str(r/'pup.zip') + ' ./pup.zip\ncp ' +
                    str(r/'APKEditor.jar') + ' ./APKEditor.jar\n')
                (bin/'wget').write_text(
                    '#!/usr/bin/env python3\nimport sys,shutil\n'
                    'a=sys.argv[1:]\nif "-O" in a:shutil.copyfile(' + repr(str(raw)) +
                    ',a[a.index("-O")+1])\n')
                (bin/'java').write_text(
                    '#!/usr/bin/env python3\nimport sys,shutil\nshutil.copyfile(' +
                    repr(str(r/'standalone.fixture')) + ',sys.argv[sys.argv.index("-o")+1])\n')
                (bin/'pup-fixture').write_text('')
                # This pup fixture needs its format selection after clean_env drops test env.
                with zipfile.ZipFile(r/'pup.zip') as z: text = z.read('pup').decode()
                text = text.replace("os.environ['FIXTURE_KIND']", repr(kind))
                with zipfile.ZipFile(r/'pup.zip', 'w') as z:
                    i=zipfile.ZipInfo('pup');i.external_attr=0o100755<<16;z.writestr(i,text)
                for name, text in {
                    'aapt2': "#!/bin/sh\nprintf \"package: name='com.reddit.frontpage' versionCode='2038000' versionName='2026.38.0'\\nsdkVersion:'29'\\n\"\n",
                    'apksigner': '#!/bin/sh\nprintf "Number of signers: 1\\nSigner #1 certificate SHA-256 digest: ' +
                                 fixtures.CERT + '\\n"\nexit ' + str(signer_exit) + '\n'
                }.items():
                    p=bin/name;p.write_text(text);p.chmod(0o755)
                p = subprocess.run([sys.executable, 'src/build/source_fallback.py', 'fixture', '2026.38.0'],
                                   cwd=r, env=dict(os.environ, PATH=str(bin)+':'+os.environ['PATH']),
                                   capture_output=True, text=True, timeout=25)
                self.assertNotIn('FAKE_SECRET', p.stdout+p.stderr)
                self.assertEqual(p.returncode, 0 if signer_exit == 0 else 1, p.stdout+p.stderr)
                if signer_exit == 0:
                    self.assertIn('SOURCE_FALLBACK_VERIFIED',p.stdout)
                    receipt=json.loads((r/fb.RECEIPT).read_text())
                    self.assertEqual(len(receipt['original']['splits']),1)
                    self.assertEqual((r/'download/fixture.apk').read_bytes(),
                                     (r/'standalone.fixture').read_bytes())
                else:
                    self.assertFalse((r/fb.RECEIPT).exists())


if __name__=='__main__':unittest.main()
