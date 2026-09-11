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

    def session_functions(self):
        source=(ROOT/'src/build/utils.sh').read_text()
        helpers=source[source.index('_fs_session_start() {'):source.index('\n_cfb_get() {')]
        wrapper=source[source.index('get_apk() {'):source.index('\n_get_apk_impl() {')]
        return helpers+'\n'+wrapper

    def session_probe(self, scenario, inner):
        # Real shell helpers, real jq and a synthetic FlareSolverr HTTP boundary.
        self.put('mock_fs.py', """
import json,os,sys
args=sys.argv[1:]
d=json.loads(args[args.index('-d')+1])
with open('fs-calls.jsonl','a') as f:f.write(json.dumps(d)+'\\n')
s=os.environ['FS_CASE'];cmd=d['cmd']
if cmd=='sessions.create':
 if s=='create_http_fail':sys.exit(22)
 if s=='bad_json':print('not-json');sys.exit(0)
 if s=='bad_id':print(json.dumps({'status':'ok','session':'bad/id'}));sys.exit(0)
 print(json.dumps({'status':'ok','session':'fixture-session'}))
elif cmd=='sessions.destroy':
 if s=='destroy_fail':sys.exit(22)
 print(json.dumps({'status':'ok'}))
elif cmd=='request.get':
 print(json.dumps({'status':'ok','solution':{'url':d['url'],'response':'HTML',
                   'status':200,'cookies':[{'name':'example','value':'COOKIE_SECRET'}],
                   'userAgent':'UA'}}))
else:sys.exit(99)
""")
        command="""
curl(){ python3 mock_fs.py "$@"; }
green_log(){ printf '%s\\n' "$*"; }
yellow_log(){ printf '%s\\n' "$*"; }
red_log(){ printf '%s\\n' "$*"; }
""" + self.session_functions()+"""
_get_apk_impl(){
""" + inner + """
}
version=ORIGINAL
get_apk com.fixture fixture apk
rc=$?
printf 'RESULT=%s VERSION=%s SESSION_AFTER=%s\\n' "$rc" "$version" "${_PF_FS_SESSION-absent}"
exit "$rc"
"""
        result=self.run_cmd(['bash','-c',command],{'FS_CASE':scenario})
        calls=[json.loads(x) for x in (self.r/'fs-calls.jsonl').read_text().splitlines()]
        return result,calls

    def test_persistent_session_reused_across_pages_and_closed(self):
        r,calls=self.session_probe('success',"""
_fs_get 'https://www.apkmirror.com/page?a=FAKE' || return 7
_fs_get 'https://www.apkmirror.com/next?a=FAKE' || return 8
version=CHANGED
return 0
""")
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual([x['cmd'] for x in calls],
                         ['sessions.create','request.get','request.get','sessions.destroy'])
        self.assertTrue(all(x['session']=='fixture-session' for x in calls[1:]))
        self.assertIn('VERSION=CHANGED SESSION_AFTER=absent',r.stdout)
        self.assertNotIn('fixture-session',r.stdout+r.stderr)
        self.assertNotIn('COOKIE_SECRET',r.stdout+r.stderr)

    def test_session_cleanup_preserves_download_failure_status(self):
        r,calls=self.session_probe('success','return 17')
        self.assertEqual(r.returncode,17)
        self.assertEqual([x['cmd'] for x in calls],['sessions.create','sessions.destroy'])

    def test_session_cleanup_failure_not_false_download_failure(self):
        r,calls=self.session_probe('destroy_fail','version=CHANGED; return 0')
        self.assertEqual(r.returncode,0)
        self.assertIn('cleanup unavailable',r.stdout)
        self.assertEqual(calls[-1]['cmd'],'sessions.destroy')

    def test_session_creation_failure_stops_before_navigation(self):
        for case in ('create_http_fail','bad_json','bad_id'):
            with self.subTest(case=case):
                path=self.r/'fs-calls.jsonl'
                if path.exists():path.unlink()
                r,calls=self.session_probe(case,'echo SHOULD_NOT_RUN; return 0')
                self.assertNotEqual(r.returncode,0)
                self.assertEqual([x['cmd'] for x in calls],['sessions.create'])
                self.assertNotIn('SHOULD_NOT_RUN',r.stdout)

    def test_session_scope_does_not_clobber_caller_state(self):
        source=self.session_functions()
        script="""
green_log(){ :; }; yellow_log(){ :; }; red_log(){ :; }
""" + source + """
_fs_session_start(){ _PF_FS_SESSION=owned; }
_fs_session_close(){ test "$_PF_FS_SESSION" = owned || return 9; _PF_FS_SESSION=; }
_get_apk_impl(){ test "$_FFS_FAILED" = 0 || return 8; version=CHANGED; }
_PF_FS_SESSION=caller-session
_FFS_FAILED=7
version=OLD
get_apk fixture fixture apk || exit 1
test "$_PF_FS_SESSION" = caller-session || exit 2
test "$_FFS_FAILED" = 7 || exit 3
test "$version" = CHANGED || exit 4
"""
        self.assertEqual(self.run_cmd(['bash','-c',script]).returncode,0)

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

    def test_session_change_does_not_touch_final_transfer_or_apkpure(self):
        source=(ROOT/'src/build/utils.sh').read_text()
        impl=source[source.index('_get_apk_impl() {'):source.index('\nget_apkpure() {')]
        self.assertIn('if ! wget -nv -O "./download/$base_apk"',impl)
        self.assertIn('"$base_url$final_href"; then',impl)
        pure=source[source.index('get_apkpure() {'):]
        self.assertNotIn('_PF_FS_SESSION',pure)

    def test_store_transfer_failures_never_claim_success(self):
        """Exercise the actual final-transfer blocks without sourcing network setup.
        Nonempty controls are transfer evidence only, not validated APKs.
        """
        source = (ROOT / 'src/build/utils.sh').read_text()
        for store, function, end_anchor in (
                ('APKMirror', 'get_apk()', '\n\tif [[ "$matched_type" == "BUNDLE" ]]'),
                ('APKPure', 'get_apkpure()', '\n\tif [[ "$pkg_type" == "bundle" ]]')):
            begin = source.index('\tif ! wget -nv -O "./download/$base_apk"', source.index(function))
            end = source.index(end_anchor, begin)
            block = source[begin:end]
            self.assertEqual(block.count('wget -nv'), 1)
            for rc, payload, expected in ((8, '', 1), (8, 'partial', 1),
                                          (0, '', 1), (0, 'fixture-transfer-bytes', 0)):
                with self.subTest(store=store, wget_exit=rc, bytes=len(payload)):
                    command = """
green_log(){ printf '%s\\n' "$*"; }
red_log(){ printf '%s\\n' "$*"; }
wget(){
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

    def test_store_failed_transfer_stops_before_conversion(self):
        source = (ROOT / 'src/build/utils.sh').read_text()
        for function in ('get_apk()', 'get_apkpure()'):
            start = source.index('\tif ! wget -nv',source.index(function))
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

    def test_handoff_diagnostic_does_not_change_wget_argv(self):
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
        self.assertEqual(args,['-nv','-O','./download/fixture.apk','--header=User-Agent: FAKE_UA',
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
        self.put('docs/obtainium-govind.json', '{}')
        self.assertNotEqual(self.run_cmd([sys.executable, 'src/etc/obtainium.py', '--check']).returncode, 0)

    def test_workflow_guards_exist(self):
        manual = (ROOT / '.github/workflows/manual-patch.yml').read_text()
        self.assertIn("&& inputs.publish && github.ref == 'refs/heads/main'", manual)
        self.assertIn('cancel-in-progress: false', manual)
        val = (ROOT / '.github/workflows/validate.yml').read_text()
        self.assertIn('  pull_request:', val)
        self.assertIn('contents: read', val)
        self.assertIn('POLL_ERRORS', (ROOT / '.github/workflows/ci.yml').read_text())
        batch = (ROOT / '.github/workflows/batch-patch.yml').read_text()
        self.assertIn('publish: ${{ inputs.publish }}', batch)

    def test_shell_python_parse(self):
        for p in (ROOT / 'src').rglob('*.py'):
            ast.parse(p.read_text())
        for p in list((ROOT / 'src/build').glob('*.sh')) + list((ROOT / 'src/etc').glob('*.sh')):
            x = self.run_cmd(['bash', '-n', str(p)])
            self.assertEqual(x.returncode, 0, x.stderr)


if __name__ == '__main__':
    unittest.main()
