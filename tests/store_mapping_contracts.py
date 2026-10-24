"""Alternate store mappings keep the configured package, variant, and signer gates."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_PURE = {
    'ytmusic': ('com.google.android.apps.youtube.music',
                'https://apkpure.com/youtube-music/com.google.android.apps.youtube.music/download'),
    'adguard': ('com.adguard.android',
                'https://apkpure.com/adguard/com.adguard.android/download'),
    'photos': ('com.google.android.apps.photos',
               'https://apkpure.com/google-photos/com.google.android.apps.photos/download'),
    'truecaller-combo': ('com.truecaller',
                         'https://apkpure.com/truecaller-caller-id-block-for-android-2024/com.truecaller/download'),
}


class StoreMappingContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.targets = {row['id']: row for row in json.loads((ROOT / 'src/targets.json').read_text())}
        cls.apps = json.loads((ROOT / 'src/build/helper/apps.json').read_text())
        cls.publishers = json.loads((ROOT / 'src/build/PUBLISHERS.json').read_text())

    def test_apkpure_pages_match_the_exact_package_and_variant_requirements(self):
        for ident, (package, url) in EXPECTED_PURE.items():
            with self.subTest(target=ident):
                target = self.targets[ident]
                self.assertEqual(target['package'], package)
                self.assertEqual(target.get('source', 'apkmirror'), 'apkmirror')
                self.assertEqual(self.apps['apkpure'][package]['download_url'], url)
                self.assertTrue(url.endswith('/' + package + '/download'))
                self.assertTrue(url[:-len('/download')].startswith('https://apkpure.com/'))
                self.assertIn(package, self.publishers)
                self.assertTrue(self.publishers[package])
        self.assertEqual(self.targets['ytmusic']['arch'], 'arm64-v8a')
        self.assertEqual(self.targets['truecaller-combo']['apk_type'], 'bundle')

    def test_apkmirror_keymapper_page_matches_the_exact_package(self):
        target = self.targets['keymapper']
        self.assertEqual(target['package'], 'io.github.sds100.keymapper')
        self.assertEqual(target['source'], 'apkpure')
        self.assertEqual(target['apk_type'], 'bundle')
        self.assertEqual(self.apps['apkmirror'][target['package']], {
            'list_url': 'https://www.apkmirror.com/uploads/?appcategory=key-mapper-2',
            'org': 'sds100',
            'name': 'key-mapper-2',
        })
        self.assertIn(target['package'], self.publishers)
        self.assertTrue(self.publishers[target['package']])
        self.assertEqual(
            'https://www.apkmirror.com/apk/sds100/key-mapper-2/',
            'https://www.apkmirror.com/apk/' +
            self.apps['apkmirror'][target['package']]['org'] + '/' +
            self.apps['apkmirror'][target['package']]['name'] + '/')

    def test_all_five_alternates_are_present_in_the_opposite_store(self):
        for ident, (package, _) in EXPECTED_PURE.items():
            self.assertIn(package, self.apps['apkpure'])
        self.assertIn('io.github.sds100.keymapper', self.apps['apkmirror'])
