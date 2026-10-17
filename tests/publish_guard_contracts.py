"""W15 (17 Oct 2026, L059): a build never publishes an app version below the newest published
release of that app. De-Vanced Facebook 580 (3 patches) went out four times, 11 to 16 Oct,
over Hushfacebook 582 (82 patches) because nothing compared versions before publishing."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/build'))
import release_notes as notes  # noqa: E402

CUR = {'target': 'facebook', 'tag': 'facebook-v580.0.0.51.74-b2026101600000000038968981413000001',
       'version': '580.0.0.51.74'}


def rel(tag, **kw):
    return dict({'id': hash(tag) & 0xffff, 'tag_name': tag}, **kw)


class Guard(unittest.TestCase):
    def test_fallback_below_published_primary_is_refused(self):
        rows = [rel('facebook-v582.0.0.50.54-b2026101100000000038100000000000001')]
        why = notes.publish_guard(CUR, rows, True)
        self.assertIn('older than the published 582.0.0.50.54', why)

    def test_primary_below_published_is_refused_too(self):
        rows = [rel('facebook-v582.0.0.50.54-b20261011')]
        self.assertIsNotNone(notes.publish_guard(CUR, rows, False))

    def test_same_or_newer_version_publishes(self):
        for tag in ('facebook-v580.0.0.51.74-b20261011', 'facebook-v579.9.9.9.9-b20261011',
                    'facebook-v58.0-b20261011'):
            self.assertIsNone(notes.publish_guard(CUR, [rel(tag)], True), tag)
        self.assertIsNone(notes.publish_guard(CUR, [], True))

    def test_numeric_not_string_order(self):
        cur = dict(CUR, tag='x-v10.0-b20261011', version='10.0')
        self.assertIsNone(notes.publish_guard(cur, [rel('x-v9.9-b20261010')], False))
        self.assertIsNotNone(notes.publish_guard(cur, [rel('x-v10.1-b20261010')], False))

    def test_other_apps_drafts_and_prereleases_do_not_count(self):
        rows = [rel('facebook-lite-v999.0-b20261011'), rel('instagram-v999.0-b20261011'),
                rel('facebook-v999.0-b20261011', draft=True), rel('facebook-v999.0-b20261012', prerelease=True),
                rel('facebook-v999.0'), 'junk', rel('facebook-v999-b20261011x')]
        self.assertIsNone(notes.publish_guard(CUR, rows, True))

    def test_unreadable_inventory_blocks_only_a_fallback(self):
        self.assertIn('not published blind', notes.publish_guard(CUR, None, True))
        self.assertIsNone(notes.publish_guard(CUR, None, False))

    def test_release_contract_runs_the_guard_before_the_notes(self):
        text = (ROOT / 'src/build/release_contract.py').read_text(encoding='utf-8')
        guard = text.index('release_notes.publish_guard(summary, rows')
        self.assertLess(text.index('rows = release_notes.inventory()'), guard)
        self.assertLess(guard, text.index('release_notes.previous_release(summary, rows)'))
        self.assertIn("raise ValueError('PUBLISH_REFUSED '", text)


if __name__ == '__main__':
    unittest.main()
