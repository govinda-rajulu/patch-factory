"""Tooling watch contracts (packet W1, 8 Oct 2026): pins follow the newest release,
pre-releases included, bytes verified, and a change only ever becomes a pull request."""
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'etc'))
import tooling_watch as tw  # noqa: E402

PIN = ('apkeditor|https://github.com/REAndroid/APKEditor/releases/download/V1.4.9/APKEditor-1.4.9.jar|'
       + 'a' * 64 + '|./APKEditor.jar')


def rel(tag, when, pre=False, draft=False, assets=()):
    return {'tag_name': tag, 'published_at': when, 'prerelease': pre, 'draft': draft, 'html_url': 'u',
            'assets': [{'name': n, 'browser_download_url': 'https://github.com/REAndroid/APKEditor/releases/download/%s/%s' % (tag, n),
                        'digest': d} for n, d in assets]}


class Watch(unittest.TestCase):
    def test_newest_counts_prereleases_and_skips_drafts(self):
        rows = [rel('V1.4.9', '2026-01-01T00:00:00Z'), rel('V1.5.0', '2026-03-01T00:00:00Z', pre=True),
                rel('V1.6.0', '2026-04-01T00:00:00Z', draft=True)]
        self.assertEqual(tw.newest(rows)['tag_name'], 'V1.5.0')

    def test_asset_name_swaps_the_version(self):
        self.assertEqual(tw.asset_name('APKEditor-1.4.9.jar', 'V1.4.9', 'V1.5.0'), 'APKEditor-1.5.0.jar')
        self.assertEqual(tw.asset_name('pup_v0.4.0_linux_amd64.zip', 'v0.4.0', 'v0.5.0'), 'pup_v0.5.0_linux_amd64.zip')
        self.assertIsNone(tw.asset_name('tool.jar', 'v1', 'v2'))

    def test_update_current_missing_and_mismatch(self):
        pins = tw.parse_pins(PIN)
        data = b'new jar bytes'
        good = 'sha256:' + hashlib.sha256(data).hexdigest()
        cases = {
            'UPDATE': [rel('V1.5.0', '2026-03-01T00:00:00Z', pre=True, assets=[('APKEditor-1.5.0.jar', good)])],
            'CURRENT': [rel('V1.4.9', '2026-01-01T00:00:00Z')],
            'ASSET_NOT_FOUND': [rel('V1.5.0', '2026-03-01T00:00:00Z', assets=[('other.jar', good)])],
            'DIGEST_MISMATCH': [rel('V1.5.0', '2026-03-01T00:00:00Z', assets=[('APKEditor-1.5.0.jar', 'sha256:' + 'b' * 64)])],
        }
        for status, releases in cases.items():
            row = tw.plan(pins, {}, fetch_releases=lambda o, r: releases, fetch_bytes=lambda u: data)[0]
            self.assertEqual(row['status'], status)
        row = tw.plan(pins, {}, fetch_releases=lambda o, r: cases['UPDATE'], fetch_bytes=lambda u: data)[0]
        self.assertTrue(row['prerelease'])
        self.assertEqual(row['new_line'].split('|')[2], hashlib.sha256(data).hexdigest())
        self.assertTrue(row['new_line'].endswith('|./APKEditor.jar'))

    def test_workflow_only_opens_pull_requests(self):
        text = (ROOT / '.github' / 'workflows' / 'tooling-watch.yml').read_text(encoding='utf-8')
        self.assertIn('git push origin "$B"', text)
        self.assertNotIn('git push origin main', text)
        self.assertNotIn('git push\n', text)
        self.assertIn('gh pr create', text)
        self.assertIn('gh workflow run validate.yml', text)


if __name__ == '__main__':
    unittest.main()
