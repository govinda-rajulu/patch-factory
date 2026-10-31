import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import zipfile
from unittest.mock import patch
from target_counts import ENABLED  # W4: counts follow src/targets.json

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/build'))
import resolved_contracts as fixtures
import resolved_inputs as resolved
import source_inputs as source
import execution_inputs as execution
import shadow_inputs as shadow
import input_recipe


class SourceContracts(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ResolvedContracts()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.r, self.env = self.f.r, dict(self.f.env)
        self.env.pop('JAVA_TOOL_OPTIONS', None)
        self.env.pop('COE', None)
        self.env['KEYSTORE_ALIAS'] = 'fixture-alias'
        self.ident = 'keymapper'
        self.meta = dict(package='io.github.sds100.keymapper', version_name='4.2.1', version_code='42', min_sdk=29)
        self.fetches = 0
        # W15c: prepare checks the publisher pin on the original download; the rule itself is
        # covered by publisher_cert_contracts, so these fixtures answer like a pinned match.
        self.publisher_calls = []
        self.publisher = lambda root, ident, env: (self.publisher_calls.append(ident), 0)[1]

    def downloader(self, args, **kwargs):
        self.assertEqual(args, ['bash', 'src/build/source_download.sh', self.ident, '4.2.1'])
        self.assertNotIn('KEYSTORE_PASS', kwargs['env'])
        self.assertNotIn('JAVA_TOOL_OPTIONS', kwargs['env'])
        self.fetches += 1
        p = self.r / 'download' / (shadow.target(self.r, self.ident)['apk_name'] + '.apk')
        p.parent.mkdir()
        with zipfile.ZipFile(p, 'w') as z:
            z.writestr('AndroidManifest.xml', b'manifest fixture')
            z.writestr('classes.dex', b'x' * 1000100)
        return subprocess.CompletedProcess(args, 0)

    def prepare(self):
        self.dep = self.f.prepare(self.ident)
        return source.prepare(self.r, self.ident, self.env, self.downloader, lambda *a: self.meta, publisher=self.publisher)

    def consumer(self):
        self.doc = self.prepare()
        (self.r / 'download').rename(self.r / 'preserved-producer-download')
        return source.install(self.r, self.ident, self.env)

    def capture(self):
        return {'target': self.ident, 'patcher_input_apk': resolved.regular(self.r, 'download/key-mapper.apk')}

    def reseal(self, doc):
        (self.r / source.LOCK).write_bytes(input_recipe.canonical(shadow.seal({k:v for k,v in doc.items() if k != 'sha256'})))

    def test_prepare_checks_the_publisher_on_the_original_download(self):
        # W15c (20 Oct 2026): Check new patch run 39483060645 read the pin from the merged copy.
        self.dep = self.f.prepare(self.ident)
        with self.assertRaisesRegex(ValueError, 'publisher certificate refused'):
            source.prepare(self.r, self.ident, self.env, self.downloader, lambda *a: self.meta,
                           publisher=lambda root, ident, env: 1)
        self.assertFalse((self.r / 'source-inputs').exists())
        self.assertEqual(self.prepare_again(), [self.ident])

    def prepare_again(self):
        import shutil
        shutil.rmtree(self.r / 'download')
        source.prepare(self.r, self.ident, self.env, self.downloader, lambda *a: self.meta, publisher=self.publisher)
        return self.publisher_calls

    def test_exact_prepare_verify_install_consume_without_second_download(self):
        doc = self.consumer()
        self.assertEqual(source.verify(self.r, self.ident, self.env), doc)
        self.assertEqual(source.consumed(self.r, self.ident, self.capture(), self.env)['status'], 'MATCH')
        self.assertEqual(self.fetches, 1)
        self.assertEqual((self.r/'download/key-mapper.apk').read_bytes(), (self.r/'preserved-producer-download/key-mapper.apk').read_bytes())

    def test_mutated_packet_refused_before_install(self):
        self.prepare()
        (self.r/'download').rename(self.r/'preserved-download')
        p = self.r/'source-inputs/source.apk'
        b = p.read_bytes(); p.write_bytes(b[:-1] + bytes([b[-1]^1]))
        with self.assertRaises(ValueError): source.install(self.r,self.ident,self.env)
        self.assertFalse((self.r/'download').exists())

    def test_mutated_actual_input_refused_at_consumption(self):
        self.consumer()
        p=self.r/'download/key-mapper.apk'; b=p.read_bytes();p.write_bytes(b[:-1]+bytes([b[-1]^1]))
        with self.assertRaises(ValueError):source.consumed(self.r,self.ident,self.capture(),self.env)

    def test_missing_extra_symlink_and_existing_destination_refuse(self):
        doc=self.consumer()
        with self.assertRaises(ValueError):source.install(self.r,self.ident,self.env)
        extra=self.r/'source-inputs/unlisted';extra.write_bytes(b'preserve')
        with self.assertRaises(ValueError):source.verify(self.r,self.ident,self.env)
        extra.rename(self.r/'preserved-unlisted')
        apk=self.r/'source-inputs/source.apk';apk.rename(self.r/'preserved-packet.apk');apk.symlink_to(self.r/'preserved-packet.apk')
        with self.assertRaises(ValueError):source.verify(self.r,self.ident,self.env)
        self.assertEqual((self.r/'preserved-unlisted').read_bytes(),b'preserve')

    def test_resealed_wrong_identity_metadata_and_coverage_refuse(self):
        doc=self.prepare()
        for mutate in (lambda d:d.update(target='reddit'), lambda d:d.update(dependency_lock_sha256='f'*64),
                       lambda d:d['run'].update(GITHUB_RUN_ATTEMPT='3'), lambda d:d['metadata'].update(package='wrong.package'),
                       lambda d:d['metadata'].update(min_sdk=True), lambda d:d['metadata'].update(min_sdk=30),
                       lambda d:d['metadata'].update(version_name='1\nEVIL'), lambda d:d.update(limits=[])):
            bad=copy.deepcopy(doc);mutate(bad);self.reseal(bad)
            with self.assertRaises(ValueError):source.verify(self.r,self.ident,self.env)
        self.reseal(doc)
        for key,value in [('GITHUB_RUN_ID','9'),('GITHUB_RUN_ATTEMPT','3'),('GITHUB_REPOSITORY','wrong/repo')]:
            with self.assertRaises(ValueError):source.verify(self.r,self.ident,dict(self.env,**{key:value}))

    def test_preparation_failure_has_no_packet_and_preserves_existing_files(self):
        self.f.prepare()
        p=self.r/'download';p.mkdir();(p/'keep').write_bytes(b'keep')
        with self.assertRaises(ValueError):source.prepare(self.r,self.ident,self.env,self.downloader,lambda *a:self.meta,publisher=self.publisher)
        self.assertEqual(self.fetches,0);self.assertFalse((self.r/'source-inputs').exists())
        self.assertEqual((p/'keep').read_bytes(),b'keep')

    def test_wrong_manifest_fails_before_exposing_packet(self):
        self.meta['package']='wrong.package'
        with self.assertRaises(ValueError):self.prepare()
        self.assertFalse((self.r/'source-inputs').exists())

    def pin(self, code):
        p=self.r/'src/targets.json';ts=json.loads(p.read_text());next(t for t in ts if t['id']==self.ident)['version_code']=code
        p.write_text(json.dumps(ts))

    def test_pinned_version_code_other_file_refused(self):
        # W16w: a store's other file of the same version name is never sealed as the source.
        self.pin('43')
        with self.assertRaisesRegex(ValueError,'not the pinned 43'):self.prepare()
        self.assertFalse((self.r/'source-inputs').exists())

    def test_pinned_version_code_match_prepares(self):
        self.pin('42')
        self.assertTrue(self.prepare())

    def test_note_only_does_not_drift_source_packet(self):
        doc=self.prepare()
        p=self.r/'src/targets.json';ts=json.loads(p.read_text());next(t for t in ts if t['id']==self.ident)['note']='irrelevant'
        p.write_text(json.dumps(ts))
        self.assertEqual(source.verify(self.r,self.ident,self.env),doc)

    def test_actual_cli_verify_install_and_consumption_boundary(self):
        self.prepare();(self.r/'download').rename(self.r/'producer-download')
        for mode in ['verify','install']:
            result=subprocess.run([sys.executable,'src/build/source_inputs.py',mode,self.ident],cwd=self.r,env=self.env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.strip(),'4.2.1')
        resolved.install(self.r,self.ident,self.env)
        (self.r/'extra').mkdir()
        subprocess.run(['bash','src/build/selections.sh',self.ident,'legendsciber'],cwd=self.r,check=True,capture_output=True)
        fakebin=self.r/'fakebin';fakebin.mkdir()
        java=fakebin/'java';java.write_text('#!/bin/bash\ntouch PATCHER_REACHED\nexit 77\n');java.chmod(0o755)
        env={k:v for k,v in self.env.items() if not k.startswith('KEYSTORE')}
        env.update(PATH=str(fakebin)+':'+os.environ['PATH'],PF_SOURCE_READY='true',
                   PF_EXECUTION_OBSERVATION='true',PF_UNSIGNED='true')
        args=[sys.executable,'src/build/patch_target.py',self.ident,'legendsciber']
        good=subprocess.run(args,cwd=self.r,env=env,capture_output=True,text=True)
        self.assertEqual(good.returncode,77,good.stderr)
        observed = json.loads((self.r/execution.PATH).read_text())
        self.assertEqual(observed['status'], 'UNKNOWN')  # Fake Java has no runtime modules.
        (self.r/'PATCHER_REACHED').rename(self.r/'prior-good-marker')
        p=self.r/'download/key-mapper.apk';p.write_bytes(p.read_bytes()+b'drift')
        bad=subprocess.run(args,cwd=self.r,env=env,capture_output=True,text=True)
        self.assertNotEqual(bad.returncode,0);self.assertFalse((self.r/'PATCHER_REACHED').exists())
        self.assertNotIn('DO_NOT_INHERIT',good.stdout+good.stderr+bad.stdout+bad.stderr)

    def test_real_build_shell_uses_packet_instead_of_store_fetch(self):
        (self.r/'src/build/utils.sh').write_text('mkdir -p release download\ngreen_log(){ :; }\nred_log(){ echo "$1"; }\nyellow_log(){ :; }\nget_patches_key(){ :; }\nget_apk(){ echo SECOND_FETCH; return 91; }\nget_apkpure(){ echo SECOND_FETCH; return 91; }\n')
        self.prepare();(self.r/'download').rename(self.r/'producer-download')
        fakebin=self.r/'fakebin';fakebin.mkdir()
        py=fakebin/'python3';py.write_text('#!/bin/bash\n# W15b: a pinned package with an unreadable certificate now stops; the fixture\n# supplies the reviewed publisher-certificate check (publisher_cert_contracts covers the rule).\ncase "$1" in\nsrc/build/publisher_cert.py) echo "PUBLISHER_CERT fake pinned OK"; exit 0;;\nesac\ncase "$1 $2" in\n"src/build/artifact_identity.py capture-inputs") echo CAPTURE_BOUNDARY; exit 77;;\nesac\nexec '+sys.executable+' "$@"\n');py.chmod(0o755)
        aapt=fakebin/'aapt2';aapt.write_text("#!/bin/bash\nif [ \"$2\" = packagename ]; then echo io.github.sds100.keymapper; else echo \"sdkVersion:'29'\"; fi\n");aapt.chmod(0o755)
        env=dict(self.env,PATH=str(fakebin)+':'+os.environ['PATH'],ANDROID_HOME=str(fakebin),PF_RESOLVED_READY='true',PF_SOURCE_READY='true')
        result=subprocess.run(['bash','src/build/build.sh',self.ident],cwd=self.r,env=env,capture_output=True,text=True,timeout=30)
        self.assertIn('CAPTURE_BOUNDARY',result.stdout,result.stdout+result.stderr)
        self.assertNotIn('SECOND_FETCH',result.stdout+result.stderr)
        self.assertEqual(result.returncode,1)

    def test_download_adapter_preserves_apkpure_apkmirror_and_any_version(self):
        (self.r/'src/build/utils.sh').write_text('get_apk(){ printf "mirror|%s|%s|%s|%s|%s|%s\\n" "$1" "$2" "$3" "$version" "$lock_version" "$near_version"; }\nget_apkpure(){ printf "pure|%s|%s|%s|%s|%s\\n" "$1" "$2" "$3" "$version" "$lock_version"; }\n')
        targets=[t for t in json.loads((self.r/'src/targets.json').read_text()) if t.get('enabled') is True]  # W16l: a disabled app (CCleaner) is never downloaded
        self.assertEqual(len(targets),ENABLED)
        for target in targets:
            result=subprocess.run(['bash','src/build/source_download.sh',target['id'],'4.2.1'],cwd=self.r,env=source.clean_env(self.env),capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            parts=result.stdout.strip().split('|')
            self.assertEqual(parts[:4],['pure' if target.get('source')=='apkpure' else 'mirror',target['package'],target['apk_name'],target.get('apk_type','apk')])
            self.assertEqual(parts[4:6],['','1'] if target.get('any_version') else ['4.2.1',''])
            if parts[0]=='mirror':self.assertEqual(parts[-1],'1')

    def test_w16d_empty_provider_version_downloads_latest(self):
        # Amazon Music (24 Oct): the provider lists no versions, the Plan version is "", and
        # ${2:?} refused it in 0 s, so the shadow step never prepared an APK and Qualify went red.
        (self.r/'src/build/utils.sh').write_text('get_apk(){ printf "mirror|%s|%s|%s\\n" "$1" "$version" "$lock_version"; }\nget_apkpure(){ printf "pure|%s|%s\\n" "$1" "$version"; }\n')
        target=json.loads((self.r/'src/targets.json').read_text())[0]
        r=subprocess.run(['bash','src/build/source_download.sh',target['id'],''],cwd=self.r,env=source.clean_env(self.env),capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertIn('|'+target['package']+'||',r.stdout)
        r=subprocess.run(['bash','src/build/source_download.sh',target['id']],cwd=self.r,env=source.clean_env(self.env),capture_output=True,text=True)
        self.assertNotEqual(r.returncode,0)

    def test_failed_store_tries_the_other_mapped_store_before_the_qualified_fallback(self):
        (self.r/'src/build/utils.sh').write_text('get_apk(){ if [ -n "${MIRROR_FAIL:-}" ]; then return 3; fi; printf "mirror|%s|%s|%s|%s\\n" "$1" "$version" "$4" "$5"; }\nget_apkpure(){ if [ -n "${PURE_FAIL:-}" ]; then return 4; fi; printf "pure|%s|%s\\n" "$1" "$version"; }\n')
        stub=self.r/'src/build/source_fallback.py';stub.write_text('import sys\nprint("QUALIFIED_FALLBACK")\nsys.exit(9)\n')
        env=source.clean_env(self.env)
        r=subprocess.run(['bash','src/build/source_download.sh','reddit','2026.40.0'],cwd=self.r,env=dict(env,PURE_FAIL='1'),capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertIn('mirror|com.reddit.frontpage|2026.40.0|arm64-v8a|480-640dpi',r.stdout)
        self.assertIn('STORE_CHAIN used apkmirror',r.stdout);self.assertNotIn('QUALIFIED_FALLBACK',r.stdout)
        r=subprocess.run(['bash','src/build/source_download.sh','telegram','12.10.1'],cwd=self.r,env=dict(env,MIRROR_FAIL='1'),capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertIn('pure|org.telegram.messenger|12.10.1',r.stdout)
        r=subprocess.run(['bash','src/build/source_download.sh','reddit','2026.40.0'],cwd=self.r,env=dict(env,PURE_FAIL='1',MIRROR_FAIL='1'),capture_output=True,text=True)
        self.assertEqual(r.returncode,9);self.assertIn('QUALIFIED_FALLBACK',r.stdout)
        r=subprocess.run(['bash','src/build/source_download.sh','youtube','21.40.161'],cwd=self.r,env=dict(env,MIRROR_FAIL='1'),capture_output=True,text=True)
        self.assertEqual(r.returncode,9);self.assertIn('no apkpure mapping',r.stdout);self.assertNotIn('pure|',r.stdout)
        build=(self.r/'src/build/build.sh').read_text()
        self.assertLess(build.index('try_other_store "$PKG"'),build.index('python3 src/build/source_fallback.py "$ID" "$RVER"'))
        self.assertIn('source ./src/build/store_chain.sh',build)

    def test_qualified_source_subset_same_changed_legacy_wrong_attempt_and_missing(self):
        self.prepare()
        snap = source.snapshot(self.r, self.ident, self.env)
        receipt = dict(target=self.ident, source_commit=self.env['GITHUB_SHA'],
                       run_id=self.env['GITHUB_RUN_ID'], attempt=self.env['GITHUB_RUN_ATTEMPT'],
                       repository=self.env['GITHUB_REPOSITORY'], tag='fixture-tag',
                       prepared_source=snap)
        with patch.object(shadow, 'latest_baseline', return_value=(receipt, 'VERIFIED_DURABLE_ACTIONS_RECORD')):
            result = source.observe(self.r, self.ident, self.env, object())
            self.assertEqual(result['decision']['state'], 'MATCHED_SOURCE_SUBSET')
            changed = copy.deepcopy(snap); changed['apk']['sha256'] = 'f'*64
            receipt['prepared_source'] = shadow.seal({k:v for k,v in changed.items() if k != 'sha256'})
            self.assertEqual(source.observe(self.r,self.ident,self.env,object())['decision']['state'], 'CHANGED_SOURCE_SUBSET')
            receipt['attempt'] = '3'
            self.assertEqual(source.observe(self.r,self.ident,self.env,object())['decision']['state'], 'UNKNOWN')
            receipt.pop('prepared_source')
            self.assertEqual(source.observe(self.r,self.ident,self.env,object())['decision']['reason'], 'LATEST_PUBLICATION_HAS_NO_SOURCE_SUBSET')
        with patch.object(shadow,'latest_baseline',return_value=(None,'NO_VERIFIED_BASELINE')):
            self.assertEqual(source.observe(self.r,self.ident,self.env,object())['decision']['state'],'UNKNOWN')
        (self.r/'source-inputs').rename(self.r/'preserved-source-inputs')
        self.assertEqual(source.observe(self.r,self.ident,self.env,object())['decision']['state'],'UNKNOWN')

    def test_real_source_prepare_cli_runs_adapter_and_metadata_reader(self):
        stub = ('mkdir release download\n'
                'get_apk(){ cp fixture.apk \"download/$2.apk\"; }\n'
                'get_apkpure(){ cp fixture.apk \"download/$2.apk\"; }\n')
        (self.r/'src/build/utils.sh').write_text(stub)
        with zipfile.ZipFile(self.r/'fixture.apk','w') as z:
            z.writestr('AndroidManifest.xml',b'fixture')
            z.writestr('classes.dex',b'd'*1000100)
        tools=self.r/'android/build-tools/35';tools.mkdir(parents=True)
        reader=tools/'aapt2'
        reader.write_text("#!/bin/bash\nprintf \"package: name='io.github.sds100.keymapper' versionCode='42' versionName='4.2.1'\\nsdkVersion:'29'\\n\"\n")
        reader.chmod(0o755)
        # W15c: prepare reads the publisher pin from the original download (the real check).
        pin=json.loads((Path(__file__).resolve().parents[1]/'src/build/PUBLISHERS.json').read_text())['io.github.sds100.keymapper'][0]
        signer=tools/'apksigner'
        signer.write_text('#!/bin/bash\necho "Signer #1 certificate SHA-256 digest: %s"\n' % pin)
        signer.chmod(0o755)
        self.f.prepare()
        env=dict(self.env,ANDROID_HOME=str(self.r/'android'))
        result=subprocess.run([sys.executable,'src/build/source_inputs.py','prepare',self.ident],
                              cwd=self.r,env=env,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('PUBLISHER_CERT io.github.sds100.keymapper %s pinned OK' % pin, result.stdout)
        self.assertEqual(source.verify(self.r,self.ident,self.env)['metadata'],self.meta)
        self.assertTrue((self.r/'source-observation/keymapper.json').exists())

    def test_prepare_failure_names_its_own_reason_never_fetcher_text(self):
        # 28 Sep 2026: Edge failed every shadow preparation and printed only the fixed warning.
        stub = 'get_apk(){ echo "<html>SECRET upstream page</html>"; return 7; }\nget_apkpure(){ return 7; }\n'
        (self.r/'src/build/utils.sh').write_text(stub)
        (self.r/'src/build/source_fallback.py').write_text('import sys\nprint("fallback SECRET text")\nsys.exit(5)\n')
        self.f.prepare()
        result=subprocess.run([sys.executable,'src/build/source_inputs.py','prepare',self.ident],
                              cwd=self.r,env=self.env,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,1)
        self.assertIn('source APK preparation unavailable or invalid',result.stderr)
        self.assertRegex(result.stderr,r'source inputs failure: existing store fetcher refused [(]exit 5 after [0-9]+s, source apkpure, type bundle[)]')
        self.assertNotIn('SECRET',result.stderr+result.stdout)
        self.assertEqual(json.loads((self.r/'source-observation/keymapper.json').read_text())['reason'],'SOURCE_PREPARATION_FAILED')

    def test_public_reason_and_observed_line_are_sanitized(self):
        self.assertEqual(source.public_reason(ValueError('source inputs: invalid APK identity/SDK')),'invalid APK identity/SDK')
        self.assertEqual(source.public_reason(ValueError('resolved inputs: dependency packet missing')),'resolved inputs: dependency packet missing')
        self.assertEqual(source.public_reason(ValueError('invalid APK identity/SDK')),'ValueError')
        self.assertEqual(source.public_reason(ValueError('Expecting value: line 1 <html>')),'ValueError')
        self.assertEqual(source.public_reason(OSError('/home/runner/secret path')),'OSError')
        self.assertEqual(source.public_reason(subprocess.TimeoutExpired(['x'],1200)),'TimeoutExpired')
        line=source.observed_line(dict(package='com.microsoft.emmx',version_name='152.0.4191.65',version_code='x y',min_sdk=30),{'bytes':280000000})
        self.assertEqual(line,'source apk observed: package=com.microsoft.emmx version=152.0.4191.65 code=? min_sdk=30 bytes=280000000')

    def test_min_sdk_over_ceiling_is_reported_with_the_observed_value(self):
        self.meta['min_sdk']=30
        with patch.object(source, '_next_version', side_effect=ValueError(
                'source inputs: sdk ceiling 29 exceeded and no lower version to try (status 1)')):
            with self.assertRaises(ValueError) as caught, patch('sys.stderr') as err:
                self.prepare()
        self.assertEqual(source.public_reason(caught.exception),
                         'sdk ceiling 29 exceeded and no lower version to try (status 1)')
        self.assertIn('min_sdk=30',''.join(c.args[0] for c in err.write.call_args_list))
        self.assertFalse((self.r/'source-inputs').exists())

    def test_min_sdk_over_ceiling_steps_down_and_rechecks_the_lower_apk(self):
        self.dep = self.f.prepare(self.ident)
        versions = []
        metadata = {'4.2.1': dict(self.meta, min_sdk=30),
                    '4.2.0': dict(self.meta, version_name='4.2.0', min_sdk=29)}

        def downloader(args, **kwargs):
            version = args[-1]
            versions.append(version)
            p = self.r / 'download' / (shadow.target(self.r, self.ident)['apk_name'] + '.apk')
            p.parent.mkdir(exist_ok=True)
            with zipfile.ZipFile(p, 'w') as z:
                z.writestr('AndroidManifest.xml', b'manifest fixture')
                z.writestr('classes.dex', b'x' * 1000100)
            return subprocess.CompletedProcess(args, 0)

        def read_metadata(root, path, env):
            return metadata[versions[-1]]

        with patch.object(source, '_next_version', return_value=('4.2.0', 'provider')) as step:
            doc = source.prepare(self.r, self.ident, self.env, downloader, read_metadata,
                                 publisher=self.publisher)
        self.assertEqual(versions, ['4.2.1', '4.2.0'])
        step.assert_called_once_with(self.r, self.dep, shadow.target(self.r, self.ident),
                                     source.clean_env(self.env), '4.2.1', 0)
        self.assertEqual(doc['metadata']['version_name'], '4.2.0')
        self.assertEqual(self.publisher_calls, [self.ident, self.ident])

    def test_workflow_selection_publication_and_qualification_reader_preserved(self):
        ci=(self.r/'.github/workflows/ci.yml').read_text();manual=(self.r/'.github/workflows/manual-patch.yml').read_text()
        self.assertIn('matrix: ${{ fromJson(needs.plan.outputs.matrix) }}',ci)
        self.assertIn('cron: "23 12 * * *"',ci)
        block=ci.split('\n  resolve:\n')[1].split('\n  dependency_report:\n')[0]
        self.assertNotIn('secrets.',block);self.assertIn('contents: read',block)
        self.assertLess(manual.index('Verify source APK before signing secrets'),manual.index('Decode keystore'))
        self.assertIn("inputs.publish && github.ref == 'refs/heads/main'",manual)
        # Source rows must never pollute the existing strict dependency report.
        self.assertIn('path: source-observation/',ci)
        self.assertIn('name: source-observation-${{ matrix.target }}',ci)
        self.assertNotIn('resolved-observation/',Path(source.__file__).read_text())


class ExecutionContracts(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ResolvedContracts();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.r,self.env=self.f.r,dict(self.f.env);self.env.pop('JAVA_TOOL_OPTIONS',None);self.env.pop('COE',None)
        self.f.prepare();resolved.install(self.r,'keymapper',self.env)
        (self.r/'extra').mkdir()
        subprocess.run(['bash','src/build/selections.sh','keymapper','legendsciber'],cwd=self.r,check=True,capture_output=True)

    def test_actual_public_command_has_no_signing_secrets_or_absolute_checkout(self):
        doc=execution.public_command(self.r,'keymapper','legendsciber',self.env)
        text=json.dumps(doc)
        for value in ['DO_NOT_INHERIT','SECRET','OMITTED','--keystore',str(self.r)]:self.assertNotIn(value,text)
        self.assertIn('Premium',doc['argv']);self.assertEqual(doc['approval'],'not evaluated')
        changed=execution.public_command(self.r,'keymapper','legendsciber',dict(self.env,COE='true'))
        self.assertNotEqual(doc,changed)
        note=execution.public_command(self.r,'keymapper','legendsciber',dict(self.env,KEYSTORE_PASS='changed secret'))
        self.assertEqual(doc,note)

    def test_byte_mode_positive_and_timestamp_negative_controls(self):
        p=self.r/'runtime';p.write_bytes(b'one');before=execution.file_identity(p)
        os.utime(p,(1,1));self.assertEqual(before,execution.file_identity(p))
        p.write_bytes(b'two');self.assertNotEqual(before,execution.file_identity(p))
        p.write_bytes(b'one');p.chmod(0o755);self.assertNotEqual(before,execution.file_identity(p))

    def test_observed_capture_rechecks_runtime_and_invocation(self):
        with patch.object(execution,'runtime',return_value={'fixture':'one'}):
            doc=execution.capture(self.r,'keymapper','legendsciber',self.env)
            self.assertEqual(execution.verify(self.r,'keymapper','legendsciber',self.env),doc)
        with patch.object(execution,'runtime',return_value={'fixture':'two'}):
            with self.assertRaises(ValueError):execution.verify(self.r,'keymapper','legendsciber',self.env)
        with patch.object(execution,'runtime',return_value={'fixture':'one'}):
            with self.assertRaises(ValueError):execution.verify(self.r,'keymapper','legendsciber',dict(self.env,COE='true'))
        with self.assertRaises(ValueError):execution.capture(self.r,'keymapper','legendsciber',self.env)

    def test_unmodeled_runtime_unknown_never_exposes_values(self):
        env=dict(self.env,JAVA_TOOL_OPTIONS='super private string')
        doc=execution.capture(self.r,'keymapper','legendsciber',env)
        self.assertEqual(doc['status'],'UNKNOWN');self.assertNotIn('super private string',json.dumps(doc))
        self.assertIn('incomplete',' '.join(doc['limits']))

    def test_runtime_reaches_binary_and_java_module_consumers(self):
        home=self.r/'jdk';(home/'bin').mkdir(parents=True)
        java=home/'bin/java';java.write_bytes(b'executable')
        for relative in ['release','lib/modules','lib/server/libjvm.so','conf/security/java.security']:
            p=home/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(relative.encode())
        with patch.object(execution.shutil,'which',return_value=str(java)):
            before=execution.runtime(self.env)
            self.assertEqual(len(before['files']),9)
            (home/'lib/modules').write_bytes(b'changed same runtime version')
            self.assertNotEqual(before,execution.runtime(self.env))
            (home/'lib/modules').unlink()
            with self.assertRaises(OSError):execution.runtime(self.env)

class ConnectedObservationContracts(unittest.TestCase):
    def setUp(self):
        import shadow_contracts
        self.s = shadow_contracts.ShadowContracts()
        self.s.setUp()
        self.addCleanup(self.s.doCleanups)

    def test_actual_consumed_key_contains_observed_runtime_and_unknown_on_drift(self):
        s = self.s
        captured = fixtures.capture_shadow_inputs(s)
        env = dict(s.env, PF_EXECUTION_OBSERVATION='true')
        with patch.object(execution, 'runtime', return_value={'fixture': 'before'}):
            execution.capture(s.r, 'keymapper', 'lain', env)
            doc = shadow.realized(s.r, captured, env)
            self.assertEqual(doc['material']['execution']['runtime'], {'fixture': 'before'})
            baseline = {'target': 'keymapper', 'effective_sha256': doc['effective_sha256']}
            self.assertEqual(shadow.compare(doc, baseline, 'VERIFIED')['state'], 'UNCHANGED')
        with patch.object(execution, 'runtime', return_value={'fixture': 'after'}):
            changed = shadow.realized(s.r, captured, env)
            self.assertEqual(shadow.compare(changed, baseline, 'VERIFIED')['state'], 'UNKNOWN')
        missing_source = shadow.realized(s.r, captured, dict(s.env, PF_SOURCE_REQUESTED='true'))
        self.assertEqual(shadow.compare(missing_source, baseline, 'VERIFIED')['state'], 'UNKNOWN')

    def test_missing_source_or_runtime_cannot_publish_a_new_receipt(self):
        s = self.s
        root = s.r
        captured = {"target": "keymapper"}
        unsigned_sha = "a" * 64
        evidence = root / "build-evidence" / "keymapper.json"
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text(json.dumps({"inputs": captured, "signing_split": True,
                                        "unsigned_output": {"sha256": unsigned_sha}}))
        for missing in ("source", "runtime"):
            with self.subTest(missing=missing):
                material = {"execution": {"status": "UNKNOWN"} if missing == "runtime" else {"status": "KNOWN"}}
                consumed = shadow.seal({
                    "domain": shadow.DOMAIN, "schema": 1, "kind": "consumed", "target": "keymapper",
                    "binding": "NO_PLAN", "material": material, "effective_sha256": shadow.sha(material),
                    "resolution": {"status": "NOT_REQUESTED"},
                    "source_resolution": {"status": "UNAVAILABLE" if missing == "source" else "NOT_REQUESTED"}})
                draft = shadow.seal({"domain": shadow.DRAFT_DOMAIN, "schema": 1, "target": "keymapper",
                                     "inputs_sha256": shadow.sha(captured), "unsigned_sha256": unsigned_sha,
                                     "consumed": consumed})
                draft_path = root / "shadow-evidence" / "keymapper-receipt-draft.json"
                draft_path.parent.mkdir(parents=True, exist_ok=True)
                draft_path.write_text(json.dumps(draft))
                import build_identity, release_contract
                with patch.object(release_contract, "verify", return_value={"suffix": "-b20261025000000000000000000000000"}), \
                     patch.object(build_identity, "verify_run", return_value=None):
                    with self.assertRaisesRegex(ValueError, "unavailable source/runtime evidence"):
                        shadow.publish_receipt(root, "keymapper", s.env, upload=lambda *_: self.fail("receipt upload reached"))
                self.assertFalse((root / "shadow-evidence" / shadow.receipt_name("keymapper")).exists())

    def test_source_extension_survives_existing_durable_reader_after_run_expiry(self):
        import datetime
        import hashlib
        import build_identity
        import qualified_baselines as qualified

        ident = "keymapper"
        repo, source_commit, run_id, attempt = "fixture/repo", "a" * 40, "12345", "2"
        run = {"GITHUB_SHA": source_commit, "GITHUB_RUN_ID": run_id,
               "GITHUB_RUN_ATTEMPT": attempt, "GITHUB_REPOSITORY": repo}
        snapshot = shadow.seal({
            "domain": "patch-factory/prepared-source-subset/v1", "schema": 1,
            "target": ident, "run": run, "apk": {"bytes": 1000100, "sha256": "c" * 64},
            "limits": source.LIMITS})
        suffix = build_identity.create({"GITHUB_RUN_ID": run_id, "GITHUB_RUN_ATTEMPT": attempt},
                                       datetime.datetime(2026, 9, 18, tzinfo=datetime.timezone.utc))
        tag = "key-mapper-v4.2.1" + suffix
        receipt = shadow.seal({
            "domain": shadow.RECEIPT_DOMAIN, "schema": 1, "target": ident, "repository": repo,
            "publication": "confirmed", "source_commit": source_commit,
            "run_id": run_id, "attempt": attempt, "tag": tag, "release_id": 77,
            "effective_sha256": "a" * 64, "declaration_sha256": "b" * 64,
            "apk": {"id": 88, "name": "key-mapper-v4.2.1-arm64-v8a.apk",
                    "bytes": 1000100, "sha256": "d" * 64},
            "eligibility": "REQUIRES_COMPLETED_SUCCESSFUL_RUN_AND_TARGET_JOB",
            "limits": ["same-run recorded evidence, not an independent signature or trust anchor",
                       "runtime/OS/container transitive dependencies incomplete"],
            "prepared_source": snapshot})
        blob = input_recipe.canonical(receipt)
        receipt_asset = {"id": 321, "name": shadow.receipt_name(ident), "state": "uploaded",
                         "size": len(blob), "digest": "sha256:" + hashlib.sha256(blob).hexdigest()}
        proof = {"coverage": "complete", "jobs_checked": 3, "repository": repo,
                 "run": {"id": int(run_id), "run_attempt": int(attempt), "head_sha": source_commit,
                         "head_branch": "main", "status": "completed", "conclusion": "success"},
                 "layout": "split", "jobs": []}
        for index, (role, steps) in enumerate(shadow.SPLIT_JOBS, 1):
            proof["jobs"].append({"id": index, "run_id": int(run_id), "run_attempt": int(attempt),
                                  "head_sha": source_commit, "name": role + " " + ident,
                                  "status": "completed", "conclusion": "success",
                                  "steps": [{"name": step, "status": "completed", "conclusion": "success"}
                                            for step in steps]})
        qualified_doc = shadow.seal({
            "domain": qualified.DOMAIN, "schema": 1, "repository": repo, "target": ident,
            "workflow_path": ".github/workflows/manual-patch.yml", "receipt": receipt,
            "proof": proof,
            "receipt_asset": {key: receipt_asset[key] for key in ("id", "name", "size", "digest")},
            "trust": "repository-actions-writer; not independent attestation"})
        qualified_asset = {"id": 654, "name": qualified.name(ident), "state": "uploaded",
                           "uploader": {"login": "github-actions[bot]", "type": "Bot"}}

        class RetainedAssets:
            def __init__(self, repository):
                self.repo = repository
            def asset(self, asset):
                return qualified_doc if asset["name"] == qualified.name(ident) else receipt
            def get(self, *_args, **_kwargs):
                raise AssertionError("durable reader must not need an expired workflow-run lookup")

        release = {"id": 77, "tag_name": tag, "draft": False, "prerelease": False,
                   "published_at": "2026-09-18T08:00:00Z"}
        with patch.object(qualified.shadow, "tag_commit", return_value=source_commit), \
             patch.object(qualified.shadow, "confirmed_apk", return_value=[receipt_asset]):
            retained = qualified.verify(RetainedAssets(repo), release, qualified_asset, ident)
        self.assertEqual(source.receipt_snapshot(retained), snapshot)



class SourceReportContracts(unittest.TestCase):
    def setUp(self):
        import source_report
        self.report = source_report
        self.s = SourceContracts()
        self.s.setUp()
        self.addCleanup(self.s.doCleanups)
        self.root, self.env = self.s.r, self.s.env
        self.prepared = self.s.prepare()
        self.identity = resolved.identity(self.root, self.env)
        self.current = source.snapshot(self.root, 'keymapper', self.env)
        self.doc = shadow.seal({
            'domain': source_report.DOMAIN, 'schema': 1, 'target': 'keymapper',
            'run': self.identity, 'current': self.current, 'baseline_tag': None,
            'decision': {'state': 'UNKNOWN', 'reason': 'LATEST_PUBLICATION_HAS_NO_SOURCE_SUBSET'},
            'limits': source.LIMITS})
        self.folder = self.root / 'source-observations' / (
            'source-observation-keymapper-' + self.identity['GITHUB_RUN_ID'] + '-' +
            self.identity['GITHUB_RUN_ATTEMPT'])
        self.folder.mkdir(parents=True)
        self.store(self.prepared, self.doc)

    def store(self, prepared, doc):
        (self.folder / 'keymapper.json').write_text(json.dumps(prepared))
        (self.folder / 'keymapper-comparison.json').write_text(json.dumps(doc))

    def aggregate(self, expected=None):
        with patch.object(self.report.dependency, 'expected_targets',
                          return_value=expected if expected is not None else ['keymapper']):
            return self.report.aggregate(self.root, self.env)

    def seal(self, doc):
        return shadow.seal({k:v for k,v in doc.items() if k != 'sha256'})

    def test_prepared_is_not_unchanged_and_cli_writes_bounded_summary(self):
        summary = self.root / 'report-summary.md'
        env = dict(self.env, GITHUB_STEP_SUMMARY=str(summary))
        with patch.object(self.report.dependency, 'expected_targets', return_value=['keymapper']), \
                patch.object(self.report.Path, 'cwd', return_value=self.root), \
                patch.object(self.report.os, 'environ', env), \
                patch.object(self.report.sys, 'argv', ['source_report.py']):
            self.assertEqual(self.report.main(), 0)
        result = json.loads((self.root / 'source-report/report.json').read_text())
        self.assertEqual(result['coverage'], 'complete')
        self.assertEqual(result['prepared_targets'], 1)
        self.assertEqual(result['counts']['UNKNOWN'], 1)
        self.assertIn('UNKNOWN is not unchanged', summary.read_text())
        self.assertIn('never selects or skips', result['authority'])

    def test_failure_marker_not_hidden_by_complete_observation_coverage(self):
        failed = {'target':'keymapper', 'status':'UNKNOWN', 'reason':'SOURCE_PREPARATION_FAILED',
                  'limits':source.LIMITS}
        doc = self.seal(dict(self.doc, current=None, decision={
            'state':'UNKNOWN', 'reason':'SOURCE_OR_BASELINE_UNAVAILABLE'}))
        self.store(failed, doc)
        result = self.aggregate()
        self.assertEqual(result['coverage'], 'complete')
        self.assertEqual(result['preparation_coverage'], 'incomplete')
        self.assertEqual(result['prepared_targets'], 0)
        self.assertEqual(result['targets'][0]['reason'], 'SOURCE_PREPARATION_FAILED')

    def test_missing_expected_target_remains_explicit_unknown(self):
        result = self.aggregate(['keymapper', 'youtube'])
        self.assertEqual(result['expected_targets'], 2)
        self.assertEqual(result['validated_observations'], 1)
        self.assertEqual(result['coverage'], 'incomplete')
        self.assertEqual(result['targets'][1]['state'], 'UNKNOWN')

    def test_zero_targets_is_not_complete(self):
        shutil.rmtree(self.root / 'source-observations')
        result = self.aggregate([])
        self.assertEqual(result['coverage'], 'incomplete')
        self.assertEqual(result['preparation_coverage'], 'incomplete')

    def test_wrong_target_run_attempt_and_tampered_digest_refused(self):
        for key, value in [('target','youtube'), ('run',dict(self.identity,GITHUB_RUN_ATTEMPT=str(int(self.identity['GITHUB_RUN_ATTEMPT'])+1))),
                           ('limits',[]), ('sha256','a'*64)]:
            with self.subTest(key=key):
                doc = dict(self.doc, **{key:value})
                if key != 'sha256':
                    doc = self.seal(doc)
                self.store(self.prepared, doc)
                result = self.aggregate()
                self.assertEqual(result['validated_observations'], 0)
                self.assertEqual(result['prepared_targets'], 0)

    def test_source_byte_and_manifest_mismatch_refused(self):
        for field, value in [('apk',dict(self.prepared['apk'],sha256='a'*64)),
                             ('metadata',dict(self.prepared['metadata'],package='wrong.package'))]:
            self.store(self.seal(dict(self.prepared, **{field:value})), self.doc)
            self.assertEqual(self.aggregate()['validated_observations'], 0)

    def test_unexpected_folder_file_and_symlink_refused(self):
        extra = self.folder / 'unexpected.json'
        extra.write_text('{}')
        self.assertEqual(self.aggregate()['validated_observations'], 0)
        extra.unlink()
        alien = self.folder.parent / 'source-observation-disabled-1-1'
        alien.mkdir()
        self.assertEqual(self.aggregate()['inventory_issues'], ['UNEXPECTED_OR_UNSAFE_ARTIFACT'])
        alien.rmdir()
        marker = self.folder / 'keymapper.json'
        marker.unlink()
        marker.symlink_to(self.root / source.LOCK)
        self.assertEqual(self.aggregate()['validated_observations'], 0)

    def test_valid_match_and_change_are_subset_only(self):
        for state in ('MATCHED_SOURCE_SUBSET', 'CHANGED_SOURCE_SUBSET'):
            doc = self.seal(dict(self.doc, baseline_tag='key-mapper-v4.2.1-b'+'1'*34,
                                decision={'state':state,'reason':'VERIFIED_SOURCE_BYTES_COMPARISON'}))
            self.store(self.prepared, doc)
            result = self.aggregate()
            self.assertEqual(result['counts'][state], 1)
            self.assertIn('shadow-only', result['authority'])
            doc = self.seal(dict(doc, baseline_tag=None))
            self.store(self.prepared, doc)
            self.assertEqual(self.aggregate()['validated_observations'], 0)

    def test_root_symlink_and_inconsistent_failure_cannot_look_healthy(self):
        failed = {'target':'keymapper', 'status':'UNKNOWN', 'reason':'SOURCE_PREPARATION_FAILED',
                  'limits':source.LIMITS}
        self.store(failed, self.doc)
        self.assertEqual(self.aggregate()['validated_observations'], 0)
        original = self.root / 'source-observations'
        saved = self.root / 'saved-source-observations'
        original.rename(saved)
        original.symlink_to(saved, target_is_directory=True)
        result = self.aggregate()
        self.assertEqual(result['prepared_targets'], 0)
        self.assertEqual(result['inventory_issues'], ['UNSAFE_ARTIFACT_ROOT'])

    def test_workflow_wiring_preserves_legacy_matrix(self):
        text = (Path(__file__).resolve().parents[1] / '.github/workflows/ci.yml').read_text()
        self.assertEqual(text.count('run: python3 src/build/source_report.py'), 1)
        self.assertIn('pattern: source-observation-*-${{ github.run_id }}-${{ github.run_attempt }}', text)
        self.assertIn('matrix: ${{ fromJson(needs.plan.outputs.matrix) }}', text)
        self.assertIn('name: source-report-${{ github.run_id }}-${{ github.run_attempt }}', text)


def load_tests(loader, tests, pattern):
    import community_watch_contracts
    tests.addTests(loader.loadTestsFromModule(community_watch_contracts))
    return tests


if __name__=='__main__':unittest.main()
