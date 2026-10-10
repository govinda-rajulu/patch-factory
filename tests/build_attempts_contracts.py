"""Provider fallback (packet W13): a failed build retries the next candidate, cleanly.

A fake build.sh in a throwaway git checkout stands in for the real build. No network.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/build'))
import build_attempts  # noqa: E402

FAKE = r'''#!/bin/bash
W=$(jq -r --arg id "$1" '.[] | select(.id==$id) | (.pin // "a")' src/targets.json)
[ "$W" = "null" ] && W=a
echo "[+] winner=$W (o/r) app=1"
echo "attempt env resolved=${PF_RESOLVED_READY:-unset} max=$(jq -r '.[0].max_app_version // "none"' src/targets.json)"
if [ -e download/junk ] || grep -q dirty src/keep.txt; then echo "[-] leftover from the failed attempt"; exit 7; fi
if [ "$W" = "${FAIL:-a}" ] || [ "${FAIL:-a}" = all ]; then
  mkdir -p download; echo x > download/junk; echo dirty >> src/keep.txt; echo "[-] boom in $W"; exit 3
fi
mkdir -p release; echo ok > release/app.apk; exit 0
'''


class Attempts(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.r = Path(self.t.name)
        (self.r / 'src/build').mkdir(parents=True)
        (self.r / 'src/build/build.sh').write_text(FAKE)
        (self.r / 'src/keep.txt').write_text('clean\n')
        self.targets()
        for c in (['init', '-q'], ['add', '-A'], ['-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'x']):
            subprocess.run(['git', *c], cwd=self.r, check=True)
        (self.r / 'src/ks.keystore').write_text('kept')  # untracked before the build: must survive
        self.out = self.r.parent / (self.r.name + '.out')
        self.addCleanup(lambda: self.out.exists() and self.out.unlink())

    def targets(self, **extra):
        t = dict(id='x', enabled=True, pin=None, max_app_version='2.0', candidates=[
            dict(name='a', patch_dir='a'),
            dict(name='b', patch_dir='b', fallback=True, overrides=dict(max_app_version='1.0'))], **extra)
        (self.r / 'src/targets.json').write_text(json.dumps([t], indent=2) + '\n')

    def run_it(self, **env):
        e = dict(os.environ, GITHUB_OUTPUT=str(self.out), RUNNER_TEMP=str(self.r.parent), PF_RESOLVED_READY='true', **env)
        rc = build_attempts.main(['x'], env=e, root=self.r)
        out = dict(l.split('=', 1) for l in self.out.read_text().splitlines()) if self.out.exists() else {}
        return rc, out

    def test_primary_works_one_attempt(self):
        rc, out = self.run_it(FAIL='none')
        self.assertEqual((rc, out['fallback'], out['winner'], out['attempts']), (0, 'false', 'a', '1'))
        self.assertFalse((self.r / 'release/.fallback').exists())

    def test_failed_primary_falls_back_clean_with_overrides(self):
        rc, out = self.run_it(FAIL='a')
        self.assertEqual((rc, out['fallback'], out['winner'], out['attempts']), (0, 'true', 'b', '2'))
        self.assertIn('Built with fallback provider b after a failed ([-] boom in a)', (self.r / 'release/.fallback').read_text())
        self.assertEqual((self.r / 'src/ks.keystore').read_text(), 'kept')
        self.assertFalse((self.r / 'download').exists())
        self.assertEqual(json.loads((self.r / 'src/targets.json').read_text())[0]['max_app_version'], '1.0')

    def test_every_candidate_fails(self):
        rc, out = self.run_it(FAIL='all')
        self.assertEqual(rc, 3)
        self.assertEqual((out['fallback'], out['attempts']), ('false', '2'))

    def test_forced_provider_builds_only_it(self):
        rc, out = self.run_it(FAIL='b', PF_PROVIDER='b')
        self.assertEqual((rc, out['attempts']), (3, '1'))

    def test_unknown_provider_refuses(self):
        rc, _ = self.run_it(PF_PROVIDER='zzz')
        self.assertEqual(rc, 1)

    def test_pinned_target_has_no_fallback(self):
        t = json.loads((self.r / 'src/targets.json').read_text())
        t[0]['fallback'] = False
        (self.r / 'src/targets.json').write_text(json.dumps(t, indent=2) + '\n')
        rc, out = self.run_it(FAIL='a')
        self.assertEqual((rc, out['attempts']), (3, '1'))

    def test_plan_order(self):
        t = dict(id='x', candidates=[dict(name='p1'), dict(name='f', fallback=True), dict(name='p2')])
        self.assertEqual(build_attempts.plan(t, ''), [None, 'p1', 'p2', 'f'])


if __name__ == '__main__':
    unittest.main()
