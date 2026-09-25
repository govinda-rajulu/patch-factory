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
        return source.prepare(self.r, self.ident, self.env, self.downloader, lambda *a: self.meta)

    def consumer(self):
        self.doc = self.prepare()
        (self.r / 'download').rename(self.r / 'preserved-producer-download')
        return source.install(self.r, self.ident, self.env)

    def capture(self):
        return {'target': self.ident, 'patcher_input_apk': resolved.regular(self.r, 'download/key-mapper.apk')}

    def reseal(self, doc):
        (self.r / source.LOCK).write_bytes(input_recipe.canonical(shadow.seal({k:v for k,v in doc.items() if k != 'sha256'})))

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
        with self.assertRaises(ValueError):source.prepare(self.r,self.ident,self.env,self.downloader,lambda *a:self.meta)
        self.assertEqual(self.fetches,0);self.assertFalse((self.r/'source-inputs').exists())
        self.assertEqual((p/'keep').read_bytes(),b'keep')

    def test_wrong_manifest_fails_before_exposing_packet(self):
        self.meta['package']='wrong.package'
        with self.assertRaises(ValueError):self.prepare()
        self.assertFalse((self.r/'source-inputs').exists())

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
        subprocess.run(['bash','src/build/selections.sh',self.ident,'lain'],cwd=self.r,check=True,capture_output=True)
        fakebin=self.r/'fakebin';fakebin.mkdir()
        java=fakebin/'java';java.write_text('#!/bin/bash\ntouch PATCHER_REACHED\nexit 77\n');java.chmod(0o755)
        env=dict(self.env,PATH=str(fakebin)+':'+os.environ['PATH'],PF_SOURCE_READY='true',
                 PF_EXECUTION_OBSERVATION='true')
        args=[sys.executable,'src/build/patch_target.py',self.ident,'lain']
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
        py=fakebin/'python3';py.write_text('#!/bin/bash\ncase "$1 $2" in\n"src/build/artifact_identity.py capture-signer") exit 0;;\n"src/build/artifact_identity.py capture-inputs") echo CAPTURE_BOUNDARY; exit 77;;\nesac\nexec '+sys.executable+' "$@"\n');py.chmod(0o755)
        aapt=fakebin/'aapt2';aapt.write_text("#!/bin/bash\nif [ \"$2\" = packagename ]; then echo io.github.sds100.keymapper; else echo \"sdkVersion:'29'\"; fi\n");aapt.chmod(0o755)
        env=dict(self.env,PATH=str(fakebin)+':'+os.environ['PATH'],ANDROID_HOME=str(fakebin),PF_RESOLVED_READY='true',PF_SOURCE_READY='true')
        result=subprocess.run(['bash','src/build/build.sh',self.ident],cwd=self.r,env=env,capture_output=True,text=True,timeout=30)
        self.assertIn('CAPTURE_BOUNDARY',result.stdout,result.stdout+result.stderr)
        self.assertNotIn('SECOND_FETCH',result.stdout+result.stderr)
        self.assertEqual(result.returncode,1)

    def test_download_adapter_preserves_apkpure_apkmirror_and_any_version(self):
        (self.r/'src/build/utils.sh').write_text('get_apk(){ printf "mirror|%s|%s|%s|%s|%s|%s\\n" "$1" "$2" "$3" "$version" "$lock_version" "$near_version"; }\nget_apkpure(){ printf "pure|%s|%s|%s|%s|%s\\n" "$1" "$2" "$3" "$version" "$lock_version"; }\n')
        targets=json.loads((self.r/'src/targets.json').read_text())
        self.assertEqual(len(targets),14)
        for target in targets:
            result=subprocess.run(['bash','src/build/source_download.sh',target['id'],'4.2.1'],cwd=self.r,env=source.clean_env(self.env),capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            parts=result.stdout.strip().split('|')
            self.assertEqual(parts[:4],['pure' if target.get('source')=='apkpure' else 'mirror',target['package'],target['apk_name'],target.get('apk_type','apk')])
            self.assertEqual(parts[4:6],['','1'] if target.get('any_version') else ['4.2.1',''])
            if parts[0]=='mirror':self.assertEqual(parts[-1],'1')

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
        self.f.prepare()
        env=dict(self.env,ANDROID_HOME=str(self.r/'android'))
        result=subprocess.run([sys.executable,'src/build/source_inputs.py','prepare',self.ident],
                              cwd=self.r,env=env,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(source.verify(self.r,self.ident,self.env)['metadata'],self.meta)
        self.assertTrue((self.r/'source-observation/keymapper.json').exists())

    def test_workflow_selection_publication_and_qualification_reader_preserved(self):
        ci=(self.r/'.github/workflows/ci.yml').read_text();manual=(self.r/'.github/workflows/manual-patch.yml').read_text()
        self.assertIn('matrix: ${{ fromJson(needs.plan.outputs.matrix) }}',ci)
        self.assertIn('cron: "30 12 * * *"',ci)
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
        subprocess.run(['bash','src/build/selections.sh','keymapper','lain'],cwd=self.r,check=True,capture_output=True)

    def test_actual_public_command_has_no_signing_secrets_or_absolute_checkout(self):
        doc=execution.public_command(self.r,'keymapper','lain',self.env)
        text=json.dumps(doc)
        for value in ['DO_NOT_INHERIT','SECRET','OMITTED','--keystore',str(self.r)]:self.assertNotIn(value,text)
        self.assertIn('Unlock Premium',doc['argv']);self.assertEqual(doc['approval'],'not evaluated')
        changed=execution.public_command(self.r,'keymapper','lain',dict(self.env,COE='true'))
        self.assertNotEqual(doc,changed)
        note=execution.public_command(self.r,'keymapper','lain',dict(self.env,KEYSTORE_PASS='changed secret'))
        self.assertEqual(doc,note)

    def test_byte_mode_positive_and_timestamp_negative_controls(self):
        p=self.r/'runtime';p.write_bytes(b'one');before=execution.file_identity(p)
        os.utime(p,(1,1));self.assertEqual(before,execution.file_identity(p))
        p.write_bytes(b'two');self.assertNotEqual(before,execution.file_identity(p))
        p.write_bytes(b'one');p.chmod(0o755);self.assertNotEqual(before,execution.file_identity(p))

    def test_observed_capture_rechecks_runtime_and_invocation(self):
        with patch.object(execution,'runtime',return_value={'fixture':'one'}):
            doc=execution.capture(self.r,'keymapper','lain',self.env)
            self.assertEqual(execution.verify(self.r,'keymapper','lain',self.env),doc)
        with patch.object(execution,'runtime',return_value={'fixture':'two'}):
            with self.assertRaises(ValueError):execution.verify(self.r,'keymapper','lain',self.env)
        with patch.object(execution,'runtime',return_value={'fixture':'one'}):
            with self.assertRaises(ValueError):execution.verify(self.r,'keymapper','lain',dict(self.env,COE='true'))
        with self.assertRaises(ValueError):execution.capture(self.r,'keymapper','lain',self.env)

    def test_unmodeled_runtime_unknown_never_exposes_values(self):
        env=dict(self.env,JAVA_TOOL_OPTIONS='super private string')
        doc=execution.capture(self.r,'keymapper','lain',env)
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
        captured = s.capture()
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
        api = s.verified()
        for key in ['PF_SOURCE_REQUESTED', 'PF_EXECUTION_OBSERVATION']:
            with self.subTest(key=key), self.assertRaises(ValueError):
                shadow.publish_receipt(s.r, 'keymapper', dict(s.env, **{key:'true'}), api, api.upload)
        self.assertEqual(len(api.rows), 1)  # Existing APK only, no new receipt asset.

    def test_source_extension_survives_existing_durable_reader_after_run_expiry(self):
        import hashlib
        import qualified_contracts
        q = qualified_contracts.QualifiedContracts()
        q.setUp()
        self.addCleanup(q.doCleanups)
        receipt = copy.deepcopy(q.receipt)
        snapshot = shadow.seal({
            'domain':'patch-factory/prepared-source-subset/v1', 'schema':1,
            'target':'keymapper',
            'run':{'GITHUB_SHA':receipt['source_commit'],'GITHUB_RUN_ID':receipt['run_id'],
                   'GITHUB_RUN_ATTEMPT':receipt['attempt'],'GITHUB_REPOSITORY':receipt['repository']},
            'apk':{'bytes':1000100,'sha256':'a'*64}, 'limits':source.LIMITS})
        receipt['prepared_source'] = snapshot
        receipt = shadow.seal({k:v for k,v in receipt.items() if k != 'sha256'})
        name = shadow.receipt_name('keymapper')
        blob = input_recipe.canonical(receipt)
        q.api.documents[name] = receipt
        row = next(row for row in q.api.rows if row['name'] == name)
        row.update(size=len(blob), digest='sha256:'+hashlib.sha256(blob).hexdigest())
        q.qualify()
        q.api.fail = '/actions/runs/'
        q.api.calls.clear()
        baseline, reason = shadow.latest_baseline(q.api,'keymapper','key-mapper')
        self.assertEqual(reason,'VERIFIED_DURABLE_ACTIONS_RECORD')
        self.assertEqual(source.receipt_snapshot(baseline),snapshot)
        self.assertFalse(any('/actions/runs/' in path for path in q.api.calls))


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
