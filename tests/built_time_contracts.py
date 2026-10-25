"""W16k (owner, 25 Oct 2026: "showing release date and time in pages & Obtainium ... so i know
when last built"): the build job stamps PF_BUILT_AT once; the release record carries it and the
notes open with it (Obtainium shows those notes as the changelog)."""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/build'))
import release_notes as notes  # noqa: E402

DOC = {'schema': 1, 'target': 'telegram', 'label': 'Telegram', 'version': '13.1.0',
       'tag': 'telegram-v13.1.0-b20261025', 'package': 'org.telegram.messenger', 'min_sdk': 29,
       'arch': 'arm64-v8a', 'provider': 'hushtelegram', 'bundle': 'v1', 'patches': ['A'],
       'sha256': 'a' * 64, 'signer': 'b' * 64, 'source': 'c' * 40,
       'apk': 'telegram-v13.1.0-arm64-v8a.apk', 'bytes': 60000000}


class Built(unittest.TestCase):
    def test_line_names_utc_and_ist(self):
        self.assertEqual(notes.built_line('2026-10-25T12:18Z'), 'Built 25 Oct 2026, 12:18 UTC (17:48 IST)')
        self.assertEqual(notes.built_line('2026-10-25T20:00Z'), 'Built 25 Oct 2026, 20:00 UTC (01:30 IST)')

    def test_notes_open_with_it_and_stay_optional(self):
        body = notes.render(dict(DOC, built='2026-10-25T12:18Z'))
        self.assertTrue(body.startswith('Built 25 Oct 2026, 12:18 UTC (17:48 IST)\n\n## Changes'))
        self.assertTrue(notes.render(dict(DOC)).startswith('## Changes'))

    def test_bad_stamps_are_refused(self):
        for bad in ('2026-10-25 12:18', '2026-10-25T12:18:00Z', '', 5):
            with self.assertRaises(ValueError):
                notes.checked(dict(DOC, built=bad))

    def test_workflow_stamps_once_and_contract_reads_it(self):
        wf = (ROOT / '.github/workflows/manual-patch.yml').read_text()
        self.assertEqual(wf.count('PF_BUILT_AT='), 1)
        self.assertIn('echo "PF_BUILT_AT=$(date -u +%Y-%m-%dT%H:%MZ)" >> "$GITHUB_ENV"', wf)
        self.assertIn("fields['built'] = os.environ['PF_BUILT_AT']", (ROOT / 'src/build/release_contract.py').read_text())

    def test_pages_cards_prefer_it(self):
        js = (ROOT / 'docs/portal.js').read_text()
        self.assertIn("typeof record.built==='string'", js)


if __name__ == '__main__':
    unittest.main()
