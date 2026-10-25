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
        # W16k: one judge for chip, Android and screen; exit 4 (nothing fits) returns 4.
        self.assertIn('python3 ./src/build/variant_pick.py --type "$type_badge" --arch "$arch" --dpi "$dpi"', body)
        self.assertIn('--ceiling "${PF_SDK_CEILING:-}"', body)
        self.assertIn('return 4', body.split('variant_pick.py', 1)[1].split('direct_apk_href', 1)[0])
        self.assertIn('export PF_SDK_CEILING="$CEIL"', (ROOT / 'src/build/build.sh').read_text())
        self.assertIn('export PF_SDK_CEILING=', (ROOT / 'src/build/source_download.sh').read_text())


def pick(rows, *args):
    r = subprocess.run(['python3', str(ROOT / 'src/build/variant_pick.py')] + list(args), input=rows,
                       capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr


def row(kind, text, href):
    return '<div class="table-row"><span class="apkm-badge">%s</span> %s <a class="accent_color" href="%s">' % (kind, text, href)


class VariantPick(unittest.TestCase):
    """W16k (owner, 25 Oct 2026): chip, Android and screen judged together; never a non-fitting row."""
    KEYMAPPER = '\n'.join([  # APKMirror Key Mapper 4.5.0 (owner's link, 25 Oct 2026), 3 variants
        row('BUNDLE', 'arm64-v8a Android 10+ 480-640dpi', '/km-arm64-10'),
        row('BUNDLE', 'universal Android 12L+ 120-480dpi', '/km-univ-12l'),
        row('BUNDLE', 'universal Android 8.0+ 480-640dpi', '/km-univ-8')])

    def test_key_mapper_450_takes_the_arm64_android_10_build(self):
        self.assertEqual(pick(self.KEYMAPPER, '--type', 'BUNDLE', '--ceiling', '29')[:2], (0, 'BUNDLE\t/km-arm64-10'))

    def test_nothing_fits_is_exit_4_not_the_first_row(self):
        rows = '\n'.join([row('BUNDLE', 'arm64-v8a + armeabi-v7a Android 12L+ 120-640dpi', '/tc-12l'),
                          row('APK', 'armeabi-v7a Android 8.0+ nodpi', '/tc-32bit')])
        rc, out, err = pick(rows, '--type', 'BUNDLE', '--ceiling', '29')
        self.assertEqual((rc, out), (4, ''))
        self.assertIn('needs Android API 32, phone 29', err)
        self.assertIn('no arm64 code', err)

    def test_other_type_and_universal_when_the_wanted_type_has_no_fit(self):
        rows = '\n'.join([row('BUNDLE', 'arm64-v8a Android 12+ nodpi', '/b-12'), row('APK', 'universal Android 9+ nodpi', '/a-9')])
        self.assertEqual(pick(rows, '--type', 'BUNDLE', '--ceiling', '29')[:2], (0, 'APK\t/a-9'))

    def test_pinned_code_and_dpi_preferences(self):
        rows = '\n'.join([row('APK', 'arm64-v8a Android 9+ 480dpi 475614280', '/x'), row('APK', 'arm64-v8a Android 9+ 480-640dpi 475614366', '/y')])
        self.assertEqual(pick(rows, '--type', 'APK', '--ceiling', '29', '--pin', '475614366')[1], 'APK\t/y')
        self.assertEqual(pick(rows, '--type', 'APK', '--ceiling', '29', '--dpi', '480dpi')[1], 'APK\t/x')

    def test_no_rows_is_exit_3(self):
        self.assertEqual(pick('<html>no table</html>', '--type', 'APK')[0], 3)


class SameVersionFirst(unittest.TestCase):
    def test_sdk_gate_tries_the_other_store_for_the_same_version_before_stepping_down(self):
        b = (ROOT / 'src/build/build.sh').read_text()
        gate = b.split('# --- 5. sdk gate, enforced', 1)[1]
        self.assertLess(gate.index('VARIANT_RETRY same version'), gate.index('pf_next_version'))
        self.assertIn('FORCE_STORE="$OTHER"; RVER="${version:-$RVER}"', gate)
        self.assertIn('TRIED=""; FORCE_STORE=""', gate)  # a lower version starts with both stores again
        self.assertIn('USE_SRC="${FORCE_STORE:-$SRC}"', b)

    def test_key_mapper_downloads_from_apkmirror_first(self):
        import json
        t = next(x for x in json.loads((ROOT / 'src/targets.json').read_text()) if x['id'] == 'keymapper')
        self.assertEqual(t.get('source'), 'apkpure')  # qualified store kept; VARIANT_RETRY reaches APKMirror


if __name__ == '__main__':
    unittest.main()
