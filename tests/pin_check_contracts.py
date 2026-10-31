"""Offline contracts for the read-only configured-store pin check."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pin_check', ROOT / 'src/etc/pin_check.py')
pin = importlib.util.module_from_spec(spec); spec.loader.exec_module(pin)

APPS = {'apkmirror': {'pkg': {'list_url': 'https://www.apkmirror.com/uploads/?appcategory=pkg'}},
        'apkpure': {'pkg2': {'download_url': 'https://apkpure.com/x/pkg2/download'}}}
TARGET = {'id': 'fixture', 'enabled': True, 'package': 'pkg', 'source': 'apkmirror',
          'version_code': '123456', 'max_app_version': '1.2.3'}
RELEASE_OK = '''<html><h1>Pkg 1.2.3</h1><div class="variants-table"><div class="table-row">
<a class="accent_color" href="/pkg-variant/">BUNDLE arm64-v8a Android 11+ 480dpi versionCode 123456</a>
</div></div></html>'''
RELEASE_MISSING = RELEASE_OK.replace('versionCode 123456', 'versionCode 999999')
CLOUDFLARE = '''<!doctype html><html><head><title>Just a moment...</title><script>var code=123456</script></head>
<body>Performing security verification</body></html>'''


class PinCheck(unittest.TestCase):
    def check(self, body, target=TARGET):
        return pin.check_target(target, APPS, lambda _url: body)

    def test_exact_code_and_ceiling_are_ok(self):
        row = self.check('<div>Version 1.2.3 versionCode 123456</div>')
        self.assertEqual((row['status'], pin.line(row)), ('OK', 'PIN_STORE_OK target=fixture store=apkmirror version=1.2.3 code=123456'))

    def test_release_fixture_with_variant_code_is_ok(self):
        self.assertEqual(self.check(RELEASE_OK)['status'], 'OK')

    def test_release_fixture_without_variant_code_is_missing(self):
        row = self.check(RELEASE_MISSING)
        self.assertEqual((row['status'], row['reason']), ('MISSING', 'version_code_not_listed'))

    def test_cloudflare_challenge_is_unknown(self):
        row = self.check(CLOUDFLARE)
        self.assertEqual((row['status'], row['reason']), ('UNKNOWN', 'listing_unreadable'))

    def test_pin_fetch_has_no_download_request(self):
        import subprocess, tempfile
        script = ROOT / 'src/etc/pin_fetch.sh'
        text = script.read_text()
        self.assertNotIn('/download/', text)
        self.assertNotIn('key=', text)
        with tempfile.TemporaryDirectory() as d:
            probe = Path(d) / 'probe.sh'
            probe.write_text(r'''#!/bin/bash
set -eu
export PF_PIN_FETCH_SOURCE_ONLY=1 PF_TMP_DIR="$1" PF_PIN_CHECK_ONLY=1 PF_PIN_CODE=123456 PF_SDK_CEILING=30
source src/etc/pin_fetch.sh
urls=()
_cf_get() {
  urls+=("$1")
  if [[ "$1" == *uploads* ]]; then
    html='<h5 class="appRowTitle"><a class="fontBlack" href="/pkg-1-2-3-release/">Pkg 1.2.3</a></h5>'
  else
    html='<div class="variants-table"><div class="table-row"><a class="accent_color" href="/pkg-variant/">BUNDLE arm64-v8a Android 11+ 480dpi versionCode 123456</a></div></div>'
  fi
}
export version=1.2.3 lock_version=0 prefer_version=""
get_apk com.facebook.katana facebook bundle arm64-v8a 480dpi
printf '%s\n' "${urls[@]}"
''')
            probe.chmod(0o755)
            got = subprocess.run([str(probe), d], cwd=ROOT, text=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 check=True).stdout
        urls = [line for line in got.splitlines() if line.startswith('https://')]
        self.assertTrue(urls)
        self.assertTrue(all('/download/' not in u and 'key=' not in u and
                            not u.endswith(('.apk', '.apkm')) for u in urls))

    def pin_only(self, code, release_html):
        """Run the build's get_apk pin-only branch on a captured release page (no network)."""
        import subprocess, tempfile
        with tempfile.TemporaryDirectory() as d:
            page = Path(d) / 'release.html'
            page.write_text(release_html)
            probe = Path(d) / 'probe.sh'
            probe.write_text(r'''#!/bin/bash
set -u
export PF_PIN_FETCH_SOURCE_ONLY=1 PF_TMP_DIR="$1" PF_PIN_CHECK_ONLY=1 PF_PIN_CODE="$2" PF_SDK_CEILING=30
PAGE="$3"
source src/etc/pin_fetch.sh
_cf_get() {
  if [[ "$1" == *uploads* ]]; then
    html='<h5 class="appRowTitle"><a class="fontBlack" href="/apk/facebook-2/facebook/facebook-584-0-0-51-56-release/">Facebook 584.0.0.51.56</a></h5>'
  else
    html=$(cat "$PAGE")
  fi
}
export version=584.0.0.51.56 lock_version=0 prefer_version=""
get_apk com.facebook.katana facebook bundle arm64-v8a 480dpi
''')
            probe.chmod(0o755)
            return subprocess.run([str(probe), d, code, str(page)], cwd=ROOT, text=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT).returncode

    def test_real_apkmirror_rows_carry_a_bare_code(self):
        # W16z (wrong call 122): run 41158386985 printed PIN_STORE_MISSING for Facebook, Facebook
        # De-Vanced and Instagram while the captured pages listed all three pins. APKMirror prints
        # the code as a bare number; the old fixtures had a "versionCode" label real pages lack.
        real = (ROOT / 'tests/fixtures/apkmirror-facebook-584-rows.html').read_text()
        self.assertNotRegex(real.split('-->', 1)[1], r'(?i)version[ _-]?code')
        self.assertEqual(self.pin_only('475817393', real), 0)
        self.assertEqual(self.pin_only('475817392', real), 2)
        self.assertEqual(self.pin_only('47581739', real), 2)

    def test_code_and_max_version_missing_are_distinct(self):
        self.assertEqual(self.check('<div>Version 1.2.3 versionCode 9</div>')['reason'], 'version_code_not_listed')
        t = dict(TARGET, version_code=None)
        self.assertEqual(self.check('<div>Version 1.2.4</div>', t)['reason'], 'max_version_not_listed')

    def test_transport_parser_and_mapping_failures_are_unknown(self):
        unknown = pin.check_target(TARGET, APPS, lambda _url: '<html>not a release</html>')
        self.assertEqual(unknown['status'], 'UNKNOWN')
        unknown = pin.check_target(TARGET, APPS, lambda _url: (_ for _ in ()).throw(RuntimeError('secret URL')))
        self.assertEqual(pin.line(unknown), 'PIN_STORE_UNKNOWN target=fixture store=apkmirror reason=listing_unreadable')
        unknown = pin.check_target(dict(TARGET, package='not-mapped'), APPS, lambda _url: '')
        self.assertEqual(unknown['status'], 'UNKNOWN')

    def run_main(self, rows, body, *extra):
        import contextlib, io, json, tempfile
        with tempfile.TemporaryDirectory() as d:
            tp, ap = Path(d) / 't.json', Path(d) / 'a.json'
            tp.write_text(json.dumps(rows)); ap.write_text(json.dumps(APPS))
            old = pin.http_fetch
            pin.http_fetch = lambda _url: body
            out = io.StringIO()
            try:
                with contextlib.redirect_stdout(out):
                    rc = pin.main(['--targets', str(tp), '--apps', str(ap)] + list(extra))
            finally:
                pin.http_fetch = old
        return rc, out.getvalue().splitlines()

    def test_only_exact_build_pins_are_selected(self):
        # W16y-b review: a max_app_version ceiling is not a pin; disabled targets are skipped.
        rows = [dict(TARGET), dict(TARGET, id='ceiling', version_code=None),
                dict(TARGET, id='plain', version_code=None, max_app_version=None),
                dict(TARGET, id='disabled', enabled=False)]
        rc, lines = self.run_main(rows, '<div>Version 1.2.3 versionCode 123456</div>')
        self.assertEqual((rc, [l.split()[1] for l in lines]), (0, ['target=fixture']))
        self.assertNotIn('https://', lines[0])

    def test_report_only_until_strict(self):
        # W16y-b (wrong call 115): UNKNOWN and MISSING never fail the probe unless --strict.
        rc, lines = self.run_main([dict(TARGET)], '<html>challenge</html>')
        self.assertEqual((rc, lines[0].split()[0]), (0, 'PIN_STORE_UNKNOWN'))
        rc, _ = self.run_main([dict(TARGET)], '<html>challenge</html>', '--strict')
        self.assertEqual(rc, 1)

    def test_script_numbers_are_not_a_listing(self):
        body = '<html><script>var code = 123456; var version="1.2.3"</script><!-- 1.2.3 --></html>'
        self.assertEqual(self.check(body)['status'], 'UNKNOWN')

    def test_workflow_is_manual_and_read_only(self):
        wf = (ROOT / '.github/workflows/pin-check.yml').read_text()
        self.assertNotIn('schedule:', wf)
        self.assertIn('workflow_dispatch:', wf)
        self.assertIn('contents: read', wf)
        self.assertNotIn('secrets.', wf)


    def test_wrapper_exit_code_decides_first(self):
        # W16y-c review (HIGH): a nonzero wrapper exit never becomes OK, even with matching HTML.
        import tempfile
        good = '<div class="table-row">Version 1.2.3 versionCode 123456</div>'
        with tempfile.TemporaryDirectory() as d:
            ev = Path(d)
            ok = pin._check_wrapped_target(TARGET, APPS, good, 0, ev)
            self.assertEqual(ok['status'], 'OK')
            for rc in (1, 3, 4, 8):
                row = pin._check_wrapped_target(TARGET, APPS, good, rc, ev)
                self.assertEqual((row['status'], row['reason']), ('UNKNOWN', 'wrapper_exit_%d' % rc))
            self.assertEqual(pin._check_wrapped_target(TARGET, APPS, good, 2, ev)['status'], 'MISSING')
            self.assertEqual(pin._check_wrapped_target(TARGET, APPS, None, 0, ev)['status'], 'UNKNOWN')
            bad = '<div class="table-row">Version 1.2.3 versionCode 9</div>'
            self.assertEqual(pin._check_wrapped_target(TARGET, APPS, bad, 0, ev)['status'], 'UNKNOWN')

if __name__ == '__main__':
    unittest.main()
