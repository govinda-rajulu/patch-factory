"""W16h (L088): the APKMirror variant picker skips rows whose minimum Android is above the cap."""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROWS = ('<div class="table-row">BUNDLE arm64-v8a + armeabi-v7a Android 12L+ 120-640dpi <a class="accent_color" href="/a">\n'
        '<div class="table-row">BUNDLE arm64-v8a + armeabi-v7a Android 8.0+ 480-640dpi <a class="accent_color" href="/b">\n'
        '<div class="table-row">BUNDLE arm64-v8a Android 10+ 480-640dpi <a class="accent_color" href="/c">\n'
        '<div class="table-row">BUNDLE universal nodpi <a class="accent_color" href="/d">')


def fit(ceil):
    utils = (ROOT / 'src/build/utils.sh').read_text()
    funcs = utils[utils.index('pf_android_sdk() {'):utils.index('get_apk() {')]
    script = funcs + '\npf_rows_fit_ceiling "$ROWS" "$CEIL" | grep -oP \'href="\\K[^"]+\'\n'
    out = subprocess.run(['bash', '-c', script], env={'ROWS': ROWS, 'CEIL': str(ceil), 'PATH': '/usr/bin:/bin'},
                         capture_output=True, text=True)
    return out.stdout.split()


class VariantCeiling(unittest.TestCase):
    def test_truecaller_rows_under_android_10(self):
        self.assertEqual(fit(29), ['/b', '/c', '/d'])

    def test_high_cap_keeps_every_row_and_low_cap_keeps_unreadable_rows(self):
        self.assertEqual(fit(37), ['/a', '/b', '/c', '/d'])
        self.assertEqual(fit(25), ['/d'])

    def test_picker_and_callers_wire_the_cap(self):
        utils = (ROOT / 'src/build/utils.sh').read_text()
        body = utils.split('get_apk() {', 1)[1]
        self.assertLess(body.index('pf_rows_fit_ceiling "$filtered_rows" "$PF_SDK_CEILING"'),
                        body.index("variant_href=$(echo \"$filtered_rows\" | grep -oP"))
        self.assertIn('export PF_SDK_CEILING="$CEIL"', (ROOT / 'src/build/build.sh').read_text())
        self.assertIn('export PF_SDK_CEILING=', (ROOT / 'src/build/source_download.sh').read_text())


if __name__ == '__main__':
    unittest.main()
