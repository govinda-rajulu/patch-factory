import ast
import contextlib
import importlib.util
import io
import json
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


preflight = load('preflight', 'src/etc/preflight.py')
writer = load('writer', 'src/etc/selection_writer.py')
patcher = load('patcher', 'src/build/patch_target.py')
output = load('output', 'src/build/verify_output.py')
transfer_diagnostic = load('transfer_diagnostic', 'src/build/transfer_diagnostic.py')


class Repair(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='pf-contract-')
        self.r = pathlib.Path(self.tmp.name)
        shutil.copytree(ROOT / 'src', self.r / 'src')
        shutil.copytree(ROOT / 'docs', self.r / 'docs')
        shutil.copytree(ROOT / '.github', self.r / '.github')
        for name in ('README.md', 'CREDITS.md', 'AGENTS.md'):
            shutil.copy(ROOT / name, self.r / name)
        (self.r / 'release').mkdir()
        (self.r / 'download').mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, cmd, env=None):
        return subprocess.run(cmd, cwd=self.r, env={**os.environ, **(env or {})}, capture_output=True, text=True, timeout=45)

    def put(self, path, text):
        p = self.r / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def stub(self, name, body):
        self.put('bin/' + name, '#!/bin/bash\n' + body + '\n')
        (self.r / 'bin' / name).chmod(0o755)

    def env(self):
        return {'PATH': str(self.r / 'bin') + ':' + os.environ['PATH']}

    def snapshot(self):
        return {str(p.relative_to(self.r)): p.read_bytes() for p in (self.r / 'src/patches').rglob('*') if p.is_file()}

    def decide(self, rows):
        with contextlib.redirect_stdout(io.StringIO()):
            return writer.apply_decisions(self.r, rows)

    def make_apk(self, name='fixture-arm64-v8a.apk', manifest=True, dex=True):
        with zipfile.ZipFile(self.r / 'release' / name, 'w', compression=zipfile.ZIP_STORED) as z:
            if manifest:
                z.writestr('AndroidManifest.xml', b'fixture')
            if dex:
                z.writestr('classes.dex', b'x' * 1000100)
            z.writestr('assets/padding', b'p' * 1000100)

    def test_current_preflight(self):
        with contextlib.redirect_stdout(io.StringIO()):
            preflight.check(self.r)

    def test_public_import_generator_roundtrip_and_retired_exports_absent(self):
        path = self.r/'docs/obtainium.json'
        before = path.read_bytes()
        result = self.run_cmd(['python3','src/etc/obtainium.py'])
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertEqual(path.read_bytes(), before)
        exports = sorted(p.name for p in (self.r/'docs').glob('obtainium*.json'))
        self.assertEqual(exports, ['obtainium-microg.json', 'obtainium-self.json', 'obtainium.json'])
        apps = json.loads(before)['apps']
        targets = json.loads((self.r/'src/targets.json').read_text())
        self.assertEqual({a['name'] for a in apps},
                         {t['label'] for t in targets if t['enabled']})
        self.assertEqual(len(apps), len({a['id'] for a in apps}))

    def test_neutral_import_check_is_readonly_and_mismatch_is_failure(self):
        before = {str(p.relative_to(self.r)):p.read_bytes()
                  for p in (self.r/'docs').rglob('*') if p.is_file()}
        result = self.run_cmd(['python3','src/etc/obtainium.py','--check'])
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        after = {str(p.relative_to(self.r)):p.read_bytes()
                 for p in (self.r/'docs').rglob('*') if p.is_file()}
        self.assertEqual(before,after)
        self.put('docs/obtainium.json','{"apps":[]}')
        result = self.run_cmd(['python3','src/etc/obtainium.py','--check'])
        self.assertNotEqual(result.returncode,0)
        self.assertEqual((self.r/'docs/obtainium.json').read_text(),'{"apps":[]}')

    def test_identity_and_recipe_use_only_neutral_catalog_path(self):
        for name in ('artifact_identity.py','input_recipe.py'):
            source=(ROOT/'src/build'/name).read_text()
            self.assertIn('docs/obtainium.json',source)
            self.assertNotIn('obtainium-'+'govind.json',source)
            self.assertNotIn('obtainium-'+'parents.json',source)

    def test_portal_import_release_and_rendering_contracts(self):
        result = subprocess.run(['node', str(ROOT/'tests/portal_contracts.cjs')],
                                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertIn('PORTAL_CONTRACTS_PASS=23', result.stdout)

    def test_microg_companion_generator_is_separate_and_check_refuses_drift(self):
        path = self.r/'docs/obtainium-microg.json'
        before = path.read_bytes()
        main = (self.r/'docs/obtainium.json').read_bytes()
        result = self.run_cmd(['python3','src/etc/obtainium.py'])
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(path.read_bytes(),before)
        self.assertEqual((self.r/'docs/obtainium.json').read_bytes(),main)
        apps=json.loads(before)['apps']
        self.assertEqual(len(apps),1)
        self.assertEqual(apps[0]['id'],'app.revanced.android.gms')
        self.assertFalse(any(t['package']==apps[0]['id'] for t in json.loads((self.r/'src/targets.json').read_text())))
        self.put('docs/obtainium-microg.json','{"apps":[]}')
        result=self.run_cmd(['python3','src/etc/obtainium.py','--check'])
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(path.read_text(),'{"apps":[]}')
        self.assertEqual((self.r/'docs/obtainium.json').read_bytes(),main)

    def test_failure_notifier_contracts(self):
        result = subprocess.run(['node', str(ROOT / 'tests/notify_contracts.cjs')],
                                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('NOTIFY_CONTRACTS_PASS=21', result.stdout)

    def batch_probe(self, raw, targets=None):
        if targets is not None:
            self.put('src/targets.json', json.dumps(targets))
        self.put('batch-output.txt', 'preserved=yes\n')
        result = self.run_cmd(['bash', 'src/etc/batchplan.sh'],
                             {'RAW': raw, 'GITHUB_OUTPUT': str(self.r/'batch-output.txt')})
        return result, (self.r/'batch-output.txt').read_text()

    def test_batch_all_enabled_has_exact_unique_coverage(self):
        targets = json.loads((self.r/'src/targets.json').read_text())
        ids = [t['id'] for t in targets if t['enabled']]
        self.assertEqual(len(ids), 14)
        result, text = self.batch_probe(','.join(ids))
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        lines = text.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], 'preserved=yes')
        self.assertEqual(json.loads(lines[1].removeprefix('matrix=')), {'target': ids})

    def test_batch_invalid_requests_never_append_outputs(self):
        for raw in ('', ' ', ',', 'youtube,', ',youtube', 'youtube,,reddit',
                    'youtube,youtube', 'unknown', 'youtube\nmatrix=wrong', 'x'*8193):
            with self.subTest(raw=raw[:40]):
                result, text = self.batch_probe(raw)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(text, 'preserved=yes\n')

    def test_batch_refuses_disabled_and_ambiguous_config(self):
        for targets in ([], {}, [{'id':'youtube','enabled':False}],
                        [{'id':'youtube','enabled':True}]*2,
                        [{'id':'youtube','enabled':'true'}],
                        [{'id':'youtube'}], [None], [{'id':'../x','enabled':True}]):
            with self.subTest(targets=targets):
                result, text = self.batch_probe('youtube', targets)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(text, 'preserved=yes\n')

    def test_batch_json_duplicate_keys_fail_before_output(self):
        self.put('src/targets.json', '[{"id":"youtube","enabled":true,"enabled":false}]')
        result, text = self.batch_probe('youtube')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('duplicate JSON key', result.stderr)
        self.assertEqual(text, 'preserved=yes\n')

    def test_batch_keeps_requested_order_and_trims_outer_spaces(self):
        result, text = self.batch_probe(' reddit , youtube ')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(text.splitlines()[1][len('matrix='):]),
                         {'target':['reddit','youtube']})

    def test_batch_malformed_json_is_not_empty_success(self):
        self.put('src/targets.json', 'not json')
        result, text = self.batch_probe('youtube')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(text, 'preserved=yes\n')

    def test_test_apk_upload_follows_successful_handoff_only(self):
        text = (ROOT/'.github/workflows/manual-patch.yml').read_text()
        gate = text.index('      - name: Verify release handoff (no publishing)')
        upload = text.index('      - name: Save verified test APK and evidence (not a release)')
        publish = text.index('      - name: Releasing APK files')
        self.assertLess(gate, upload)
        self.assertLess(upload, publish)
        block = text[upload:publish]
        self.assertIn("if: success() && (!inputs.publish || github.ref != 'refs/heads/main')", block)
        from action_refs import same_reference
        same_reference(block, (ROOT/'.github/workflows/validate.yml').read_text(), 'actions/upload-artifact')
        self.assertIn('test-apk-${{ inputs.target }}-${{ github.run_id }}-${{ github.run_attempt }}', block)
        self.assertIn('            release/*.apk\n            build-evidence/${{ inputs.target }}.json\n', block)
        self.assertIn('if-no-files-found: error', block)
        self.assertIn('retention-days: 7', block)
        for unsafe in ('src/', '**', 'always()', 'continue-on-error', 'keystore'):
            self.assertNotIn(unsafe, block)

    def test_action_upgrade_smoke_stays_inside_mandatory_readonly_validation(self):
        text = (ROOT/'.github/workflows/validate.yml').read_text()
        block = text.split('      # ACTION_COMPATIBILITY_SMOKE_START\n', 1)[1]
        self.assertIn('permissions:\n  contents: read\n', text)
        from action_refs import references, same_reference
        for action in ('setup-java', 'cache', 'cache/save', 'upload-artifact',
                       'github-script', 'download-artifact'):
            references(block, 'actions/' + action, pinned=action == 'download-artifact')
        self.assertEqual(references(block, 'actions/cache'), references(block, 'actions/cache/save'))
        # Dependabot may update releases, but every production workflow use must
        # still be exercised by the same mandatory runtime smoke.
        for workflow in (ROOT/'.github/workflows').glob('*.yml'):
            source = workflow.read_text()
            for action in ('checkout', 'setup-java', 'cache', 'upload-artifact',
                           'github-script', 'download-artifact'):
                if 'uses: actions/' + action + '@' in source:
                    same_reference(source, text, 'actions/' + action,
                                   pinned=action == 'download-artifact')
        for forbidden in ('secrets.', 'continue-on-error', 'overwrite: true',
                          'restore-keys:', 'include-hidden-files: true',
                          'pull_request_target', 'workflow_run:', 'release/*.apk',
                          'actions: write', 'contents: write', 'issues: write'):
            self.assertNotIn(forbidden, block)
        self.assertIn('archive: true', block)
        self.assertIn('digest-mismatch: error', block)
        self.assertIn('skip-decompress: false', block)
        self.assertIn('retention-days: 1', block)
        self.assertIn('pf-action-smoke-${{ github.run_id }}-${{ github.run_attempt }}', block)
        self.assertIn('steps.smoke_cache.outputs.cache-hit', block)
        self.assertIn('cmp action-smoke-cache/value.txt action-smoke-download/nested/value.txt', block)
        self.assertIn('test ! -e action-smoke-download/.hidden-probe', block)
        self.assertIn('github.rest.actions.getWorkflowRun', block)

    def test_action_refs_accept_coordinated_versions_but_reject_drift(self):
        from action_refs import references, same_reference
        for version in ('v7', 'v8.2.1', 'a'*40):
            text = '  uses: actions/upload-artifact@' + version + '\n'
            self.assertEqual(same_reference(text, text, 'actions/upload-artifact'), {version})
        for version in ('main', '${{ inputs.ref }}', 'v0', 'abcd', 'v7;echo'):
            with self.assertRaises(ValueError):
                references('uses: actions/upload-artifact@' + version, 'actions/upload-artifact')
        for source, smoke in [('v7', 'v8'), ('v8', 'v7')]:
            with self.assertRaises(ValueError):
                same_reference('uses: actions/upload-artifact@' + source,
                               'uses: actions/upload-artifact@' + smoke, 'actions/upload-artifact')
        with self.assertRaises(ValueError):
            references('uses: actions/download-artifact@v8', 'actions/download-artifact', pinned=True)
        with self.assertRaises(ValueError):
            references('uses: other/upload-artifact@v7', 'actions/upload-artifact')

    def direct_navigation_probe(self, source=None):
        # Execute the real get_apk entrypoint; stop at its first page request.
        # This fixture does not download an APK or contact a live service.
        source = source or (ROOT/'src/build/utils.sh').read_text()
        fn = source[source.index('get_apk() {'):source.index('\nget_apkpure() {')]
        self.put('src/build/helper/apps.json', json.dumps({
            'apkmirror': {'com.fixture': {
                'list_url': 'https://www.apkmirror.com/fixture',
                'example_url': 'https://www.apkmirror.com/fixture-1-0-release/'}}}))
        script = """
green_log(){ :; }; yellow_log(){ :; }; red_log(){ :; }
_fs_session_start(){ echo SESSION_START_CALLED; return 91; }
_fs_session_close(){ echo SESSION_CLOSE_CALLED; return 92; }
detect_version(){ version=2.0; }
_cf_get(){ echo PAGE_REACHED; return 17; }
""" + fn + """
version=1.0
prefer_version=
near_version=1
_FFS_FAILED=7
_PF_FS_SESSION=caller-owned
get_apk com.fixture fixture apk
rc=$?
printf 'RESULT=%s VERSION=%s FALLBACK=%s CALLER=%s\\n' "$rc" "$version" "$_FFS_FAILED" "$_PF_FS_SESSION"
"""
        return self.run_cmd(['bash', '-c', script])

    def test_direct_navigation_needs_no_session_service(self):
        r = self.direct_navigation_probe()
        self.assertEqual(r.returncode, 0, r.stdout+r.stderr)
        self.assertIn('PAGE_REACHED', r.stdout)
        self.assertIn('RESULT=1', r.stdout)
        self.assertNotIn('SESSION_START_CALLED', r.stdout)
        self.assertNotIn('SESSION_CLOSE_CALLED', r.stdout)

    def test_direct_navigation_preserves_version_and_existing_fallback_state(self):
        r = self.direct_navigation_probe()
        self.assertEqual(r.returncode, 0, r.stdout+r.stderr)
        self.assertIn('VERSION=2.0 FALLBACK=7 CALLER=caller-owned', r.stdout)

    def test_session_prerequisite_mutation_is_detected(self):
        source = (ROOT/'src/build/utils.sh').read_text()
        self.assertEqual(source.count('get_apk() {'), 1)
        mutant = source.replace('get_apk() {',
                                'get_apk() {\n\t_fs_session_start || return 1', 1)
        r = self.direct_navigation_probe(mutant)
        self.assertEqual(r.returncode, 0, r.stdout+r.stderr)
        self.assertIn('SESSION_START_CALLED', r.stdout)
        self.assertNotIn('PAGE_REACHED', r.stdout)

    def test_stateless_resolver_never_sends_caller_session(self):
        source = (ROOT/'src/build/utils.sh').read_text()
        fn = source[source.index('_fs_get() {'):source.index('\n_cfb_get() {')]
        self.put('stateless-http.py', """
import json,sys
args=sys.argv[1:];d=json.loads(args[args.index('-d')+1])
with open('stateless-calls.jsonl','a') as f:f.write(json.dumps(d)+'\\n')
if set(d)!={'cmd','url','maxTimeout'} or d['cmd']!='request.get':sys.exit(91)
print(json.dumps({'status':'ok','solution':{'response':'HTML','cookies':[],'userAgent':'UA'}}))
""")
        script = """
curl(){ python3 stateless-http.py "$@"; }
yellow_log(){ :; }; red_log(){ :; }
""" + fn + """
_PF_FS_SESSION=caller-owned
_fs_get https://www.apkmirror.com/first || exit 21
_fs_get https://www.apkmirror.com/second || exit 22
test "$_PF_FS_SESSION" = caller-owned || exit 23
"""
        r = self.run_cmd(['bash','-c',script])
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        calls = [json.loads(x) for x in (self.r/'stateless-calls.jsonl').read_text().splitlines()]
        self.assertEqual(len(calls),2)
        self.assertTrue(all(c['cmd']=='request.get' and 'session' not in c for c in calls))

    def test_existing_fallback_reached_after_stateless_resolver_failure(self):
        source = (ROOT/'src/build/utils.sh').read_text()
        fn = source[source.index('_cf_get() {'):source.index('\nget_apk() {')]
        for fallback_rc in (0,19):
            script = """
yellow_log(){ :; }
_fs_get(){ echo FS >> calls.txt; return 1; }
_cfb_get(){ echo CFB >> calls.txt; return "$FALLBACK_RC"; }
""" + fn + """
_FFS_FAILED=0
_cf_get https://example.invalid/first
a=$?
_cf_get https://example.invalid/second
b=$?
test "$a" = "$FALLBACK_RC" && test "$b" = "$FALLBACK_RC" && test "$_FFS_FAILED" = 1
"""
            self.put('calls.txt','')
            r = self.run_cmd(['bash','-c',script],{'FALLBACK_RC':str(fallback_rc)})
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            self.assertEqual((self.r/'calls.txt').read_text().splitlines(),['FS','CFB','CFB'])

    def test_unscoped_resolver_retains_ephemeral_contract_and_quotes_url(self):
        self.put('capture-request.py',"""
import json,sys
a=sys.argv[1:];d=json.loads(a[a.index('-d')+1])
json.dump(d,open('unscoped-request.json','w'))
print(json.dumps({'status':'ok','solution':{'response':'HTML','cookies':[],'userAgent':'UA'}}))
""")
        source=(ROOT/'src/build/utils.sh').read_text()
        fn=source[source.index('_fs_get() {'):source.index('\n_cfb_get() {')]
        url='https://www.apkmirror.com/page?q="quoted"&backslash=\\\\'
        r=self.run_cmd(['bash','-c',"""
curl(){ python3 capture-request.py "$@"; }
yellow_log(){ :; }; red_log(){ :; }
""" + fn + '\n_fs_get "$TEST_URL"\n'],{'TEST_URL':url})
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        d=json.loads((self.r/'unscoped-request.json').read_text())
        self.assertEqual(d['url'],url)
        self.assertNotIn('session',d)

    def test_stateless_change_keeps_transfer_gates_and_no_session_dependency(self):
        source=(ROOT/'src/build/utils.sh').read_text()
        impl=source[source.index('get_apk() {'):source.index('\nget_apkpure() {')]
        self.assertIn('if ! wget -q -O "./download/$base_apk"',impl)
        self.assertIn('"$base_url$final_href"; then',impl)
        pure=source[source.index('get_apkpure() {'):]
        self.assertNotIn('_PF_FS_SESSION',pure)
        for token in ('sessions.create','sessions.destroy','_fs_session_start','_fs_session_close','_get_apk_impl','_PF_FS_SESSION'):
            self.assertNotIn(token,source)

    def test_store_transfer_failures_never_claim_success(self):
        """Exercise the actual final-transfer blocks without sourcing network setup.
        Nonempty controls are transfer evidence only, not validated APKs.
        """
        source = (ROOT / 'src/build/utils.sh').read_text()
        for store, function, end_anchor in (
                ('APKMirror', 'get_apk()', '\n\tif [[ "$matched_type" == "BUNDLE" ]]'),
                ('APKPure', 'get_apkpure()', '\n\tif [[ "$pkg_type" == "bundle" ]]')):
            begin = source.index('\tif ! wget -q -O "./download/$base_apk"', source.index(function))
            end = source.index(end_anchor, begin)
            block = source[begin:end]
            self.assertEqual(block.count('wget -q'), 1)
            for rc, payload, expected in ((8, '', 1), (8, 'partial', 1),
                                          (0, '', 1), (0, 'fixture-transfer-bytes', 0)):
                with self.subTest(store=store, wget_exit=rc, bytes=len(payload)):
                    command = """
green_log(){ printf '%s\\n' "$*"; }
red_log(){ printf '%s\\n' "$*"; }
wget(){
  [ "$1" = -q ] || { echo FAKE_SIGNED_URL_LEAK >&2; return 99; }
  printf '%s' "$FIXTURE_BYTES" > "./download/fixture.apk"
  return "$FIXTURE_EXIT"
}
transfer(){
  local base_apk=fixture.apk apk_name=fixture user_agent=fixture
  local base_url=https://example.invalid dl_btn_href=/button final_href=/file
  local dl_page_url=https://example.invalid/page download_url=https://example.invalid/file
  local cookie_args=()
""" + block + '\n}\ntransfer\n'
                    result = self.run_cmd(['bash', '-c', command],
                                          {'FIXTURE_BYTES':payload, 'FIXTURE_EXIT':str(rc)})
                    self.assertEqual(result.returncode, expected, result.stdout+result.stderr)
                    self.assertEqual('Successfully downloaded' in result.stdout, expected == 0)
                    self.assertNotIn('FAKE_SIGNED_URL_LEAK', result.stdout+result.stderr)

    def test_store_failed_transfer_stops_before_conversion(self):
        source = (ROOT / 'src/build/utils.sh').read_text()
        for function in ('get_apk()', 'get_apkpure()'):
            start = source.index('\tif ! wget -q',source.index(function))
            end = source.index('\n}',start)
            body = source[start:end]
            stop = body.index('return 1')
            self.assertLess(stop, body.index('Successfully downloaded'))
            if 'java -jar' in body:
                self.assertLess(stop, body.index('java -jar'))

    def test_diagnostic_redacts_fake_signed_url_and_cookie(self):
        request='https://www.apkmirror.com/download.php?key=FAKE_REQUEST_SECRET'
        resolved='https://fixture.r2.cloudflarestorage.com/file.apk?X-Amz-Signature=FAKE_SIGNATURE'
        data={'status':'ok','solution':{'url':resolved,'status':200,
              'cookies':[{'name':'secret','value':'FAKE_COOKIE'}],'userAgent':'FAKE_USER_AGENT'}}
        out=transfer_diagnostic.resolver(json.dumps(data).encode(),request)
        text=json.dumps(out)
        for secret in ('FAKE_REQUEST_SECRET','FAKE_SIGNATURE','FAKE_COOKIE','FAKE_USER_AGENT','file.apk'):
            self.assertNotIn(secret,text)
        self.assertEqual(out['resolved']['kind'],'r2-object')
        self.assertFalse(out['same_url'])
        self.assertTrue(out['cookies_present'])
        self.assertEqual(out['http_status'],200)

    def test_diagnostic_no_redirect_is_distinct_from_missing_url(self):
        u='https://www.apkmirror.com/download.php?key=FAKE'
        for resolved, expected in ((u,True),('',None),(None,None)):
            with self.subTest(resolved=resolved):
                raw=json.dumps({'status':'ok','solution':{'url':resolved}}).encode()
                d=transfer_diagnostic.resolver(raw,u)
                self.assertEqual(d['same_url'],expected)

    def test_diagnostic_malformed_and_oversized_response_redacted(self):
        for raw in (b'RAW_SECRET',b'[]',b'null',b'{"solution":[]}',
                    b'x'*(transfer_diagnostic.MAX_RESPONSE+1)):
            out=transfer_diagnostic.resolver(raw,'SECRET')
            self.assertEqual(out,{'stage':'resolver','parser':'invalid-or-oversized'})

    def test_diagnostic_url_shapes_never_raise_or_reveal_input(self):
        values=('http://example.invalid/key=SECRET','https://name:SECRET@host/file',
                'https://host:wrong/SECRET','https://host:444/SECRET',
                'https://[invalid/SECRET','not-url-SECRET')
        for u in values:
            with self.subTest(url=u):
                d=transfer_diagnostic.location(u)
                self.assertNotIn('SECRET',json.dumps(d))
                self.assertIn(d['kind'],('unsupported','unparseable'))

    def test_diagnostic_http_status_cannot_inject_logs(self):
        raw=json.dumps({'status':'ok','solution':{'status':'SECRET\nanother line'}}).encode()
        d=transfer_diagnostic.resolver(raw,'')
        self.assertIsNone(d['http_status'])
        self.assertNotIn('SECRET',json.dumps(d))

    def test_diagnostic_handoff_records_presence_not_values(self):
        d=transfer_diagnostic.handoff({'PF_DIAG_DEST':'https://www.apkmirror.com/download.php?key=SECRET',
                                      'PF_DIAG_REFERER':'https://www.apkmirror.com/page',
                                      'PF_DIAG_COOKIES':'SECRET','PF_DIAG_UA':'SECRET'})
        self.assertEqual(d['destination']['kind'],'apkmirror-download-endpoint')
        self.assertTrue(d['cookies_present'])
        self.assertNotIn('SECRET',json.dumps(d))

    def test_page_shape_counts_without_exposing_content(self):
        raw=b'<title>FAKE_TITLE_SECRET</title><a id="download_link" href="https://host/file?sig=FAKE_SIGNED_SECRET">FAKE_TEXT_SECRET</a>'
        d=transfer_diagnostic.page(raw)
        self.assertEqual(d['bytes'],len(raw))
        self.assertEqual(d['apkpure_download_ids'],1)
        self.assertEqual(d['download_ids_with_href'],1)
        self.assertEqual(d['authority'],'diagnostic-only')
        for value in ('FAKE_', 'https:', 'host', 'sig=', 'title'):
            self.assertNotIn(value,json.dumps(d))

    def test_page_shape_unicode_byte_count(self):
        raw='<p>é日本</p>'.encode()
        self.assertEqual(transfer_diagnostic.page(raw)['bytes'],len(raw))

    def test_page_shape_missing_and_empty_are_distinct(self):
        self.assertTrue(transfer_diagnostic.page(b'  ')['empty'])
        d=transfer_diagnostic.page(b'<html>No download anchor</html>')
        self.assertFalse(d['empty'])
        self.assertEqual(d['apkpure_download_ids'],0)

    def test_page_shape_marker_is_not_proof(self):
        d=transfer_diagnostic.page(b'<p>Just a moment; version not found</p>')
        self.assertTrue(d['challenge_marker_present'])
        self.assertTrue(d['unavailable_marker_present'])
        self.assertEqual(d['marker_limit'],'heuristic presence only, not a diagnosis')

    def test_page_shape_duplicate_href_and_multiple_links(self):
        d=transfer_diagnostic.page(b'<a href="secret" href="other" id="download_link"></a><a id="download_link"></a><a id="download-link" href="/secret"></a>')
        self.assertEqual(d['apkpure_download_ids'],2)
        self.assertEqual(d['apkmirror_download_ids'],1)
        self.assertEqual(d['download_ids_with_duplicate_href'],1)
        self.assertEqual(d['download_ids_with_href'],2)

    def test_page_shape_non_anchor_ids_do_not_count(self):
        d=transfer_diagnostic.page(b'<script>FAKE_SECRET</script><div id="download_link"></div>')
        self.assertEqual(d['anchors'],0)
        self.assertEqual(d['apkpure_download_ids'],0)
        self.assertNotIn('FAKE_SECRET',json.dumps(d))

    def test_page_shape_refuses_oversized_invalid_and_nonbytes(self):
        for raw in (None,'FAKE_SECRET',b'\xff',b'x'*(transfer_diagnostic.MAX_PAGE+1)):
            d=transfer_diagnostic.page(raw)
            self.assertEqual(d['parser'],'invalid-or-oversized')
            self.assertNotIn('FAKE_SECRET',json.dumps(d))

    def test_resolver_adds_shape_without_changing_status(self):
        raw=json.dumps({'status':'ok','solution':{'status':200,'response':'<p>Page not found FAKE_SECRET</p>'}}).encode()
        d=transfer_diagnostic.resolver(raw,'')
        self.assertTrue(d['resolver_ok'])
        self.assertEqual(d['http_status'],200)
        self.assertTrue(d['response_shape']['unavailable_marker_present'])
        self.assertNotIn('FAKE_SECRET',json.dumps(d))

    def test_page_cli_is_bounded_json_only(self):
        r=subprocess.run([sys.executable,str(ROOT/'src/build/transfer_diagnostic.py'),'page'],
                         input=b'<a id="download_link" href="?secret=FAKE_SECRET"></a>',
                         capture_output=True,timeout=10)
        self.assertEqual(r.returncode,0)
        self.assertEqual(r.stderr,b'')
        self.assertNotIn(b'FAKE_SECRET',r.stdout)
        self.assertEqual(json.loads(r.stdout.decode().split(' ',1)[1])['apkpure_download_ids'],1)

    def test_apkpure_missing_link_emits_safe_stage_and_never_transfers(self):
        source=(ROOT/'src/build/utils.sh').read_text()
        fn=source[source.index('get_apkpure() {'):source.index('\n# Download APK from Google Play Store')]
        self.put('src/build/helper/apps.json',json.dumps({'apkpure':{'com.fixture':{'download_url':'https://apkpure.com/x/com.fixture/download'}}}))
        command="""
green_log(){ printf '%s\\n' "$*"; }; yellow_log(){ printf '%s\\n' "$*"; }; red_log(){ printf '%s\\n' "$*"; }
detect_version(){ :; }
_cf_get(){ html='<html>Just a moment FAKE_PAGE_SECRET</html>'; return 0; }
fake_pup(){ cat >/dev/null; }
wget(){ echo TRANSFER_REACHED; return 99; }
version=1.0; prefer_version=; pup=fake_pup; user_agent=FAKE_UA_SECRET; FS_COOKIES=FAKE_COOKIE_SECRET
""" + fn + '\nget_apkpure com.fixture fixture apk\n'
        r=self.run_cmd(['bash','-c',command])
        self.assertEqual(r.returncode,1,r.stdout+r.stderr)
        self.assertIn('"binary_transfer_started":false',r.stdout)
        self.assertIn('"challenge_marker_present": true',r.stdout)
        self.assertNotIn('TRANSFER_REACHED',r.stdout)
        self.assertNotIn('FAKE_',r.stdout+r.stderr)

    def test_apkpure_valid_link_preserves_transfer_inputs_privately(self):
        source=(ROOT/'src/build/utils.sh').read_text()
        fn=source[source.index('get_apkpure() {'):source.index('\n# Download APK from Google Play Store')]
        self.put('src/build/helper/apps.json',json.dumps({'apkpure':{'com.fixture':{'download_url':'https://apkpure.com/x/com.fixture/download'}}}))
        command="""
green_log(){ printf '%s\\n' "$*"; }; yellow_log(){ printf '%s\\n' "$*"; }; red_log(){ printf '%s\\n' "$*"; }
detect_version(){ :; }
_cf_get(){ html='<a id="download_link" href="https://example.invalid/file?sig=FAKE_SIGNED_SECRET">Download</a>'; return 0; }
fake_pup(){ cat >/dev/null; printf '%s\\n' 'https://example.invalid/file?sig=FAKE_SIGNED_SECRET'; }
wget(){
 [ "$1" = -q ] || { echo FAKE_SIGNED_SECRET; return 99; }
 printf '%s\\n' "$@" > private-argv.txt
 printf fixture > ./download/fixture.apk
}
version=1.0; prefer_version=; pup=fake_pup; user_agent=FAKE_UA_SECRET; FS_COOKIES=FAKE_COOKIE_SECRET
""" + fn + '\nget_apkpure com.fixture fixture apk\n'
        r=self.run_cmd(['bash','-c',command])
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertNotIn('FAKE_',r.stdout+r.stderr)
        args=(self.r/'private-argv.txt').read_text().splitlines()
        self.assertIn('https://example.invalid/file?sig=FAKE_SIGNED_SECRET',args)
        self.assertIn('Cookie: FAKE_COOKIE_SECRET',args)
        self.assertIn('--header=User-Agent: FAKE_UA_SECRET',args)
        self.assertIn('--referer=https://apkpure.com/x/com.fixture/download/1.0',args)

    def test_store_url_echoes_removed_without_changing_selectors(self):
        source=(ROOT/'src/build/utils.sh').read_text()
        block=source[source.index('_fs_get() {'):source.index('\n# Download APK from Google Play Store')]
        for literal in ('echo "$base_url$final_href"','echo "$download_url"','echo "$dl_page_url"','failed: $url','HTTP $http_code: $url'):
            self.assertNotIn(literal,block)
        self.assertEqual(block.count('wget -q -O "./download/$base_apk"'),2)
        self.assertIn("'a#download_link attr{href}'",block)
        self.assertIn("'a#download-link attr{href}'",block)

    def test_real_resolver_calls_diagnostic_without_changing_url_or_cookie(self):
        text=(ROOT/'src/build/utils.sh').read_text()
        fn=text[text.index('_fs_get() {'):text.index('\n_cfb_get() {')]
        req='https://www.apkmirror.com/download.php?key=FAKE_REQUEST'
        resolved='https://fixture.r2.cloudflarestorage.com/file.apk?sig=FAKE_SIGNATURE'
        raw=json.dumps({'status':'ok','solution':{'url':resolved,'response':'FIXTURE_HTML',
                        'status':200,'cookies':[{'name':'test','value':'FAKE_COOKIE'}],
                        'userAgent':'FIXTURE_UA'}})
        command="""
curl(){ printf '%s' "$FAKE_RESPONSE"; }
yellow_log(){ printf '%s\\n' "$*"; }
red_log(){ printf '%s\\n' "$*"; }
""" + fn + """
_fs_get "$FAKE_REQUEST"
test "$html" = FIXTURE_HTML || exit 51
test "$FS_COOKIES" = 'test=FAKE_COOKIE' || exit 52
test "$user_agent" = FIXTURE_UA || exit 53
"""
        r=self.run_cmd(['bash','-c',command],{'FAKE_RESPONSE':raw,'FAKE_REQUEST':req})
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(len(r.stdout.splitlines()),1,r.stdout)
        self.assertTrue(r.stdout.startswith('DOWNLOAD_DIAGNOSTIC '))
        self.assertIn('"kind": "r2-object"',r.stdout)
        for secret in ('FAKE_SIGNATURE','FAKE_COOKIE','FAKE_REQUEST'):
            self.assertNotIn(secret,r.stdout+r.stderr)

    def test_diagnostic_failure_does_not_change_resolver_success(self):
        text=(ROOT/'src/build/utils.sh').read_text()
        fn=text[text.index('_fs_get() {'):text.index('\n_cfb_get() {')]
        raw=json.dumps({'status':'ok','solution':{'response':'HTML','cookies':[],'userAgent':'UA'}})
        command="curl(){ printf '%s' \"$FAKE_RESPONSE\"; }\npython3(){ return 9; }\nyellow_log(){ :; }\nred_log(){ :; }\n"+fn+"\n_fs_get https://example.invalid/page\n"
        r=self.run_cmd(['bash','-c',command],{'FAKE_RESPONSE':raw})
        self.assertEqual(r.returncode,0)

    def test_handoff_quiets_wget_without_changing_request_argv(self):
        text=(ROOT/'src/build/utils.sh').read_text()
        start=text.index('\tlocal cookie_args=()',text.index('\tlocal final_href',text.index('get_apk()')))
        end=text.index('\n\tif [[ "$matched_type" == "BUNDLE" ]]',start)
        block=text[start:end]
        command="""
green_log(){ printf '%s\\n' "$*"; }
yellow_log(){ printf '%s\\n' "$*"; }
red_log(){ printf '%s\\n' "$*"; }
wget(){
  python3 -c 'import json,sys;json.dump(sys.argv[1:],open("fixture-argv.json","w"))' "$@"
  printf 'fixture bytes' > download/fixture.apk
}
transfer(){
 local base_apk=fixture.apk apk_name=fixture base_url=https://www.apkmirror.com
 local final_href='/download.php?key=FAKE_DEST' dl_btn_href='/button?key=FAKE_REF'
 local FS_COOKIES='test=FAKE_COOKIE' user_agent=FAKE_UA
""" + block + "\n}\ntransfer\n"
        r=self.run_cmd(['bash','-c',command])
        self.assertEqual(r.returncode,0,r.stderr)
        args=json.loads((self.r/'fixture-argv.json').read_text())
        self.assertEqual(args,['-q','-O','./download/fixture.apk','--header=User-Agent: FAKE_UA',
                             '--referer=https://www.apkmirror.com/button?key=FAKE_REF','--header',
                             'Cookie: test=FAKE_COOKIE','--timeout=120',
                             'https://www.apkmirror.com/download.php?key=FAKE_DEST'])
        for secret in ('FAKE_DEST','FAKE_REF','FAKE_COOKIE','FAKE_UA'):
            self.assertNotIn(secret,r.stdout+r.stderr)

    def test_unknown_target(self):
        with self.assertRaises(ValueError):
            preflight.check(self.r, 'unknown')

    def test_preflight_overlap(self):
        self.put('src/patches/esfile-ftl/exclude-patches', 'Remove Ads\n')
        with self.assertRaises(ValueError):
            preflight.check(self.r)

    def test_preflight_duplicate_prefix(self):
        p = self.r / 'src/targets.json'
        data = json.loads(p.read_text());data[1]['tag_prefix'] = data[0]['tag_prefix'];p.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            preflight.check(self.r)

    def test_sdk_unreadable_rejects(self):
        self.stub('python3', 'exit 1');self.stub('pip', 'exit 1')
        x = self.run_cmd(['bash', 'src/build/check_sdk.sh', 'missing.apk', '29'], {**self.env(), 'ANDROID_HOME': str(self.r / 'empty')})
        self.assertNotEqual(x.returncode, 0, x.stdout)

    def sdk(self, n):
        p = self.r / 'sdk/build-tools/1/aapt2';p.parent.mkdir(parents=True)
        p.write_text('#!/bin/bash\necho "sdkVersion:\'' + str(n) + '\'"\n');p.chmod(0o755)
        return self.run_cmd(['bash', 'src/build/check_sdk.sh', 'fixture.apk', '29'], {'ANDROID_HOME': str(self.r / 'sdk')})

    def test_sdk_supported(self):
        self.assertEqual(self.sdk(29).returncode, 0)

    def test_sdk_excessive(self):
        self.assertNotEqual(self.sdk(30).returncode, 0)

    def sdk_readers(self, badging='', xmltree='', analyzer=None, badging_rc=0,
                    xmltree_rc=0, analyzer_rc=0, ceiling='29',
                    py_min=None, py_rc=0, apk='fixture.apk'):
        self.stub('pip', 'exit 1')
        # Block network/install fallback while leaving the actual strict reader intact.
        self.stub('python3', 'if [ "$1" = "-c" ]; then exit 1; fi\nexec ' +
                  shlex.quote(sys.executable) + ' "$@"')
        if py_min is not None:
            self.stub('python3', 'exec ' + shlex.quote(sys.executable) + ' "$@"')
            self.put('pyaxmlparser.py',
                     "from pathlib import Path\nclass APK:\n"
                     " def __init__(self, path): Path('received-apk.txt').write_text(path)\n"
                     " def get_min_sdk_version(self):\n" +
                     ("  print(" + repr(py_min) + "); raise SystemExit(" + str(py_rc) + ")\n"
                      if py_rc else "  return " + repr(py_min) + "\n"))
        p = self.r / 'sdk/build-tools/35.0.0/aapt2'
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('#!/bin/bash\ncase "$2" in\nbadging) printf %s ' +
                     shlex.quote(badging) + '; exit ' + str(badging_rc) +
                     ';;\nxmltree) printf %s ' + shlex.quote(xmltree) +
                     '; exit ' + str(xmltree_rc) + ';;\nesac\nexit 99\n')
        p.chmod(0o755)
        if analyzer is not None:
            a = self.r / 'sdk/tools/bin/apkanalyzer'
            a.parent.mkdir(parents=True, exist_ok=True)
            a.write_text('#!/bin/bash\nprintf %s ' + shlex.quote(analyzer) +
                         '\nexit ' + str(analyzer_rc) + '\n')
            a.chmod(0o755)
        return self.run_cmd(['bash', 'src/build/check_sdk.sh', apk, ceiling],
                            {**self.env(), 'ANDROID_HOME': str(self.r / 'sdk')})

    def test_sdk_google35_observed_label(self):
        # Captured aapt2 35.0.0 output for PotHelper 1.1.1, not a guessed label.
        text = ("package: name='app.morphe.pot.helper' versionCode='100100199' "
                "versionName='1.1.1' platformBuildVersionName='15' "
                "platformBuildVersionCode='35' compileSdkVersion='35' "
                "compileSdkVersionCodename='15'\nminSdkVersion:'26'\n"
                "targetSdkVersion:'35'\napplication-label:'PotHelper'\n")
        result = self.sdk_readers(text)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('minSdkVersion=26 ceiling=29', result.stdout)

    def test_sdk_modern_excessive_and_invalid_ceiling(self):
        for ceiling in ('29', 'invalid', '0', '-1', '29x', '29\n30'):
            with self.subTest(ceiling=ceiling):
                result = self.sdk_readers("minSdkVersion:'30'\n", ceiling=ceiling)
                self.assertNotEqual(result.returncode, 0)

    def test_sdk_duplicate_conflict_or_malformed_never_uses_fallback(self):
        for text in ("sdkVersion:'26'\nsdkVersion:'26'\n",
                     "sdkVersion:'26'\nminSdkVersion:'26'\n",
                     "sdkVersion:'26'\nminSdkVersion:'35'\n",
                     "minSdkVersion:'26junk'\n", "minSdkVersion:'0'\n",
                     "minSdkVersion:'Preview'\n", "sdkVersion:'26' trailing\n",
                     "sdkVersion:'26'\nminSdkVersion:bad\n"):
            with self.subTest(text=text):
                result = self.sdk_readers(text, analyzer='26\n')
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('read via apkanalyzer', result.stdout)

    def test_sdk_target_compile_only_are_not_minimum(self):
        result = self.sdk_readers("targetSdkVersion:'26'\ncompileSdkVersion:'26'\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('all four readers failed', result.stdout)

    def test_sdk_nonzero_badging_stdout_is_not_accepted(self):
        result = self.sdk_readers("sdkVersion:'26'\n", badging_rc=7)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('stdout ignored', result.stdout)

    def test_sdk_xmltree_fallback_and_nonzero_rejection(self):
        text = "    A: android:minSdkVersion(0x0101020c)=(type 0x10)0x1a\n"
        result = self.sdk_readers('', xmltree=text)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('read via xmltree', result.stdout)
        self.assertNotEqual(self.sdk_readers('', xmltree=text, xmltree_rc=8).returncode, 0)
        self.assertNotEqual(self.sdk_readers('', xmltree=text + text, analyzer='26').returncode, 0)
        excessive = text.replace('0x1a', '0x23')
        self.assertNotEqual(self.sdk_readers('', xmltree=excessive).returncode, 0)

    def test_sdk_apkanalyzer_fallback_and_strict_output(self):
        result = self.sdk_readers('', analyzer='26\n')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('read via apkanalyzer', result.stdout)
        for text in ('26junk', '26\n26\n', '0', '35'):
            self.assertNotEqual(self.sdk_readers('', analyzer=text).returncode, 0)
        self.assertNotEqual(self.sdk_readers('', analyzer='26', analyzer_rc=9).returncode, 0)

    def test_sdk_failed_badging_can_use_successful_independent_reader(self):
        result = self.sdk_readers("sdkVersion:'26'\n", badging_rc=7, analyzer='30')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('minSdkVersion=30 ceiling=29', result.stdout)

    def test_sdk_python_fallback_and_literal_apk_path(self):
        apk = "a quote' and spaces.apk"
        result = self.sdk_readers(py_min='26', apk=apk)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('read via pyaxmlparser', result.stdout)
        self.assertEqual((self.r/'received-apk.txt').read_text(), apk)

    def test_sdk_python_fallback_rejects_invalid_and_nonzero(self):
        for value in ('26junk', '26\n26\n', '0', '35', ''):
            with self.subTest(value=value):
                self.assertNotEqual(self.sdk_readers(py_min=value).returncode, 0)
        self.assertNotEqual(self.sdk_readers(py_min='26', py_rc=7).returncode, 0)

    def test_sdk_xmltree_invalid_zero_rejects_without_apkanalyzer_fallback(self):
        p = self.r / 'sdk/build-tools/1/aapt2';p.parent.mkdir(parents=True)
        p.write_text('#!/bin/bash\nif [ "$2" = badging ];then exit 1;fi\necho "  A: android:minSdkVersion(0x01010272)=(type 0x10)0x0"\n');p.chmod(0o755)
        x = self.run_cmd(['bash', 'src/build/check_sdk.sh', 'fixture.apk', '29'], {'ANDROID_HOME': str(self.r / 'sdk')})
        self.assertNotEqual(x.returncode, 0, x.stdout)
        self.assertNotIn('read via apkanalyzer', x.stdout)

    def test_poll_unknown_provider(self):
        self.stub('curl', 'echo \'{"message":"API rate limit exceeded"}\'')
        x = self.run_cmd(['bash', 'src/etc/poll.sh', 'youtube'], {**self.env(), 'repository': 'fixture/repo', 'GITHUB_OUTPUT': str(self.r / 'out')})
        self.assertEqual(x.returncode, 2, x.stdout)
        self.assertNotIn('new_patch=0', (self.r / 'out').read_text())

    def test_poll_unreadable_release_inventory(self):
        self.stub('curl', '''case "$*" in *fixture/repo*) echo '{"message":"rate limit"}' ;; *) echo '[{"assets":[{"name":"a.mpp","updated_at":"2026-09-01T00:00:00Z"}]}]' ;; esac''')
        x = self.run_cmd(['bash', 'src/etc/poll.sh', 'youtube'], {**self.env(), 'repository': 'fixture/repo', 'GITHUB_OUTPUT': str(self.r / 'out')})
        self.assertEqual(x.returncode, 2, x.stdout)

    def test_discovery_scope(self):
        x = self.run_cmd([sys.executable, 'src/etc/community_discover.py'])
        self.assertEqual(x.returncode, 0, x.stderr)
        for target in ('hotstar', 'photos', 'esfile'):
            block = x.stdout.split('\n' + target, 1)[1].split('\n\n', 1)[0]
            self.assertIn('you have 1 wired', block)
            self.assertIn('MISSING', block)
        for target in ('truecaller-combo', 'mxplayer'):
            block = x.stdout.split('\n' + target, 1)[1].split('\n\n', 1)[0]
            self.assertNotIn('MISSING  Paresh-Maheshwari', block)

    def test_writer_moves_both_sides(self):
        self.decide([('esfile-ftl', 'Remove Ads Ultra Lite', 'IN', False)])
        inc = (self.r / 'src/patches/esfile-ftl/include-patches').read_text()
        exc = (self.r / 'src/patches/esfile-ftl/exclude-patches').read_text()
        self.assertIn('Remove Ads Ultra Lite\n', inc);self.assertNotIn('Remove Ads Ultra Lite', exc)

    def test_writer_out_removes_include(self):
        self.decide([('esfile-ftl', 'Remove Ads', 'OUT', False)])
        self.assertNotIn('Remove Ads\n', (self.r / 'src/patches/esfile-ftl/include-patches').read_text())

    def test_writer_question_preserves(self):
        old = self.snapshot();self.decide([('esfile-ftl', 'Remove Ads', '?', False)])
        self.assertEqual(old, self.snapshot())

    def test_writer_absent_preserves(self):
        old = (self.r / 'src/patches/esfile-ftl/include-patches').read_text()
        self.decide([('esfile-ftl', 'A new explicit name', 'IN', False)])
        for s in old.splitlines():
            self.assertIn(s, (self.r / 'src/patches/esfile-ftl/include-patches').read_text().splitlines())

    def test_writer_roundtrip(self):
        rows = []
        targets = json.loads((self.r / 'src/targets.json').read_text())
        seen = set()
        for t in targets:
            for b in t['candidates'] + t.get('extra_bundles', []):
                d = b['patch_dir']
                if d in seen:
                    continue
                seen.add(d)
                for side, dec in [('include', 'IN'), ('exclude', 'OUT')]:
                    rows += [(d, s, dec, False) for s in (self.r / 'src/patches' / d / (side + '-patches')).read_text().splitlines() if s]
        old = self.snapshot();self.assertEqual(self.decide(rows), 0);self.assertEqual(old, self.snapshot())

    def test_writer_banned_rejected_without_writes(self):
        old = self.snapshot()
        with self.assertRaises(ValueError):
            self.decide([('esfile-ftl', 'Fixture first', 'IN', False), ('reddit-adobo', 'Spoof signature verification', 'IN', False)])
        self.assertEqual(old, self.snapshot())

    def test_writer_quarantine_rejected(self):
        with self.assertRaises(ValueError):
            self.decide([('esfile-ftl', 'Remove Debug Info', 'IN', False)])

    def test_writer_empty_exclusive_rejected(self):
        with self.assertRaises(ValueError):
            self.decide([('keymapper-lain', 'Unlock Premium', 'OUT', False)])

    def test_writer_stale_bundle_rejected(self):
        with self.assertRaises(ValueError):
            self.decide([('../escape', 'patch', 'IN', False)])

    def test_writer_exception_preserved(self):
        self.assertEqual(self.decide([('gg-photos', 'Change package name', 'IN', False)]), 0)

    def test_writer_failed_replace_rolls_back(self):
        old = self.snapshot();real = writer.os.replace;count = [0]
        def replace(*args):
            count[0] += 1
            if count[0] == 2:
                raise OSError('fixture')
            return real(*args)
        with patch.object(writer.os, 'replace', replace):
            with self.assertRaises(OSError):
                self.decide([('esfile-ftl', 'Remove Ads Ultra Lite', 'IN', False)])
        self.assertEqual(old, self.snapshot())

    def test_writer_legacy_full_entrypoint(self):
        self.put('docs/review/PATCHES.tsv', 'IN\tout\tesfile\tesfile-ftl\tRemove Ads Ultra Lite\toff\t-\tEXCL\tfixture\n')
        x = self.run_cmd([sys.executable, 'src/etc/review_full_apply.py'])
        self.assertEqual(x.returncode, 0, x.stderr)
        self.assertNotIn('Remove Ads Ultra Lite', (self.r / 'src/patches/esfile-ftl/exclude-patches').read_text())

    def test_writer_legacy_unreviewed_banned(self):
        self.put('docs/review/UNREVIEWED.tsv', 'INCLUDE\tesfile\tesfile-ftl\tSpoof signature\n')
        self.assertNotEqual(self.run_cmd([sys.executable, 'src/etc/review_apply.py']).returncode, 0)

    def test_output_valid_shape(self):
        self.make_apk()
        with contextlib.redirect_stdout(io.StringIO()):
            output.verify(self.r)

    def test_output_text_rejected(self):
        self.put('release/fixture-arm64-v8a.apk', 'not an APK' * 120000)
        with self.assertRaises(zipfile.BadZipFile):
            output.verify(self.r)

    def test_output_missing_manifest(self):
        self.make_apk(manifest=False)
        with self.assertRaises(ValueError):
            output.verify(self.r)

    def test_output_multiple_rejected(self):
        self.make_apk();self.make_apk('second-arm64-v8a.apk')
        with self.assertRaises(ValueError):
            output.verify(self.r)

    def prepare_bundles(self, t, c):
        for p in list(self.r.glob('*.mpp')) + list((self.r / 'extra').glob('*.mpp')):
            p.unlink()
        entries = [(f'{i+1:02d}-' + b['name'] + '.mpp') for i, b in enumerate(t.get('extra_bundles', []))] + ['09-' + c['name'] + '.mpp']
        for i, name in enumerate(sorted(entries)):
            self.put(('' if i == 0 else 'extra/') + name, 'fixture')
        self.put('morphe-desktop-fixture.jar', 'fixture')
        x = self.run_cmd(['bash', 'src/build/selections.sh', t['id'], c['name']])
        self.assertEqual(x.returncode, 0, x.stderr)
        return x.stdout

    def test_resource_reduction_explicitly_disabled_both_ftl_bundles(self):
        removed=['APK Junk Cleanup','Remove Duplicate Graphics','Remove Languages']
        for directory in ('esfile-ftl','mxplayer-ftl'):
            with self.subTest(directory=directory):
                inc=(self.r/'src/patches'/directory/'include-patches').read_text().splitlines()
                exc=(self.r/'src/patches'/directory/'exclude-patches').read_text().splitlines()
                self.assertTrue(inc)
                for name in removed:
                    self.assertNotIn(name,inc)
                    self.assertEqual(exc.count(name),1)
                self.assertIn('Remove Debug Info',exc)

    def test_resource_exclusions_bind_to_ftl_in_actual_argv(self):
        targets=json.loads((self.r/'src/targets.json').read_text())
        for ident in ('esfile','mxplayer'):
            t=next(t for t in targets if t['id']==ident)
            c=next(c for c in t['candidates'] if c['name']=='ftl')
            self.prepare_bundles(t,c)
            args=patcher.command(self.r,ident,'ftl',{'KEYSTORE_PASS':'fixture','KEYSTORE_ALIAS':'fixture'})
            scopes={};current=None;i=args.index('patch')+1
            while i<args.index('--options-file'):
                token=args[i]
                if token=='-p':
                    current=pathlib.Path(args[i+1]).stem.split('-',1)[1]
                    scopes[current]={'-e':[],'-d':[]};i+=2
                elif token in ('-e','-d'):
                    scopes[current][token].append(args[i+1]);i+=2
                else:i+=1
            for name in ('APK Junk Cleanup','Remove Duplicate Graphics','Remove Languages'):
                self.assertEqual(scopes['ftl']['-d'].count(name),1)
                self.assertNotIn(name,scopes['ftl']['-e'])
            self.assertIn('Remove Ads',scopes['ftl']['-e'])
            self.assertIn('Remove Debug Info',scopes['ftl']['-d'])
            if ident=='mxplayer':
                self.assertEqual(scopes['paresh']['-e'],['MX Player Pro License'])
                self.assertNotIn('Remove Languages',scopes['paresh']['-d'])
            ledger=(self.r/'.requested').read_text()
            self.assertNotIn('ftl\tRemove Languages',ledger)

    def test_resource_decision_does_not_change_options_or_target_limits(self):
        self.assertEqual((self.r/'src/options/ftl.json').read_text().strip(),'[]')
        targets=json.loads((self.r/'src/targets.json').read_text())
        mx=next(t for t in targets if t['id']=='mxplayer')
        self.assertEqual(mx['max_app_version'],'1.93.4')
        self.assertEqual(mx['min_sdk_ceiling'],29)
        self.assertFalse(mx['any_version'])
        self.assertEqual(mx['extra_bundles'][0]['patch_dir'],'mxplayer-paresh')


    def test_safe_argv_all_current_targets(self):
        targets = json.loads((self.r / 'src/targets.json').read_text())
        for t in targets:
            for c in t['candidates']:
                with self.subTest(target=t['id'], candidate=c['name']):
                    text = self.prepare_bundles(t, c)
                    args = patcher.command(self.r, t['id'], c['name'], {'KEYSTORE_PASS': 'dummy', 'KEYSTORE_ALIAS': 'fixture'})
                    sel = text.split('SEL=', 1)[1].strip()
                    first = sorted(self.r.glob('*.mpp'))[0]
                    old = ['-p', str(first)] + (['--exclusive'] if t.get('exclusive') else []) + shlex.split(sel)
                    got = args[args.index('patch')+1:args.index('--options-file')]
                    def norm(s):
                        return s.removeprefix(str(self.r) + '/').removeprefix('./')
                    self.assertEqual(list(map(norm, old)), list(map(norm, got)))

    def test_safe_argv_literal_shell_metacharacters(self):
        targets = json.loads((self.r / 'src/targets.json').read_text());t = next(t for t in targets if t['id'] == 'keymapper');c = t['candidates'][0]
        evil = '$(touch QUOTING_PROOF) "quoted"'
        self.put('src/patches/keymapper-lain/include-patches', evil + '\n')
        self.prepare_bundles(t, c)
        args = patcher.command(self.r, t['id'], c['name'], {'KEYSTORE_PASS': 'dummy password;$test', 'KEYSTORE_ALIAS': 'fixture'})
        self.assertIn(evil, args);self.assertIn('--keystore-password=dummy password;$test', args)
        self.assertFalse((self.r / 'QUOTING_PROOF').exists())

    def test_build_rejects_patcher_failure_after_applied(self):
        self.build_tail(42, 'Applied: Fixture patch')

    def test_build_rejects_zero_applied(self):
        self.build_tail(0, '')

    def test_build_tail_happy_path(self):
        self.make_apk()
        source = (ROOT / 'src/build/build.sh').read_text()
        tail = source[source.index('# --- 6. patch,'):]
        self.put('.requested', 'fixture\tFixture patch\n')
        setup = '''set -uo pipefail
green_log(){ echo "$1"; }; red_log(){ echo "$1"; }; yellow_log(){ echo "$1"; }
python3(){ if [ "$1" = src/build/patch_target.py ]; then echo 'Filtering patches for com.fixture'; echo 'Applied: Fixture patch'; return 0; elif [ "${2:-}" = input-version ]; then echo 1.0; else command python3 "$@"; fi; }
apkanalyzer(){ echo 1.0; }
export GITHUB_RUN_ID=12345 GITHUB_RUN_ATTEMPT=1
APK_NAME=fixture; OPTS=fixture; PKG=com.fixture; EXCL=true; WANT_E=1; version=1.0; PREFIX=fixture; WINNER=fixture; ID=fixture
excludePatches=""; includePatches=""
'''
        x = self.run_cmd(['bash', '-c', setup + tail])
        self.assertEqual(x.returncode, 0, x.stdout + x.stderr)
        self.assertIn('1 APK(s) built', x.stdout)

    def test_policy_failure_is_preflight_failure(self):
        self.put('src/patches/keymapper-lain/include-patches', 'Spoof signature verification\n')
        x = self.run_cmd([sys.executable, 'src/etc/preflight.py', 'keymapper'])
        self.assertNotEqual(x.returncode, 0)

    def build_tail(self, rc, applied):
        source = (ROOT / 'src/build/build.sh').read_text()
        tail = source[source.index('# --- 6. patch,'):]
        self.put('.requested', 'fixture\tFixture patch\n')
        setup = '''set -uo pipefail
green_log(){ echo "$1"; }; red_log(){ echo "$1"; }; yellow_log(){ echo "$1"; }
python3(){ if [ "$1" = src/build/patch_target.py ]; then echo 'Filtering patches for com.fixture'; echo '%s'; return %d; else command python3 "$@"; fi; }
APK_NAME=fixture; OPTS=fixture; PKG=com.fixture; EXCL=true; WANT_E=1; version=1.0; PREFIX=fixture; WINNER=fixture; ID=fixture
excludePatches=""; includePatches=""
''' % (applied, rc)
        x = self.run_cmd(['bash', '-c', setup + tail])
        self.assertNotEqual(x.returncode, 0, x.stdout)
        self.assertNotIn('APK(s) built', x.stdout)

    def test_obtainium_deterministic_check(self):
        x = self.run_cmd([sys.executable, 'src/etc/obtainium.py', '--check'])
        self.assertEqual(x.returncode, 0, x.stdout + x.stderr)

    def test_obtainium_detects_drift(self):
        self.put('docs/obtainium.json', '{}')
        self.assertNotEqual(self.run_cmd([sys.executable, 'src/etc/obtainium.py', '--check']).returncode, 0)

    def test_workflow_guards_exist(self):
        manual = (ROOT / '.github/workflows/manual-patch.yml').read_text()
        self.assertIn("&& inputs.publish && github.ref == 'refs/heads/main'", manual)
        self.assertIn('cancel-in-progress: false', manual)
        val = (ROOT / '.github/workflows/validate.yml').read_text()
        self.assertIn('  pull_request:', val)
        self.assertIn('contents: read', val)
        self.assertIn('run: python3 src/etc/daily_plan.py',
                      (ROOT / '.github/workflows/ci.yml').read_text())
        batch = (ROOT / '.github/workflows/batch-patch.yml').read_text()
        self.assertIn('publish: ${{ inputs.publish }}', batch)

    def test_shell_python_parse(self):
        for p in (ROOT / 'src').rglob('*.py'):
            ast.parse(p.read_text())
        for p in list((ROOT / 'src/build').glob('*.sh')) + list((ROOT / 'src/etc').glob('*.sh')):
            x = self.run_cmd(['bash', '-n', str(p)])
            self.assertEqual(x.returncode, 0, x.stderr)


class PageAssetVersionTests(unittest.TestCase):
    def fixture(self):
        import tempfile, shutil
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = pathlib.Path(folder.name)
        for name in ('docs/index.html', 'docs/portal.js', 'src/targets.json', 'src/etc/pagegen.py'):
            p = root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, p)
        return root

    def check(self, root, *args):
        return subprocess.run([sys.executable, 'src/etc/pagegen.py', *args], cwd=root, capture_output=True)

    def test_current_script_digest_and_noop(self):
        import hashlib
        root = self.fixture()
        before = (root / 'docs/index.html').read_bytes()
        self.assertIn(('portal.js?v=' + hashlib.sha256((root / 'docs/portal.js').read_bytes()).hexdigest()).encode(), before)
        self.assertEqual(self.check(root, '--check').returncode, 0)
        self.assertEqual(self.check(root).returncode, 0)
        self.assertEqual((root / 'docs/index.html').read_bytes(), before)

    def test_script_mutation_requires_new_version_and_revert_restores(self):
        root = self.fixture()
        script = root / 'docs/portal.js'
        original = script.read_bytes()
        page = (root / 'docs/index.html').read_bytes()
        script.write_bytes(original + b'\n/* mutation */\n')
        self.assertEqual(self.check(root, '--check').returncode, 1)
        self.assertEqual((root / 'docs/index.html').read_bytes(), page)
        self.assertEqual(self.check(root).returncode, 0)
        self.assertNotEqual((root / 'docs/index.html').read_bytes(), page)
        self.assertEqual(self.check(root, '--check').returncode, 0)
        script.write_bytes(original)
        self.assertEqual(self.check(root).returncode, 0)
        self.assertEqual((root / 'docs/index.html').read_bytes(), page)

    def test_missing_duplicate_unknown_script_tags_refuse_before_write(self):
        for replacement in ('', '<script src="portal.js" defer></script>' * 2, '<script src="portal.js?v=wrong" defer></script>'):
            root = self.fixture()
            p = root / 'docs/index.html'
            text = p.read_text()
            import re
            text = re.sub(r'<script src="portal\.js\?v=[0-9a-f]{64}" defer></script>', replacement, text)
            p.write_text(text)
            before = p.read_bytes()
            self.assertEqual(self.check(root).returncode, 4)
            self.assertEqual(p.read_bytes(), before)

    def test_empty_script_refuses_and_catalog_mutation_still_detected(self):
        root = self.fixture()
        page = (root / 'docs/index.html').read_bytes()
        (root / 'docs/portal.js').write_bytes(b'')
        self.assertEqual(self.check(root).returncode, 4)
        self.assertEqual((root / 'docs/index.html').read_bytes(), page)
        root = self.fixture()
        targets = root / 'src/targets.json'
        data = json.loads(targets.read_text())
        data[0]['label'] = 'Changed label'
        targets.write_text(json.dumps(data))
        self.assertEqual(self.check(root, '--check').returncode, 1)

def load_tests(loader, tests, pattern):
    import nightly_contracts
    import daily_plan_contracts
    import reddit_probe_contracts
    import operational_docs_contracts
    tests.addTests(loader.loadTestsFromTestCase(nightly_contracts.Nightly))
    tests.addTests(loader.loadTestsFromTestCase(daily_plan_contracts.DailyPlanTests))
    tests.addTests(loader.loadTestsFromTestCase(reddit_probe_contracts.RedditProbe))
    tests.addTests(loader.loadTestsFromTestCase(operational_docs_contracts.OperationalDocs))
    return tests


if __name__ == '__main__':
    unittest.main()
