"""W16q (27 Oct 2026): the one-file owner combo (docs/review/controllers/build_combo.py) runs the
read-only probe first, then the packet controller, streams both, and ends with one RESULT line."""
import fcntl, hashlib, importlib.util, json, os, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_combo', ROOT / 'docs/review/controllers/build_combo.py')
combo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(combo)

PROBE = "import sys\nprint('probe ran', flush=True)\nprint('RESULT %s. probe zip x.zip')\nsys.exit(%d)\n"
CTL = ("import pathlib, sys\nopen(str(pathlib.Path(__file__).with_name('ctl-ran')), 'a').write('x')\n"
       "print('RESULT %s. controller')\nsys.exit(%d)\n")


class Combo(unittest.TestCase):
    def make(self, home, probe_ok=True, ctl_ok=True):
        src = pathlib.Path(home) / 'src'
        src.mkdir()
        (src / 'pf-p2.py').write_text(PROBE % ('OK' if probe_ok else 'STOP', 0 if probe_ok else 1))
        body = CTL % ('OK' if ctl_ok else 'STOP', 0 if ctl_ok else 1)
        sha = hashlib.sha256(body.encode()).hexdigest()
        ctl = src / ('pf-w16q-%s.py' % sha[:8])
        ctl.write_text(body)
        text = combo.build(str(src / 'pf-p2.py'), str(ctl), 'w16q')
        out = pathlib.Path(home) / ('pf-w16q-combo-%s.py' % hashlib.sha256(text.encode()).hexdigest()[:8])
        out.write_text(text)
        return out, ctl.name

    def run_combo(self, out, home):
        env = dict(os.environ, PF_HOME=home, HOME=home)
        return subprocess.run([sys.executable, str(out)], capture_output=True, text=True, env=env, timeout=60)

    def test_probe_then_controller_then_one_result_and_self_removal(self):
        with tempfile.TemporaryDirectory() as home:
            out, ctl = self.make(home)
            r = self.run_combo(out, home)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertLess(r.stdout.index('probe ran'), r.stdout.index('step 2 of 2'))
            self.assertIn('COMBO probe: RESULT OK. probe zip x.zip', r.stdout)
            self.assertIn('COMBO packet: RESULT OK. controller', r.stdout)
            self.assertTrue(r.stdout.strip().splitlines()[-1].startswith('RESULT OK.'))
            self.assertFalse(out.exists())
            run = pathlib.Path(home) / 'work' / 'run-logs'
            self.assertFalse(list(run.glob('combo-probe-*')), 'the probe copy is removed')
            self.assertTrue((run / 'ctl-ran').exists())
            self.assertFalse(list(pathlib.Path(home).glob('pf-w16q-*.py')), 'nothing left in home')

    def test_a_stop_keeps_the_combo_and_the_controller_still_runs(self):
        with tempfile.TemporaryDirectory() as home:
            out, ctl = self.make(home, probe_ok=False)
            r = self.run_combo(out, home)
            self.assertEqual(r.returncode, 1)
            self.assertIn('COMBO probe: RESULT STOP', r.stdout)
            self.assertIn('COMBO packet: RESULT OK', r.stdout)
            self.assertTrue(r.stdout.strip().splitlines()[-1].startswith('RESULT STOP'))
            self.assertTrue(out.exists())

    def test_controller_stop_is_kept_for_a_rerun(self):
        with tempfile.TemporaryDirectory() as home:
            out, ctl = self.make(home, ctl_ok=False)
            r = self.run_combo(out, home)
            self.assertEqual(r.returncode, 1)
            self.assertTrue((pathlib.Path(home) / 'work' / 'run-logs' / ctl).exists())
            r2 = self.run_combo(out, home)
            self.assertEqual(r2.returncode, 1)
            self.assertEqual((pathlib.Path(home) / 'work' / 'run-logs' / 'ctl-ran').read_text(), 'xx')

    def test_tampered_payload_stops_before_anything_runs(self):
        with tempfile.TemporaryDirectory() as home:
            out, ctl = self.make(home)
            text = out.read_text()
            sha = text.split("PROBE_NAME, PROBE_SHA = 'pf-p2.py', '")[1][:64]
            out.write_text(text.replace(sha, '0' * 64))
            r = self.run_combo(out, home)
            self.assertNotEqual(r.returncode, 0)
            self.assertNotIn('probe ran', r.stdout)
            self.assertIn('does not match its sha256', r.stdout + r.stderr)

    def test_t1_findings_are_never_result_ok(self):
        # W16v review a126: a merged packet whose all-flows test listed findings ends RESULT FINDINGS.
        with tempfile.TemporaryDirectory() as home:
            src = pathlib.Path(home) / 'src'
            src.mkdir()
            (src / 'pf-p2.py').write_text(PROBE % ('OK', 0))
            body = "print('RESULT FINDINGS: merged #1, but the all-flows test listed 2 finding(s)')\n"
            ctl = src / ('pf-w16q-%s.py' % hashlib.sha256(body.encode()).hexdigest()[:8])
            ctl.write_text(body)
            text = combo.build(str(src / 'pf-p2.py'), str(ctl), 'w16q')
            out = pathlib.Path(home) / ('pf-w16q-combo-%s.py' % hashlib.sha256(text.encode()).hexdigest()[:8])
            out.write_text(text)
            r = self.run_combo(out, home)
            self.assertEqual(r.returncode, 0, r.stdout)
            last = r.stdout.strip().splitlines()[-1]
            self.assertTrue(last.startswith('RESULT FINDINGS'), last)
            self.assertNotIn('RESULT OK.', last)
            self.assertFalse(out.exists(), 'nothing to rerun after a merge')

    def test_controller_t1_findings_contract(self):
        src = (ROOT / 'docs/review/controllers/packet.tmpl.py').read_text()
        self.assertIn("R['result'] = 'FINDINGS' if t1n else 'OK'", src)
        self.assertIn("print('RESULT FINDINGS: merged #%s", src)
        self.assertIn("'FINDING' if found else 'OK'", src)

    def test_zero_exit_stop_is_not_combo_success(self):
        with tempfile.TemporaryDirectory() as home:
            src = pathlib.Path(home) / 'src'; src.mkdir()
            (src / 'pf-p2.py').write_text("print('RESULT STOP: probe', flush=True)\n")
            body = "print('RESULT OK: controller', flush=True)\n"
            sha = hashlib.sha256(body.encode()).hexdigest()
            ctl = src / ('pf-w16q-%s.py' % sha[:8]); ctl.write_text(body)
            text = combo.build(str(src / 'pf-p2.py'), str(ctl), 'w16q')
            out = pathlib.Path(home) / ('pf-w16q-combo-%s.py' % hashlib.sha256(text.encode()).hexdigest()[:8]); out.write_text(text)
            r = self.run_combo(out, home)
            self.assertEqual(r.returncode, 1)
            self.assertIn('RESULT STOP:', r.stdout)

    def test_controller_must_carry_its_final_name(self):
        with tempfile.TemporaryDirectory() as home:
            p = pathlib.Path(home) / 'pf-w16q.py'
            p.write_text('x')
            with self.assertRaises(SystemExit):
                combo.build(str(p), str(p), 'w16q')

    def test_a_second_combo_stops_while_the_first_holds_the_lock(self):
        with tempfile.TemporaryDirectory() as home:
            out, ctl = self.make(home)
            run = pathlib.Path(home) / 'work' / 'run-logs'
            run.mkdir(parents=True)
            with open(str(run / 'pf-w16q-combo.lock'), 'a') as held:
                fcntl.flock(held.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                r = self.run_combo(out, home)
            self.assertEqual(r.returncode, 1)
            self.assertNotIn('probe ran', r.stdout)
            self.assertTrue(r.stdout.strip().splitlines()[-1].startswith('RESULT STOP: another w16q combo'))
            self.assertTrue(out.exists())

    def test_a_setup_error_still_ends_in_one_result_line(self):
        with tempfile.TemporaryDirectory() as home:
            out, ctl = self.make(home)
            (pathlib.Path(home) / 'work').write_text('not a folder')
            r = self.run_combo(out, home)
            self.assertEqual(r.returncode, 1)
            self.assertNotIn('Traceback', r.stdout + r.stderr)
            self.assertTrue(r.stdout.strip().splitlines()[-1].startswith('RESULT STOP'))


P2 = ROOT / 'docs/review/controllers/owner-probes/pf-p2.py'


def load_p2(home):
    """Load the probe with its home in a temp folder; the environment is put back at once."""
    before = os.environ.get('PF_HOME')
    os.environ['PF_HOME'] = home
    try:
        spec2 = importlib.util.spec_from_file_location('pf_p2_under_test', P2)
        mod = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(mod)
    finally:
        if before is None:
            os.environ.pop('PF_HOME', None)
        else:
            os.environ['PF_HOME'] = before
    mod.OUT.mkdir(parents=True)
    return mod


class remote:
    """PF_REMOTE for one block; any earlier value comes back."""
    def __init__(self, path):
        self.path, self.before = str(path), os.environ.get('PF_REMOTE')

    def __enter__(self):
        os.environ['PF_REMOTE'] = self.path

    def __exit__(self, *exc):
        if self.before is None:
            os.environ.pop('PF_REMOTE', None)
        else:
            os.environ['PF_REMOTE'] = self.before


class ProbeP2(unittest.TestCase):
    def test_w16v_redaction_covers_token_forms_before_shortening(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('p2red', str(ROOT / 'docs/review/controllers/owner-probes/pf-p2.py'))
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        m.lines.clear()
        long = 'ERROR: FAILED token=' + 'A' * 400
        m.clues('x', ('ERROR: FAILED ghs_supersecret\nERROR: FAILED password=hunter2\n'
                      'ERROR: FAILED Authorization: Bearer abc.def\nERROR: FAILED https://u:pw@host/x\n' + long).encode())
        out = '\n'.join(m.lines)
        for secret in ('ghs_supersecret', 'hunter2', 'abc.def', 'u:pw@', 'AAAA'):
            self.assertNotIn(secret, out)
        for leak in ('api key=abc1', 'access key=abc2', 'private key=abc3',
                     '-----BEGIN RSA PRIVATE KEY-----\nLEAKEDKEY\n-----END RSA PRIVATE KEY-----',
                     '-----BEGIN PRIVATE KEY-----LEAKEDKEY-----END PRIVATE KEY-----'):
            cleaned = m.clean_text(leak, 300)
            self.assertNotIn('abc', cleaned); self.assertNotIn('LEAKEDKEY', cleaned)
        for keep in ('secrets: inherit', 'tokens: read', 'TRANSFER_FAILED store=apkmirror try=2 wget_exit=8',
                     'STORE_DOWNGRADE_REFUSED store=apkpure got=25.20.0 wanted=26.36.1'):
            self.assertEqual(m.clean_text(keep, 300), keep)
        import time
        m.lines.clear()
        start = time.time(); m.clues('x', ('TRANSFER_FAILED store=apkmirror ' + 'x' * (2 * 1024 * 1024)).encode())
        self.assertLess(time.time() - start, 5)
        self.assertIn('TRANSFER_FAILED store=apkmirror', m.lines[-1])
        self.assertEqual(m.loads(b'null', 'D'), 'D')
        self.assertEqual(m.loads(b'[]', 'D'), [])

    """W16q round 3: the probe pulls evidence, never test APKs, and names the cause lines."""

    def test_test_apks_and_big_artifacts_are_never_downloaded(self):
        with tempfile.TemporaryDirectory() as home:
            mod = load_p2(home)
            rows = [{'name': 'test-apk-mxplayer-1-1', 'size_in_bytes': 27317985, 'expired': False},
                    {'name': 'build-evidence-adguard', 'size_in_bytes': 35459, 'expired': False},
                    {'name': 'huge-evidence', 'size_in_bytes': 6 * 2**20, 'expired': False}]
            calls = []

            def fake(args, dest=None, timeout=900):
                calls.append(args)
                if args[0] == 'api':
                    self.assertIn('per_page=100', args[1])
                    return 0, json.dumps({'artifacts': rows}).encode()
                return 0, b''
            mod.gh = fake
            mod.artifacts('1', 'batch')
            downloads = [c[c.index('-n') + 1] for c in calls if c[:2] == ['run', 'download']]
            self.assertEqual(downloads, ['build-evidence-adguard'])
            self.assertTrue(any('huge-evidence' in l and 'not downloaded' in l for l in mod.lines))

    def test_cause_lines_are_printed_from_the_log(self):
        with tempfile.TemporaryDirectory() as home:
            mod = load_p2(home)
            log = b'noise\nbuild\tPatch apk\t2026 TRANSFER_FAILED store=apkmirror try=2 wget_exit=8 bytes=0\nmore noise\n'
            mod.clues('batch', log)
            self.assertEqual([l for l in mod.lines if l.startswith('CLUE')],
                             ['CLUE batch: build\tPatch apk\t2026 TRANSFER_FAILED store=apkmirror try=2 wget_exit=8 bytes=0'])

    def test_routine_lines_never_crowd_out_a_failure(self):
        with tempfile.TemporaryDirectory() as home:
            mod = load_p2(home)
            log = (b'Detected version 26.36.1\n' + b'DOWNLOAD_DIAGNOSTIC {"stage": "resolver"}\n') * 20 + b'TRANSFER_FAILED store=apkmirror try=1\n'
            mod.clues('batch', log)
            self.assertEqual([l for l in mod.lines if l.startswith('CLUE')], ['CLUE batch: TRANSFER_FAILED store=apkmirror try=1'])

    def test_the_patcher_error_reaches_the_screen(self):
        """W16q run: the Amazon Music cause was Morphe's abort line, not the store lines."""
        with tempfile.TemporaryDirectory() as home:
            mod = load_p2(home)
            mod.clues('batch', b'ERROR: Patching aborted: Patching failed: Patch "Skip ads" failed\n')
            self.assertEqual(len([l for l in mod.lines if l.startswith('CLUE') and 'Skip ads' in l]), 1)

    def test_status_json_is_read_from_the_status_branch(self):
        with tempfile.TemporaryDirectory() as home:
            mod = load_p2(home)
            self.assertEqual(mod.PAGES, 'https://raw.githubusercontent.com/govinda-rajulu/patch-factory/status/status.json')

    def test_icons_fake_curl_validates_magic_hosts_and_size(self):
        """Owner icon downloads never use the network in this contract test."""
        fake = """#!/usr/bin/env python3
import json, os, pathlib, struct, sys
target = sys.argv[sys.argv.index('--output') + 1]
pathlib.Path(os.environ['FAKE_CURL_LOG']).write_text(json.dumps(sys.argv))
mode = os.environ['FAKE_CURL_MODE']
if mode == 'png':
    data = b'\\x89PNG\\r\\n\\x1a\\n' + struct.pack('>I', 13) + b'IHDR' + struct.pack('>II', 3, 4) + b'\\x08\\x06\\x00\\x00\\x00'
elif mode == 'webp':
    data = b'RIFF' + struct.pack('<I', 22) + b'WEBPVP8X' + struct.pack('<I', 10) + b'\\x00\\x00\\x00\\x00\\x02\\x00\\x00\\x03\\x00\\x00'
elif mode == 'html':
    data = b'<html>error</html>'
elif mode == 'stream':
    data = b'\\x89PNG\\r\\n\\x1a\\n' + b'x' * (3 * 1024 * 1024)  # no Content-Length: --max-filesize cannot stop it
else:
    data = b'x' * (2 * 1024 * 1024 + 1)
if target == '-':
    sys.stdout.buffer.write(data)
else:
    pathlib.Path(target).write_bytes(data)
"""
        cases = (
            ('png', 'https://play-lh.googleusercontent.com/fake', 'png', 'PNG', 3, 4),
            ('webp', 'https://img.utdstc.com/fake', 'webp', 'WebP', 3, 4),
            ('html', 'https://play-lh.googleusercontent.com/fake', None, 'FAIL', None, None),
            ('oversize', 'https://play-lh.googleusercontent.com/fake', None, 'FAIL', None, None),
            ('stream', 'https://play-lh.googleusercontent.com/fake', None, 'FAIL', None, None),
        )
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            curl = td / 'curl'
            curl.write_text(fake)
            curl.chmod(0o755)
            before_path = os.environ.get('PATH', '')
            before_mode = os.environ.get('FAKE_CURL_MODE')
            before_log = os.environ.get('FAKE_CURL_LOG')
            try:
                os.environ['PATH'] = str(td) + os.pathsep + before_path
                os.environ['FAKE_CURL_LOG'] = str(td / 'curl-args')
                for mode, url, ext, marker, width, height in cases:
                    home = td / mode
                    home.mkdir()
                    mod = load_p2(str(home))
                    mod.ICON_SOURCES = [('fixture', url)]
                    os.environ['FAKE_CURL_MODE'] = mode
                    mod.icons()
                    data = json.loads((mod.OUT / 'icons' / 'icons.json').read_text())
                    if ext:
                        self.assertEqual(len(data), 1)
                        self.assertEqual((data[0]['format'], data[0]['width'], data[0]['height']),
                                         (marker, width, height))
                        self.assertEqual(len(data[0]['sha256']), 64)
                        self.assertEqual(mod.bad[0], 0)
                        self.assertTrue((mod.OUT / 'icons' / ('fixture.' + ext)).is_file())
                        self.assertTrue(any(x.startswith('OK icon fixture') for x in mod.lines))
                        args = json.loads((td / 'curl-args').read_text())
                        self.assertEqual(('=w240-h480' in args[-1]), 'play-lh.googleusercontent.com' in url)
                        self.assertIn('--max-filesize', args)
                    else:
                        self.assertEqual(data, [])
                        self.assertEqual(mod.bad[0], 0)
                        self.assertTrue(any(x.startswith('NOTE icon fixture FAIL:') for x in mod.lines))
            finally:
                if before_mode is None:
                    os.environ.pop('FAKE_CURL_MODE', None)
                else:
                    os.environ['FAKE_CURL_MODE'] = before_mode
                if before_log is None:
                    os.environ.pop('FAKE_CURL_LOG', None)
                else:
                    os.environ['FAKE_CURL_LOG'] = before_log
                os.environ['PATH'] = before_path

            # A disallowed host must be rejected before curl is even launched.
            home = td / 'wrong-host'
            home.mkdir()
            mod = load_p2(str(home))
            mod.ICON_SOURCES = [('fixture', 'https://evil.example/icon.png')]
            (td / 'curl-args').unlink(missing_ok=True)
            os.environ['FAKE_CURL_MODE'] = 'png'
            mod.icons()
            self.assertFalse((td / 'curl-args').exists())
            self.assertEqual(json.loads((mod.OUT / 'icons' / 'icons.json').read_text()), [])
            self.assertEqual(mod.bad[0], 0)
            self.assertTrue(any(x.startswith('NOTE icon fixture FAIL:') for x in mod.lines))

    def test_case_review_separates_issues_prs_and_redacts(self):
        with tempfile.TemporaryDirectory() as home:
            mod = load_p2(home)
            issue = {'number': 262, 'title': 'Fail', 'body': 'token=ghp_secret', 'state': 'open', 'comments': 1,
                     'updated_at': 'x', 'created_at': 'x', 'labels': [], 'user': {'login': 'bot', 'type': 'Bot'}, 'html_url': 'https://github.com/govinda-rajulu/patch-factory/issues/262'}
            pr = {'number': 264, 'title': 'PR', 'body': 'safe', 'state': 'open', 'draft': False, 'updated_at': 'x',
                  'base': {'ref': 'main', 'sha': 'a'}, 'head': {'ref': 'x', 'sha': 'b'}, 'user': {'login': 'me', 'type': 'User'}, 'html_url': 'https://github.com/govinda-rajulu/patch-factory/pull/264'}
            comment = {'id': 1, 'body': 'bearer ABC123', 'created_at': 'x', 'updated_at': 'x', 'user': {'login': 'me', 'type': 'User'}, 'html_url': 'https://github.com/c'}
            def fake(path, timeout=120):
                if '/issues?' in path: return 0, [issue]
                if '/pulls?' in path: return 0, [pr]
                if '/issues/262/comments' in path or '/issues/264/comments' in path: return 0, [comment]
                if '/actions/runs?' in path: return 0, {'workflow_runs': []}
                return 1, None
            mod.api_json = fake
            mod.case_review()
            data = json.loads((mod.OUT / 'case-review.json').read_text())
            self.assertEqual((len(data['issues']), len(data['pull_requests'])), (1, 1))
            self.assertIn('[REDACTED]', data['issues'][0]['body'])
            self.assertIn('[REDACTED]', data['issues'][0]['comments'][0]['body'])

    def test_zero_open_prs_are_complete_without_a_partial_note(self):
        with tempfile.TemporaryDirectory() as home:
            mod = load_p2(home)
            self.assertEqual(mod.loads(b'[]', None), [])

            def fake(path, timeout=120):
                if '/issues?' in path or '/pulls?' in path:
                    return 0, []
                if '/actions/runs?' in path:
                    return 0, {'workflow_runs': []}
                return 1, None

            mod.api_json = fake
            mod.case_review()
            data = json.loads((mod.OUT / 'case-review.json').read_text())
            self.assertEqual(data['pull_requests'], [])
            self.assertEqual(data['coverage']['errors'], [])
            self.assertFalse(any('case review partial' in line for line in mod.lines))

    def test_zero_comments_are_complete(self):
        with tempfile.TemporaryDirectory() as home:
            mod = load_p2(home)
            issue = {'number': 1, 'title': 'Issue', 'body': '', 'state': 'open', 'comments': 0,
                     'updated_at': 'x', 'created_at': 'x', 'labels': [], 'user': {'login': 'bot', 'type': 'Bot'}}
            pr = {'number': 2, 'title': 'PR', 'body': '', 'state': 'open', 'draft': False, 'updated_at': 'x',
                  'base': {'ref': 'main', 'sha': 'a'}, 'head': {'ref': 'x', 'sha': 'b'},
                  'user': {'login': 'me', 'type': 'User'}}

            def fake(path, timeout=120):
                if '/issues?' in path:
                    return 0, [issue]
                if '/pulls?' in path:
                    return 0, [pr]
                if '/issues/1/comments' in path or '/issues/2/comments' in path:
                    return 0, []
                if '/actions/runs?' in path:
                    return 0, {'workflow_runs': []}
                return 1, None

            mod.api_json = fake
            mod.case_review()
            data = json.loads((mod.OUT / 'case-review.json').read_text())
            self.assertTrue(data['issues'][0]['comments_complete'])
            self.assertTrue(data['pull_requests'][0]['comments_complete'])
            self.assertEqual(data['coverage']['errors'], [])

    def test_exact_full_page_then_empty_page_is_complete(self):
        with tempfile.TemporaryDirectory() as home:
            mod = load_p2(home)
            calls = []

            def fake(path, timeout=120):
                calls.append(path)
                page = path.rsplit('page=', 1)[1]
                return 0, ([{'n': n} for n in range(100)] if page == '1' else [])

            mod.api_json = fake
            code, rows, complete = mod.pages('repos/example/things')
            self.assertEqual((code, len(rows), complete), (0, 100, True))
            self.assertEqual(len(calls), 2)
            self.assertTrue(calls[0].endswith('per_page=100&page=1'))
            self.assertTrue(calls[1].endswith('per_page=100&page=2'))

    def test_unreadable_collection_is_reported_as_an_error(self):
        with tempfile.TemporaryDirectory() as home:
            mod = load_p2(home)

            def fake(path, timeout=120):
                if '/issues?' in path:
                    return 0, []
                if '/pulls?' in path:
                    return 0, None
                if '/actions/runs?' in path:
                    return 0, {'workflow_runs': []}
                return 1, None

            mod.api_json = fake
            mod.case_review()
            data = json.loads((mod.OUT / 'case-review.json').read_text())
            self.assertIn('open PRs unreadable', data['coverage']['errors'])
            self.assertTrue(any('case review partial' in line for line in mod.lines))

    def test_bundle_without_main_is_a_failure(self):
        with tempfile.TemporaryDirectory() as home:
            src = pathlib.Path(home) / 'src'
            subprocess.run(['git', 'init', '-q', '-b', 'other', str(src)], check=True)
            subprocess.run(['git', '-C', str(src), '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q',
                            '--allow-empty', '-m', 'x'], check=True)
            mod = load_p2(home)
            with remote(src):
                mod.git_bundle()
            self.assertEqual(mod.bad[0], 1, mod.lines)
            self.assertTrue(any('has no main ref' in l for l in mod.lines))

    def test_bundle_with_main_is_verified_and_names_its_sha(self):
        with tempfile.TemporaryDirectory() as home:
            src = pathlib.Path(home) / 'src'
            subprocess.run(['git', 'init', '-q', '-b', 'main', str(src)], check=True)
            subprocess.run(['git', '-C', str(src), '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q',
                            '--allow-empty', '-m', 'x'], check=True)
            sha = subprocess.run(['git', '-C', str(src), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
            mod = load_p2(home)
            with remote(src):
                mod.git_bundle()
            self.assertEqual(mod.bad[0], 0, mod.lines)
            self.assertTrue(any(l.startswith('OK bundle') and ('main %s,' % sha) in l for l in mod.lines), mod.lines)
            self.assertFalse((mod.OUT / 'clone').exists())
            subprocess.run(['git', '-C', str(src), 'branch', '-q', '-m', 'main'], check=True)


if __name__ == '__main__':
    unittest.main()
