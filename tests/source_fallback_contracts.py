import copy
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/build'))
import source_fallback as fb
import input_recipe

CERT = '1' * 64


def apk_bytes(abi=None, elf=True):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as z:
        z.writestr('AndroidManifest.xml', b'SYNTHETIC MANIFEST; metadata reader is mocked')
        z.writestr('classes.dex', b'f' * 1000100)
        if abi:
            header = b'\x7fELF\x02\x01' + b'\0' * 12 + (183 if elf else 62).to_bytes(2, 'little')
            z.writestr('lib/' + abi + '/libfixture.so', header)
    return stream.getvalue()


class FallbackContracts(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='pf-fallback-test-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for d in ('src', 'docs', '.github'):
            shutil.copytree(ROOT/d, self.root/d, ignore=shutil.ignore_patterns('__pycache__'))
        self.ident = 'reddit'
        self.t = fb.target(self.root, self.ident)
        self.meta = {'package': self.t['package'], 'version_name': '2026.38.0',
                     'version_code': '2038000', 'min_sdk': 29}
        self.raw = self.root / 'fixture.apk'
        self.raw.write_bytes(apk_bytes())
        self.a = {'source': 'apkmirror', 'version_name': self.meta['version_name'],
                  'version_code': self.meta['version_code'], 'container': fb.file_record(self.raw),
                  'certificate_sha256': CERT,
                  'mapping': {'list_url': 'https://www.apkmirror.com/uploads/?appcategory=reddit',
                              'org': 'redditinc', 'name': 'reddit'},
                  'evidence': 'docs/review/source-qualifications/reddit-fixture.json'}
        self.a['variant'] = {'kind': 'apk', 'abis': [], 'min_sdk': 29,
                             'apkmirror_url': 'https://www.apkmirror.com/apk/redditinc/reddit/'
                             'reddit-2026-38-0-release/reddit-fixture-android-apk-download/'}
        self.events = []
        self.env = dict(os.environ, GH_TOKEN='SECRET_GH', GITHUB_TOKEN='SECRET_GITHUB',
                        KEYSTORE_PASS='SECRET_KEY', KEYSTORE_B64='SECRET_B64',
                        JAVA_TOOL_OPTIONS='SECRET_JAVA', HTTP_PROXY='SECRET_PROXY')

    def authorize_fixture(self):
        doc = json.loads((self.root/fb.POLICY).read_text())
        doc['targets'][self.ident]['admissions'] = [self.a]
        (self.root/fb.POLICY).write_text(json.dumps(doc))
        ev = {'schema': 1, 'target': self.ident, 'package': self.t['package'],
              'source': self.a['source'], 'version_name': self.a['version_name'],
              'version_code': self.a['version_code'], 'container': self.a['container'],
              'certificate_sha256': self.a['certificate_sha256'],
              'publisher_anchor_reviewed': True, 'variant_compatibility_reviewed': True}
        ev['variant'] = self.a['variant']
        path = self.root/self.a['evidence'];path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(ev))

    def metadata(self, *args, **kwargs):
        self.events.append('metadata')
        meta = dict(self.meta)
        if kwargs.get('original') and Path(args[1]).name == 'split-1.apk':
            meta.update(split='config.arm64_v8a', version_name='')
        return meta

    def certificate(self, *args):
        self.events.append('certificate')
        return CERT

    def runner(self, args, cwd, env, timeout=1200):
        self.assertFalse(any(k in env for k in ('GH_TOKEN','GITHUB_TOKEN','KEYSTORE_PASS',
                         'KEYSTORE_B64','JAVA_TOOL_OPTIONS','HTTP_PROXY')))
        if args[0] == 'bash':
            self.events.append('download')
            self.assertEqual(args, ['bash','src/build/source_alternate.sh',self.ident,
                                   self.a['version_name'],self.a['source']])
            d=cwd/'download';d.mkdir()
            shutil.copyfile(self.raw,d/'original')
        else:
            self.events.append('merge')
            self.assertIn('certificate',self.events)
            Path(args[-1]).write_bytes(apk_bytes())

    def execute(self):
        with patch.object(fb,'run_checked',side_effect=self.runner), \
             patch.object(fb,'apk_metadata',side_effect=self.metadata), \
             patch.object(fb,'apk_certificate',side_effect=self.certificate):
            return fb.execute(self.root,self.ident,self.a['version_name'],self.env)

    def inspect(self, certificate=None, metadata=None):
        scratch=self.root/'scratch';scratch.mkdir(exist_ok=True)
        with patch.object(fb,'apk_metadata',side_effect=metadata or self.metadata), \
             patch.object(fb,'apk_certificate',side_effect=certificate or self.certificate):
            return fb.inspect_original(self.root,self.raw,self.t,self.a,self.env,scratch)

    def make_bundle(self):
        with zipfile.ZipFile(self.raw,'w') as z:
            z.writestr('base.apk',apk_bytes())
            z.writestr('split_config.arm64_v8a.apk',apk_bytes('arm64-v8a'))
        self.a['container']=fb.file_record(self.raw)
        self.a['variant'].update(kind='bundle', abis=['arm64-v8a'])

    def test_all_14_block_before_network_and_any_output(self):
        doc=fb.policy(self.root)
        self.assertEqual(len(doc['targets']),14)
        before=set(self.root.iterdir())
        with patch.object(fb,'run_checked',side_effect=AssertionError('unexpected network')):
            for ident,row in doc['targets'].items():
                with self.subTest(target=ident):
                    self.assertNotIn('1.0',[a['version_name'] for a in row['admissions']])
                    with self.assertRaisesRegex(ValueError,'BLOCKED_UNQUALIFIED_SOURCE'):
                        fb.execute(self.root,ident,'1.0',self.env)
        self.assertEqual(set(self.root.iterdir()),before)

    def test_policy_missing_extra_duplicate_json_unknown_fields(self):
        path=self.root/fb.POLICY;original=path.read_text()
        for mutate in (lambda d:d['targets'].pop('reddit'),
                       lambda d:d['targets'].update(unknown=d['targets']['reddit']),
                       lambda d:d['targets']['reddit'].update(primary='apkmirror'),
                       lambda d:d['targets']['reddit'].update(package='wrong.package'),
                       lambda d:d['targets']['reddit'].update(enabled=True)):
            d=json.loads(original);mutate(d);path.write_text(json.dumps(d))
            with self.assertRaises(ValueError):fb.policy(self.root)
        path.write_text('{"schema":1,"schema":1,"targets":{}}')
        with self.assertRaises(ValueError):fb.policy(self.root)

    def test_exact_version_required_and_no_latest_nearest_or_ceiling_bypass(self):
        self.authorize_fixture()
        for version in ('','latest','2026.38','2026.38.1','2026.38.0-beta','1;echo unsafe'):
            with self.subTest(version=version),self.assertRaises(ValueError):
                fb.admission(self.root,self.ident,version)
        for ident,version in [('facebook','491.0.0.0.0'),('mxplayer','1.93.5')]:
            with self.assertRaisesRegex(ValueError,'ceiling'):fb.admission(self.root,ident,version)
        self.assertEqual(fb.version_key('1.93.4.0'),fb.version_key('1.93.4'))
        targets=json.loads((self.root/'src/targets.json').read_text())
        next(t for t in targets if t['id']==self.ident)['any_version']=True
        (self.root/'src/targets.json').write_text(json.dumps(targets))
        with self.assertRaisesRegex(ValueError,'any-version'):fb.admission(self.root,self.ident,self.a['version_name'])

    def test_admission_requires_original_signer_bytes_and_review_evidence(self):
        self.authorize_fixture();path=self.root/fb.POLICY;original=path.read_text()
        for mutate in (lambda a:a.update(certificate_sha256=''),
                       lambda a:a.update(source='apkpure'),
                       lambda a:a.update(evidence='https://example.org/metadata'),
                       lambda a:a.update(evidence='docs/review/source-qualifications/../missing.json'),
                       lambda a:a.update(container={'bytes':True,'sha256':'0'*64}),
                       lambda a:a.update(version_code=True),
                       lambda a:a['mapping'].update(name='wrong')):
            d=json.loads(original);mutate(d['targets'][self.ident]['admissions'][0]);path.write_text(json.dumps(d))
            with self.assertRaises(ValueError):fb.policy(self.root)
        path.write_text(original)
        ev=self.root/self.a['evidence'];data=json.loads(ev.read_text());data['publisher_anchor_reviewed']=False;ev.write_text(json.dumps(data))
        with self.assertRaises(ValueError):fb.policy(self.root)

    def test_source_mapping_refuses_other_package_and_hosts(self):
        for source,mapping in [
            ('play',{}),('apkpure',{'download_url':'https://evil.example/x/com.reddit.frontpage/download'}),
            ('apkpure',{'download_url':'https://apkpure.com/x/wrong.package/download'}),
            ('apkmirror',{'org':'redditinc','name':'reddit','list_url':'http://www.apkmirror.com/uploads/?appcategory=reddit'})]:
            with self.assertRaises(ValueError):fb.mapping_ok(source,mapping,self.t['package'])
        fb.mapping_ok('apkpure',{'download_url':'https://apkpure.com/reddit/com.reddit.frontpage/download'},self.t['package'])

    def test_standalone_happy_path_keeps_bytes_and_redacts_environment(self):
        self.authorize_fixture();proof=self.execute()
        self.assertEqual((self.root/'download/reddit.apk').read_bytes(),self.raw.read_bytes())
        self.assertTrue(proof['original']['standalone'])
        self.assertNotIn('merge',self.events)
        self.assertEqual(len([p for p in self.root.glob('.source-fallback-*') if p.is_dir()]),1)

    def test_bundle_verifies_every_original_signer_before_merge(self):
        self.make_bundle();self.authorize_fixture();proof=self.execute()
        self.assertFalse(proof['original']['standalone'])
        self.assertEqual(len(proof['original']['splits']),2)
        self.assertEqual(self.events.count('certificate'),2)
        self.assertLess(max(i for i,e in enumerate(self.events) if e=='certificate'),self.events.index('merge'))

    def test_success_preserves_failed_primary_bytes_and_other_downloads(self):
        self.authorize_fixture();d=self.root/'download';d.mkdir()
        (d/'reddit.apk').write_bytes(b'partial primary')
        (d/'keep.txt').write_bytes(b'unrelated')
        self.execute()
        work=next(p for p in self.root.glob('.source-fallback-*') if p.is_dir())
        self.assertEqual((work/'preserved-primary.apk').read_bytes(),b'partial primary')
        self.assertEqual((d/'keep.txt').read_bytes(),b'unrelated')

    def test_wrong_container_fails_before_android_readers(self):
        self.raw.write_bytes(self.raw.read_bytes()+b'changed')
        with patch.object(fb,'apk_metadata',side_effect=AssertionError('reader should not run')):
            with self.assertRaisesRegex(ValueError,'container differs'):self.inspect()

    def test_wrong_signer_preserves_primary_and_never_merges(self):
        self.make_bundle();self.authorize_fixture();d=self.root/'download';d.mkdir();(d/'reddit.apk').write_bytes(b'keep')
        with patch.object(fb,'run_checked',side_effect=self.runner),patch.object(fb,'apk_metadata',side_effect=self.metadata),patch.object(fb,'apk_certificate',return_value='2'*64):
            with self.assertRaisesRegex(ValueError,'signer differs'):fb.execute(self.root,self.ident,self.a['version_name'],self.env)
        self.assertNotIn('merge',self.events)
        self.assertEqual((d/'reddit.apk').read_bytes(),b'keep')

    def test_each_original_package_version_code_sdk_gate(self):
        for field,value in [('package','wrong.package'),('version_name','2026.39.0'),('version_code','9'),
                            ('min_sdk',30),('min_sdk',True),('min_sdk',0)]:
            bad=dict(self.meta,**{field:value})
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                self.inspect(metadata=lambda *args,**kwargs:bad)

    def test_arm32_only_and_fake_arm64_elf_refused(self):
        for abi,elf in [('armeabi-v7a',True),('x86',True),('arm64-v8a',False)]:
            self.raw.write_bytes(apk_bytes(abi,elf));self.a['container']=fb.file_record(self.raw)
            with self.subTest(abi=abi),self.assertRaises(ValueError):self.inspect()
        self.raw.write_bytes(apk_bytes('arm64-v8a'));self.a['container']=fb.file_record(self.raw)
        self.a['variant']['abis']=['arm64-v8a']
        self.assertEqual(self.inspect()['abis'],['arm64-v8a'])

    def test_archive_traversal_duplicate_symlink_missing_manifest_nested_apk_refuse(self):
        for kind in ('traversal','duplicate','symlink','missing','nested'):
            with zipfile.ZipFile(self.raw,'w') as z:
                z.writestr('padding',b'x'*11000)
                if kind!='missing':z.writestr('AndroidManifest.xml',b'fixture')
                if kind=='traversal':z.writestr('../escape',b'x')
                if kind=='duplicate':
                    import warnings
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore');z.writestr('padding',b'y'*11000)
                if kind=='symlink':
                    item=zipfile.ZipInfo('link');item.external_attr=0o120777<<16;z.writestr(item,'target')
                if kind=='nested':z.writestr('hidden.apk',b'not an apk')
            self.a['container']=fb.file_record(self.raw)
            with self.subTest(kind=kind),self.assertRaises(ValueError):self.inspect()
        self.assertFalse((self.root.parent/'escape').exists())

    def test_aggregate_split_expansion_is_bounded(self):
        self.make_bundle()
        # Outer raw bound must remain large enough; lower aggregate only with a tiny zip_inspect stub.
        with patch.object(fb,'MAX_EXPANDED',1000000),patch.object(fb.github_bundle,'zip_inspect'):
            with self.assertRaisesRegex(ValueError,'aggregate split expansion'):self.inspect()

    def test_symlink_output_preserved_and_refused(self):
        self.authorize_fixture();d=self.root/'download';d.mkdir()
        keep=self.root/'keep';keep.write_bytes(b'keep');(d/'reddit.apk').symlink_to(keep)
        with self.assertRaisesRegex(ValueError,'unsafe existing output'):self.execute()
        self.assertEqual(keep.read_bytes(),b'keep');self.assertTrue((d/'reddit.apk').is_symlink())

    def test_merged_identity_failure_never_installs(self):
        self.make_bundle();self.authorize_fixture()
        def reader(root,path,env,**kwargs):
            result=self.metadata(root,path,env,**kwargs)
            if path.name=='checked-source.apk':result['version_name']='2026.39.0'
            return result
        with patch.object(fb,'run_checked',side_effect=self.runner),patch.object(fb,'apk_metadata',side_effect=reader),patch.object(fb,'apk_certificate',side_effect=self.certificate):
            with self.assertRaisesRegex(ValueError,'merged package/version/SDK'):fb.execute(self.root,self.ident,self.a['version_name'],self.env)
        self.assertFalse((self.root/'download').exists())

    def test_primary_success_all_14_unchanged_and_failure_reaches_same_gate(self):
        utils=self.root/'src/build/utils.sh'
        utils.write_text('get_apk(){ echo PRIMARY_MIRROR; return 0; }\nget_apkpure(){ echo PRIMARY_PURE; return 0; }\n')
        for ident in fb.policy(self.root)['targets']:
            p=subprocess.run(['bash','src/build/source_download.sh',ident,'1.0'],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr);self.assertNotIn('FALLBACK',p.stdout+p.stderr)
        utils.write_text('get_apk(){ return 1; }\nget_apkpure(){ return 1; }\n')
        p=subprocess.run(['bash','src/build/source_download.sh','reddit','2026.38.0'],cwd=self.root,capture_output=True,text=True)
        self.assertEqual(p.returncode,1);self.assertIn('SOURCE_FALLBACK_REFUSED',p.stderr)
        build=(self.root/'src/build/build.sh').read_text()
        self.assertIn('python3 src/build/source_fallback.py "$ID" "$RVER"',build)
        self.assertLess(build.index('source_inputs.py install'),build.index('source_fallback.py'))

    def test_alternate_shell_enforces_exact_version_and_raw_only_both_stores(self):
        utils=self.root/'src/build/utils.sh'
        utils.write_text('get_apk(){ echo "$version|$lock_version|$near_version|$PF_APK_RAW_ONLY"; }\nget_apkpure(){ echo "$version|$lock_version|$near_version|$PF_APK_RAW_ONLY"; }\n')
        for store in ('apkmirror','apkpure'):
            variant=dict(self.a['variant'])
            if store=='apkpure':variant['apkmirror_url']=None
            (self.root/'qualified-variant.json').write_text(json.dumps({
                'source':store,'package':self.t['package'],'version':'2026.38.0',
                'mapping':self.a['mapping'],'ceiling':29,'variant':variant}))
            p=subprocess.run(['bash','src/build/source_alternate.sh','reddit','2026.38.0',store],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stdout.strip(),'2026.38.0|1|0|1')
        utils.write_text('get_apk(){ version=2026.37.0; }\nget_apkpure(){ version=2026.39.0; }\n')
        for store in ('apkmirror','apkpure'):
            p=subprocess.run(['bash','src/build/source_alternate.sh','reddit','2026.38.0',store],cwd=self.root,capture_output=True)
            self.assertEqual(p.returncode,1)

    def test_raw_hook_precedes_both_mergers_and_primary_forces_normal_mode(self):
        text=(ROOT/'src/build/utils.sh').read_text()
        mirror=text[text.index('get_apk() {'):text.index('get_apkpure() {')]
        pure=text[text.index('get_apkpure() {'):text.index('get_apk_chplay() {')]
        for body in (mirror,pure):
            raw_hook='if [[ "${PF_APK_RAW_ONLY:-0}" == "1" ]]; then return 0; fi'
            self.assertEqual(body.count(raw_hook),1)
            self.assertLess(body.index(raw_hook),body.index('java -jar $APKEditor m'))
            self.assertGreater(body.index(raw_hook),body.index('wget -q -O'))
        for name in ('build.sh','source_download.sh'):
            self.assertIn('PF_APK_RAW_ONLY=0',(ROOT/'src/build'/name).read_text())

    def test_qualification_evidence_changes_recipe(self):
        self.authorize_fixture()
        before=input_recipe.create(self.root,'reddit','adobo',{})
        self.assertIn(self.a['evidence'],[c['path'] for c in before['components']])
        path=self.root/self.a['evidence'];doc=json.loads(path.read_text());doc['publisher_anchor_reviewed']=False;path.write_text(json.dumps(doc))
        after=input_recipe.create(self.root,'reddit','adobo',{})
        self.assertNotEqual(before['sha256'],after['sha256'])

    def test_cli_reports_coverage_and_generic_refusal_without_private_environment(self):
        p=subprocess.run([sys.executable,'src/build/source_fallback.py','coverage'],cwd=self.root,capture_output=True,text=True,env=self.env)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(len(json.loads(p.stdout)),14)
        p=subprocess.run([sys.executable,'src/build/source_fallback.py','reddit','2026.38.0'],cwd=self.root,capture_output=True,text=True,env=self.env)
        self.assertEqual(p.returncode,1);self.assertNotIn('SECRET',p.stdout+p.stderr)


if __name__=='__main__':unittest.main()
