"""Contracts for the W16o stdlib replacement for pup."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'src/build/html_select.py'
HTML = '''<!doctype html>
<h5 class="appRowTitle"><a class="fontBlack" href="/stable/?v=1"> App &amp; One <!-- hidden comment --> 1.2.3 </a></h5>
<h5 class="appRowTitle"><a class="fontBlack" href="/beta/?v=2"> Beta <!-- hidden beta comment --> 1.2.4 beta </a></h5>
<div class="variants-table"><!-- table comment --><div class="table-row"><span class="apkm-badge">APK</span><a class="accent_color" href="/variant/">variant</a></div></div>
<a class="downloadButton" href="/step/?forcebaseapk=true&amp;x=1">APK<!-- button comment --></a><a class="downloadButton" href="/step/bundle">BUNDLE</a>
<a id="download-link" href="/binary?token=1&amp;x=2">final<!-- final comment --></a>
<h2> Version <!-- version comment --> <b>1.2.3</b> </h2>
<a id="download_link" href="https://download.example.invalid/app.apk?x=1&amp;y=2">download<!-- link comment --></a>
'''


class HtmlSelectContracts(unittest.TestCase):
    def run_selector(self, selector, html=HTML):
        return subprocess.run([sys.executable, str(HELPER), selector], input=html.encode(),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def test_every_inventory_selector(self):
        cases = {
            'h5.appRowTitle a.fontBlack json{}': '[{"text":"App & One  1.2.3","href":"/stable/?v=1"},{"text":"Beta  1.2.4 beta","href":"/beta/?v=2"}]\n',
            'h5.appRowTitle a.fontBlack attr{href}': '/stable/?v=1\n/beta/?v=2\n',
            'div.variants-table': '<div class="variants-table"><!-- table comment --><div class="table-row"><span class="apkm-badge">APK</span><a class="accent_color" href="/variant/">variant</a></div></div>\n',
            'a.downloadButton attr{href}': '/step/?forcebaseapk=true&x=1\n/step/bundle\n',
            'a#download-link attr{href}': '/binary?token=1&x=2\n',
            'h2 text{}': 'Version  1.2.3\n',
            'a#download_link attr{href}': 'https://download.example.invalid/app.apk?x=1&y=2\n',
        }
        for selector, expected in cases.items():
            with self.subTest(selector=selector):
                result = self.run_selector(selector)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertEqual(result.stdout.decode(), expected)

    def test_json_is_valid_and_missing_href_is_allowed(self):
        result = self.run_selector('h5.appRowTitle a.fontBlack json{}', '<h5 class="appRowTitle"><a class="fontBlack">No link</a></h5>')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout), [{'text': 'No link'}])

    def test_bad_usage(self):
        for args, data in [([], b''), (['a > b'], b'<a><b>x</b></a>'), (['a attr{href'], b'<a></a>')]:
            with self.subTest(args=args):
                result = subprocess.run([sys.executable, str(HELPER), *args], input=data,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'html_select.py:', result.stderr)

    def test_oversize_input_is_rejected(self):
        result = self.run_selector('h2 text{}', 'x' * (16 * 1024 * 1024 + 1))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'input exceeds', result.stderr)


if __name__ == '__main__':
    unittest.main()
