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
