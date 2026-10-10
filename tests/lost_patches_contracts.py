"""Lost patches are dropped by name, capped, and refused under strict_patches (packet W13).

No network: a synthetic list-patches listing stands in for the patcher.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/build'))
sys.path.insert(0, str(ROOT / 'tests'))
import lost_patches  # noqa: E402
from coverage_contracts import block  # noqa: E402


def listing(names_versions):
    return ''.join(block(i, n, versions=v) for i, (n, v) in enumerate(names_versions))


class Lost(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.r = Path(self.t.name)
        (self.r / 'src/patches/p').mkdir(parents=True)
        (self.r / 'src/patches/e').mkdir(parents=True)
        (self.r / 'extra').mkdir()
        (self.r / 'morphe-desktop-1.0-all.jar').write_bytes(b'jar')
        (self.r / '09-p.mpp').write_bytes(b'p')
        self.inc = self.r / 'src/patches/p/include-patches'
        self.inc.write_bytes(b'# comment\nA\nB\nC\nD\nE|opt\nF\nG\nH\n')
        (self.r / 'src/patches/e/include-patches').write_bytes(b'X\n')
        self.target()

    def target(self, **extra):
        t = dict(id='x', package='com.x', exclusive=True, candidates=[dict(name='p', patch_dir='p')], **extra)
        (self.r / 'src/targets.json').write_text(json.dumps([t]))

    def run_prune(self, offered, version='2.0'):
        text = listing(offered)
        return lost_patches.prune(self.r, 'x', 'p', version, listing=lambda jar, mpp, pkg: text)

    def test_all_offered_changes_nothing(self):
        before = self.inc.read_bytes()
        rc = self.run_prune([(n, ()) for n in 'ABCDEFGH'])
        self.assertEqual(rc, 0)
        self.assertEqual(self.inc.read_bytes(), before)
        self.assertFalse((self.r / '.dropped').exists())

    def test_absent_and_wrong_version_are_dropped_by_name(self):
        rc = self.run_prune([(n, ()) for n in 'ABCDFG'] + [('H', ('1.0',))])
        self.assertEqual(rc, 0)
        self.assertEqual(self.inc.read_bytes(), b'# comment\nA\nB\nC\nD\nF\nG\n')
        rows = (self.r / '.dropped').read_text().splitlines()
        self.assertEqual([r.split('\t')[1] for r in rows], ['E', 'H'])
        self.assertIn('not offered for app 2.0', rows[1])

    def test_any_version_build_skips_the_version_test(self):
        rc = self.run_prune([(n, ('1.0',)) for n in 'ABCDEFGH'], version='')
        self.assertEqual(rc, 0)
        self.assertFalse((self.r / '.dropped').exists())

    def test_more_than_a_quarter_refuses_and_writes_nothing(self):
        before = self.inc.read_bytes()
        rc = self.run_prune([(n, ()) for n in 'ABCD'])
        self.assertEqual(rc, 4)
        self.assertEqual(self.inc.read_bytes(), before)

    def test_strict_patches_refuses(self):
        self.target(strict_patches=True)
        rc = self.run_prune([(n, ()) for n in 'ABCDEFG'])
        self.assertEqual(rc, 4)

    def test_unreadable_listing_drops_nothing(self):
        before = self.inc.read_bytes()
        rc = lost_patches.prune(self.r, 'x', 'p', '2.0', listing=lambda *a: 'garbage')
        self.assertEqual(rc, 0)
        self.assertEqual(self.inc.read_bytes(), before)

    def test_accept_after_patching_counts_earlier_drops(self):
        (self.r / '.requested').write_text(''.join('p\t%s\n' % n for n in 'ABCDEFGH'))
        miss = self.r / 'miss.txt'
        miss.write_text('A\n')
        self.assertEqual(lost_patches.accept(self.r, 'x', str(miss)), 0)
        miss.write_text('B\nC\nD\n')
        self.assertEqual(lost_patches.accept(self.r, 'x', str(miss)), 4)
        self.assertEqual(len((self.r / '.dropped').read_text().splitlines()), 1)


if __name__ == '__main__':
    unittest.main()
