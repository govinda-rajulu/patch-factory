"""Release pages show the exact provider bundle version, prerelease suffix included (W15d)."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/build'))
import bundle_version as bv  # noqa: E402


class BundleVersion(unittest.TestCase):
    def test_prerelease_suffix_is_kept(self):
        cases = {'patches-1.2.0-dev.3.mpp': '1.2.0-dev.3', './patches-1.48.0.mpp': '1.48.0',
                 'patches-2.1.0-beta.12.mpp': '2.1.0-beta.12', 'hushfacebook-0.15.0.mpp': '0.15.0',
                 'patches-v1.1.1.mpp': '1.1.1', 'patches-1.0.0-dev.mpp': '1.0.0-dev',
                 'patches.mpp': 'unknown', 'x': 'unknown'}
        for name, want in cases.items():
            with self.subTest(name=name):
                self.assertEqual(bv.version_of(name), want)

    def test_build_uses_it(self):
        text = (ROOT / 'src/build/build.sh').read_text(encoding='utf-8')
        self.assertIn('PV=$(python3 src/build/bundle_version.py "$FIRST")', text)
        out = subprocess.run([sys.executable, 'src/build/bundle_version.py', 'patches-1.2.0-dev.3.mpp'],
                             cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(out.stdout.strip(), '1.2.0-dev.3')


    def test_checked_plan_path_reads_the_same_way(self):
        # W15d double check: daily and batch builds take PV from the checked Plan lock, which used the
        # old digits-only pattern too; one reader for both paths, and the lock check stays one line.
        text = (ROOT / 'src/build/resolved_inputs.py').read_text(encoding='utf-8')
        self.assertIn('"patch_version": bundle_version.version_of(source.name),', text)
        self.assertNotIn('re.findall(r"[0-9]+(?:[.][0-9]+)+", source.stem)', text)
        for good in ('1.2.0-dev.3', '1.48.0', '2.1.0-beta.12'):
            self.assertTrue(bv.PATTERN.fullmatch(good), good)
        for bad in ('1\nWINNER=evil', '1.2.0-dev.3\n', '1.2.0 x', '-dev', '1'):
            self.assertIsNone(bv.PATTERN.fullmatch(bad), bad)


if __name__ == '__main__':
    unittest.main()
