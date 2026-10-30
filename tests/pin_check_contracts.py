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


class PinCheck(unittest.TestCase):
    def check(self, body, target=TARGET):
        return pin.check_target(target, APPS, lambda _url: body)

    def test_exact_code_and_ceiling_are_ok(self):
        row = self.check('<div>Version 1.2.3 versionCode 123456</div>')
        self.assertEqual((row['status'], pin.line(row)), ('OK', 'PIN_STORE_OK target=fixture store=apkmirror version=1.2.3 code=123456'))

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


if __name__ == '__main__':
    unittest.main()
