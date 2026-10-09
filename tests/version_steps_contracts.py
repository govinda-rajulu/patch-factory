"""Version step-down contracts (packet W7, owner design 9 Oct 2026).

Dynamic: the provider's newest version, or the store's newest when the provider lists none.
When the APK needs a newer Android than the cap, the build tries the next lower version, at
most three times. Fixed: the cap, max_app_version, exact version_code pins. No network.
"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEPS = (ROOT / 'src/build/version_steps.sh').read_text()
BUILD = (ROOT / 'src/build/build.sh').read_text()

LISTING = ('<h5 class="appRowTitle"><a class="fontBlack">Amazon Music 26.40.0</a></h5>'
           '<h5 class="appRowTitle"><a class="fontBlack">Amazon Music 26.39.1 beta</a></h5>'
           '<h5 class="appRowTitle"><a class="fontBlack">Amazon Music 26.38.0</a></h5>')


class Steps(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.r = Path(self.t.name)
        (self.r / 'src/build/helper').mkdir(parents=True)
        (self.r / 'src/build/helper/apps.json').write_text(json.dumps(
            {'apkmirror': {'com.amazon.mp3': {'list_url': 'https://www.apkmirror.com/uploads/?appcategory=amazon-music'}}}))
        (self.r / 'morphe-desktop-1.0.jar').write_text('jar')
        (self.r / '09-p.mpp').write_text('mpp')
        self.bin = self.r / 'bin'
        self.bin.mkdir()

    def java(self, out, rc=0):
        p = self.bin / 'java'
        p.write_text('#!/bin/bash\ncat <<\'X\'\n' + out + '\nX\nexit %d\n' % rc)
        p.chmod(0o755)

    def run_next(self, current, maxver='', pages=(LISTING, '')):
        page_files = []
        for i, page in enumerate(pages):
            f = self.r / ('page%d.html' % i)
            f.write_text(page)
            page_files.append(str(f))
        # _cf_get and pup stand in for utils.sh: page N of the listing, then a jq-shaped JSON.
        script = ('set -u; N=0; PAGES=(%s); _cf_get(){ html=$(cat "${PAGES[$N]}"); N=$((N+1)); echo "$1" >> urls; }\n'
                  'pup=./fakepup\nsource %s\npf_next_version com.amazon.mp3 "$1" "$2"\n') % (
                      ' '.join(page_files), ROOT / 'src/build/version_steps.sh')
        pup = self.r / 'fakepup'
        pup.write_text('#!/usr/bin/env python3\nimport sys,re,json\nh=sys.stdin.read()\n'
                       'print(json.dumps([{"text":t} for t in re.findall(r\'class="fontBlack">([^<]*)<\',h)]))\n')
        pup.chmod(0o755)
        env = {**os.environ, 'PATH': str(self.bin) + ':' + os.environ['PATH']}
        return subprocess.run(['bash', '-c', script, 'x', current, maxver], cwd=self.r, env=env,
                              capture_output=True, text=True)

    def test_provider_list_steps_to_the_next_lower_version(self):
        # 9 Oct: LinkedIn's provider lists 4.1.1255.1 and 4.1.1258; 4.1.1258 needs SDK 32.
        self.java('INFO header\n  4.1.1258 (11 patches)\n  4.1.1255.1 (11 patches)')
        x = self.run_next('4.1.1258')
        self.assertEqual((x.returncode, x.stdout.strip()), (0, '4.1.1255.1 provider'), x.stderr)

    def test_provider_list_has_nothing_lower(self):
        self.java('  4.1.1258 (11 patches)\n  4.1.1255.1 (11 patches)')
        self.assertEqual(self.run_next('4.1.1255.1').returncode, 1)

    def test_max_app_version_stays_a_hard_ceiling(self):
        self.java('  30 (2 patches)\n  20 (2 patches)\n  10 (2 patches)')
        self.assertEqual(self.run_next('30', maxver='15').stdout.strip(), '10 provider')

    def test_any_version_provider_steps_down_on_the_store_listing(self):
        self.java('Any (4 patches)')
        x = self.run_next('26.40.0')
        self.assertEqual((x.returncode, x.stdout.strip()), (0, '26.38.0 store'), x.stderr)
        urls = (self.r / 'urls').read_text().split()
        self.assertEqual(urls[1], 'https://www.apkmirror.com/uploads/page/2/?appcategory=amazon-music')

    def test_unreadable_lists_fail_closed(self):
        self.java('boom', rc=2)
        self.assertEqual(self.run_next('26.40.0').returncode, 2)
        self.java('Any (4 patches)')
        (self.r / 'src/build/helper/apps.json').write_text('{"apkmirror": {}}')
        self.assertEqual(self.run_next('26.40.0').returncode, 2)

    def test_two_bundles_in_cwd_refuse(self):
        self.java('  2 (1 patches)\n  1 (1 patches)')
        (self.r / '10-q.mpp').write_text('mpp')
        self.assertEqual(self.run_next('2').returncode, 2)

    def test_build_loop_keeps_the_fixed_rules(self):
        self.assertIn('PF_MAX_STEPS=3', STEPS)
        loop = BUILD[BUILD.index('STEP=0\nwhile :; do'):BUILD.index('python3 src/build/artifact_identity.py capture-inputs')]
        for phrase in ('if [ "$SDK_RC" -ne 3 ]; then', 'no step-down"; exit 1; fi',
                       'pins an exact version_code, so no step-down', 'if [ "$STEP" -ge "$PF_MAX_STEPS" ]',
                       'echo "::notice::VERSION_STEP_DOWN step=$STEP', 'RVER="${NEXT%% *}"; ANYVER=false', '# --- 4b.'):
            self.assertIn(phrase, loop)
        self.assertLess(BUILD.index('source ./src/build/version_steps.sh'), BUILD.index('STEP=0\nwhile :; do'))

    def test_check_sdk_says_above_cap_with_its_own_status(self):
        text = (ROOT / 'src/build/check_sdk.sh').read_text()
        self.assertIn('Set max_app_version in src/targets.json."\n  # Status 3', text)
        self.assertEqual(text.count('exit 3'), 1)


class AnyVersionResolve(unittest.TestCase):
    def resolve(self, java_out, maxver=None, candidates=('p',)):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        r = Path(t.name)
        (r / 'src').mkdir()
        (r / 'morphe-desktop-fixture.jar').write_text('fixture')
        cands = [{'name': n, 'owner': 'o', 'repo': n, 'channel': 'stable'} for n in candidates]
        (r / 'src/targets.json').write_text(json.dumps([{'id': 'amazonmusic', 'package': 'com.amazon.mp3',
                                                        'max_app_version': maxver, 'candidates': cands}]))
        b = r / 'bin'
        b.mkdir()
        (b / 'python3').write_text('#!/bin/bash\necho \'{"published_at":"2026-10-01T00:00:00Z","path":"\'$3\'.mpp","sha256":"\'$3\'","tag":"v1"}\'\n')
        (b / 'java').write_text('#!/bin/bash\ncase "$*" in\n' + java_out + '\nesac\n')
        for f in b.iterdir():
            f.chmod(0o755)
        return subprocess.run(['bash', str(ROOT / 'src/build/resolve.sh'), 'amazonmusic'], cwd=r,
                              env={**os.environ, 'PATH': str(b) + ':' + os.environ['PATH']}, capture_output=True, text=True)

    def test_any_version_provider_wins_with_the_store_newest(self):
        x = self.resolve('*) echo "Any (4 patches)";;')
        self.assertEqual(x.returncode, 0, x.stdout)
        self.assertIn("any app version, the store's newest", x.stdout)
        self.assertIn('WINNER=p\nVERSION=\n', x.stdout)

    def test_a_named_version_beats_an_any_version_provider(self):
        x = self.resolve('*=p.mpp*) echo "Any (4 patches)";;\n*) echo "  5.0 (3 patches)";;', candidates=('p', 'q'))
        self.assertIn('WINNER=q\nVERSION=5.0\n', x.stdout)

    def test_ceiling_still_used_when_set(self):
        x = self.resolve('*) echo "Any (4 patches)";;', maxver='26.34.0')
        self.assertIn('VERSION=26.34.0\n', x.stdout)

    def test_plan_packet_refuses_an_empty_version(self):
        # The shadow packet needs digits; an any-version target builds through the legacy path.
        import importlib.util
        spec = importlib.util.spec_from_file_location('ri', ROOT / 'src/build/resolved_inputs.py')
        self.assertIn("any app version, the store's newest", (ROOT / 'src/build/resolved_inputs.py').read_text())
        text = (ROOT / 'src/build/resolved_inputs.py').read_text()
        self.assertIn('need(key not in result and value, "duplicate or empty resolver field")', text)


if __name__ == '__main__':
    unittest.main()
