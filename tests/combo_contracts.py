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
            log = b'Detected version 26.36.1\n' * 20 + b'TRANSFER_FAILED store=apkmirror try=1\n'
            mod.clues('batch', log)
            self.assertEqual([l for l in mod.lines if l.startswith('CLUE')], ['CLUE batch: TRANSFER_FAILED store=apkmirror try=1'])

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
