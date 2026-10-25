"""W16h: a release with several .mpp assets builds from the one named for its tag (legendsciber v1.52.0)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/build'))
import extra_bundle  # noqa: E402
import github_bundle  # noqa: E402


def names(rows):
    return [r['name'] for r in rows]


class Pick(unittest.TestCase):
    def test_one_shared_rule(self):
        self.assertIs(extra_bundle.pick_mpp, github_bundle.pick_mpp)

    def test_legendsciber_v1_52_0_shape(self):
        # Copied from the live release (25 Oct 2026): the old bundle rides along.
        rows = [{'name': 'patches-1.51.0.mpp'}, {'name': 'patches-1.52.0.mpp'}]
        self.assertEqual(names(github_bundle.pick_mpp(rows, 'v1.52.0')), ['patches-1.52.0.mpp'])

    def test_single_bundle_and_non_mpp_assets(self):
        rows = [{'name': 'oxbow.apk'}, {'name': 'oxbow-clone.apk'}, {'name': 'patches-1.0.1.mpp'}]
        self.assertEqual(names(github_bundle.pick_mpp(rows, 'v452-0-0-48-64')), ['patches-1.0.1.mpp'])

    def test_ambiguous_or_unmatched_still_refuses(self):
        two = [{'name': 'patches-1.51.0.mpp'}, {'name': 'patches-1.52.0.mpp'}]
        for tag in ('v2.0.0', 'nightly', '', None):
            self.assertEqual(len(github_bundle.pick_mpp(two, tag)), 2, tag)
        both = [{'name': 'a-1.5.0.mpp'}, {'name': 'b-1.5.0.mpp'}]
        self.assertEqual(len(github_bundle.pick_mpp(both, 'v1.5.0')), 2)

    def test_version_boundaries(self):
        rows = [{'name': 'p-1.5.0.mpp'}, {'name': 'p-11.5.0.mpp'}, {'name': 'p-1.5.01.mpp'}]
        self.assertEqual(names(github_bundle.pick_mpp(rows, 'v1.5.0')), ['p-1.5.0.mpp'])
        dev = [{'name': 'patches-1.9.0-dev.1.mpp'}, {'name': 'patches-1.8.0.mpp'}]
        self.assertEqual(names(github_bundle.pick_mpp(dev, 'v1.9.0-dev.1')), ['patches-1.9.0-dev.1.mpp'])


if __name__ == '__main__':
    unittest.main()
