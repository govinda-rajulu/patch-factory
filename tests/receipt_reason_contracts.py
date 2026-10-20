"""W15b (20 Oct 2026, L063): a refused publication receipt names its reason.

19 Oct Facebook (oversized merged APK) and 11 Oct LinkedIn (plan version differs from the
stepped-down build) printed one identical generic line; the cause took a log pull to find.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/build'))
import resolved_inputs  # noqa: E402
import shadow_inputs  # noqa: E402


class ReceiptReason(unittest.TestCase):
    def test_reason_is_printed_for_a_failed_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            env = dict(os.environ, GITHUB_REF='refs/heads/feature')
            r = subprocess.run([sys.executable, str(ROOT / 'src/build/shadow_inputs.py'), 'receipt', 'facebook'],
                               cwd=d, env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 1)
        self.assertIn('::warning::publication receipt not stored facebook: shadow inputs: receipt requires main publication', r.stderr)

    def test_foreign_text_never_reaches_the_log(self):
        self.assertEqual(shadow_inputs.public_reason(ValueError('https://x.example/?token=abc')), 'ValueError')
        self.assertEqual(shadow_inputs.public_reason(KeyError('apk')), 'KeyError')
        self.assertEqual(shadow_inputs.public_reason(ValueError('resolved inputs: nonregular, empty or oversized input')),
                         'resolved inputs: nonregular, empty or oversized input')

    def test_bound_holds_the_largest_merged_apk_seen(self):
        # Facebook 583 code 475614366 merged on 19 Oct 2026.
        self.assertGreaterEqual(resolved_inputs.MAX_FILE, 301471185)
        self.assertLess(resolved_inputs.MAX_FILE, 2 * 1024 ** 3)  # GitHub release asset limit
        self.assertGreaterEqual(resolved_inputs.MAX_TOTAL, resolved_inputs.MAX_FILE)


if __name__ == '__main__':
    unittest.main()
