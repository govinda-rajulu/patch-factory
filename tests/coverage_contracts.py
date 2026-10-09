"""Coverage-first version choice (packet W12, owner design 10 Oct 2026).

The version where the most of our chosen patches apply wins; the newest breaks a tie;
max_app_version stays a ceiling; an exact version_code pin keeps its version; any doubt
keeps the newest version as before. Uses the real listing in docs/review/PATCHES-youtube.txt
and small synthetic listings. No network.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COV = ROOT / 'src/build/coverage.py'
PY = shutil.which('python3') or sys.executable


def block(i, name, enabled=True, pkg='com.x', versions=()):
    out = ['%sIndex: %d' % ('INFO: ' if i == 0 else '', i), 'Name: ' + name, 'Description: d', 'Enabled: ' + ('true' if enabled else 'false')]
    if pkg:
        out += ['Compatible packages:', '\tPackage name: ' + pkg]
        if versions:
            out += ['\tCompatible versions:'] + ['\t\t' + v for v in versions]
    return '\n'.join(out) + '\n'


LISTING = ''.join([
    block(0, 'A', versions=('3.0', '2.0', '1.0')),
    block(1, 'B', versions=('2.0', '1.0')),
    block(2, 'C', versions=('2.0', '1.0')),
    block(3, 'D universal', pkg=None),
    block(4, 'E any', versions=()),
    'Name: F\nDescription: x\nEnabled: false\nOptions:\n\tTitle: t\n\tPossible values:\n\t\t9.9\n\t\tin-app (Change)\n'
    'Compatible packages:\n\tPackage name: com.x\n\tCompatible versions:\n\t\t3.0\n',
])


class Coverage(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.r = Path(self.t.name)
        (self.r / 'src/patches/x').mkdir(parents=True)
        (self.r / 'listing.txt').write_text(LISTING)
        self.target()

    def target(self, include=('A', 'B', 'C', 'D universal', 'E any'), exclude=(), exclusive=True, **extra):
        (self.r / 'src/patches/x/include-patches').write_text('\n'.join(include) + '\n')
        (self.r / 'src/patches/x/exclude-patches').write_text('\n'.join(exclude) + ('\n' if exclude else ''))
        t = dict(id='x', package='com.x', exclusive=exclusive, candidates=[dict(name='p', patch_dir='x', owner='o', repo='r', channel='latest')])
        t.update(extra)
        (self.r / 'src/targets.json').write_text(json.dumps([t]))

    def run_cov(self, versions, maxver='', listing=None):
        f = self.r / 'listing.txt'
        if listing is not None:
            f.write_text(listing)
        x = subprocess.run([PY, str(COV), '--listing', str(f), 'com.x', 'x', 'p', maxver], input=versions,
                           cwd=self.r, env={**os.environ, 'PF_ROOT': str(self.r)}, capture_output=True, text=True)
        return x.returncode, dict(l.split('=', 1) for l in x.stdout.splitlines() if l.startswith('COVERAGE_') and '=' in l), x.stdout

    def test_older_version_with_more_chosen_patches_wins(self):
        rc, kv, out = self.run_cov('3.0 6\n2.0 5\n1.0 5\n')
        self.assertEqual((rc, kv['COVERAGE_PICK'], kv['COVERAGE_COVERED'], kv['COVERAGE_TOTAL']), (0, '2.0', '5', '5'), out)
        self.assertIn('newest 3.0 covers 3', out)

    def test_newest_breaks_a_tie(self):
        self.target(include=('A', 'D universal'))
        rc, kv, out = self.run_cov('3.0 6\n2.0 5\n1.0 5\n')
        self.assertEqual((rc, kv['COVERAGE_PICK']), (0, '3.0'), out)

    def test_ceiling_holds_and_lost_patches_are_named(self):
        self.target(include=('A', 'B'))
        rc, kv, out = self.run_cov('3.0 6\n2.0 5\n', maxver='2.0')
        self.assertEqual(kv['COVERAGE_PICK'], '2.0')
        rc, kv, out = self.run_cov('3.0 6\n', maxver='')
        self.assertEqual((kv['COVERAGE_PICK'], kv['COVERAGE_COVERED']), ('3.0', '1'))
        self.assertIn('COVERAGE_LOST p: B', out)

    def test_exact_version_code_pin_keeps_its_version(self):
        self.target(version_code='475215365', max_app_version='3.0')
        rc, kv, out = self.run_cov('3.0 6\n2.0 5\n', maxver='3.0')
        self.assertEqual((rc, kv['COVERAGE_PICK'], kv['COVERAGE_COVERED']), (0, '3.0', '3'), out)
        self.assertIn('version kept', out)
        self.assertIn('COVERAGE_LOST p: B', out)

    def test_option_values_are_not_versions(self):
        self.target(include=('F',), exclusive=True)
        rc, kv, out = self.run_cov('9.9 1\n3.0 1\n')
        self.assertEqual((rc, kv['COVERAGE_PICK']), (0, '3.0'), out)

    def test_defaults_minus_excludes_for_non_exclusive_targets(self):
        self.target(include=(), exclude=('A',), exclusive=False)
        rc, kv, out = self.run_cov('3.0 6\n2.0 5\n')
        # A excluded, F not enabled: chosen are B, C, D, E.
        self.assertEqual((kv['COVERAGE_TOTAL'], kv['COVERAGE_PICK']), ('4', '2.0'), out)

    def test_doubt_is_unavailable_never_a_guess(self):
        for bad in ('', 'Name: A\nName: B\nEnabled: true\n', 'garbage\n'):
            rc, kv, out = self.run_cov('3.0 6\n', listing=bad)
            self.assertEqual(rc, 3, out)
            self.assertTrue(out.startswith('COVERAGE_UNAVAILABLE'), out)
        self.target(include=('Z not listed',))
        rc, kv, out = self.run_cov('3.0 6\n', listing=LISTING)
        self.assertEqual(rc, 3, out)

    def test_real_youtube_listing(self):
        x = subprocess.run([PY, str(COV), '--listing', str(ROOT / 'docs/review/PATCHES-youtube.txt'),
                            'com.google.android.youtube', 'youtube', 'morphe', ''],
                           input='21.36.45 82\n21.35.442 82\n20.21.37 81\n', cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(x.returncode, 0, x.stdout)
        self.assertIn('COVERAGE_PICK=21.36.45', x.stdout)


class Resolver(unittest.TestCase):
    """resolve.sh end to end with a fake patcher: coverage decides, doubt keeps the newest."""
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.r = Path(self.t.name)
        (self.r / 'src/build').mkdir(parents=True)
        shutil.copy(COV, self.r / 'src/build/coverage.py')
        (self.r / 'src/patches/x').mkdir(parents=True)
        (self.r / 'src/patches/x/include-patches').write_text('A\nB\nC\n')
        (self.r / 'src/targets.json').write_text(json.dumps([dict(id='x', package='com.x', exclusive=True, candidates=[
            dict(name='p', patch_dir='x', owner='o', repo='r', channel='latest')])]))
        (self.r / 'morphe-desktop-1.jar').write_text('jar')
        self.bin = self.r / 'bin'
        self.bin.mkdir()
        (self.bin / 'python3').write_text('#!/bin/bash\nif [ "$1" = src/build/github_bundle.py ]; then '
                                          'echo \'{"published_at":"2026-10-01T00:00:00Z","path":"b.mpp","sha256":"h","tag":"v1"}\'; exit 0; fi\n'
                                          'exec %s "$@"\n' % PY)
        (self.bin / 'python3').chmod(0o755)

    def java(self, listing):
        (self.r / 'listing.txt').write_text(listing)
        (self.bin / 'java').write_text('#!/bin/bash\ncase "$*" in *list-versions*) printf "  3.0 (6 patches)\\n  2.0 (5 patches)\\n" ;;\n'
                                       '*list-patches*) cat %s ;; esac\n' % (self.r / 'listing.txt'))
        (self.bin / 'java').chmod(0o755)

    def resolve(self):
        return subprocess.run(['bash', str(ROOT / 'src/build/resolve.sh'), 'x'], cwd=self.r, capture_output=True, text=True,
                              env={**os.environ, 'PATH': str(self.bin) + ':' + os.environ['PATH']})

    def test_coverage_moves_the_version(self):
        self.java(LISTING)
        x = self.resolve()
        self.assertEqual(x.returncode, 0, x.stdout + x.stderr)
        self.assertIn('VERSION=2.0', x.stdout)
        self.assertIn('COVERAGE p: app 2.0 covers 3 of 3 chosen patches; newest 3.0 covers 1', x.stdout)

    def test_unreadable_listing_keeps_the_newest(self):
        self.java('nothing useful\n')
        x = self.resolve()
        self.assertEqual(x.returncode, 0, x.stdout + x.stderr)
        self.assertIn('VERSION=3.0', x.stdout)
        self.assertIn('::notice::COVERAGE_UNAVAILABLE p: no patch names in the listing; newest version kept', x.stdout)


class PublicLog(unittest.TestCase):
    def test_plan_summary_shows_the_coverage_line_and_withholds_patch_names(self):
        sys.path.insert(0, str(ROOT / 'src/build'))
        import importlib.util
        spec = importlib.util.spec_from_file_location('pf_resolved', ROOT / 'src/build/resolved_inputs.py')
        ri = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ri)
        text = ri.resolver_summary('COVERAGE p: app 2.0 covers 3 of 3 chosen patches; newest 3.0 covers 1\n'
                                   'COVERAGE_LOST p: Some upstream name\n', 0)
        self.assertIn('COVERAGE p: app 2.0 covers 3 of 3', text)
        self.assertNotIn('upstream', text)
        self.assertIn('1 other line(s) withheld', text)


if __name__ == '__main__':
    unittest.main()
