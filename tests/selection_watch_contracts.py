"""Selection watch (packet W13): gone names leave the selection, new names wait, caps hold.

Runs on a throwaway copy of this repository with a fake name reader. No network.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/etc'))
import selection_watch as sw  # noqa: E402


class Watch(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.r = Path(self.t.name) / 'repo'
        self.r.mkdir()
        for d in ('src', 'docs'):
            shutil.copytree(ROOT / d, self.r / d)
        for c in (['init', '-q'], ['add', '-A'], ['-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'x']):
            subprocess.run(['git', *c], cwd=self.r, check=True)
        self.out = Path(self.t.name) / 'out'
        self.base = {}
        for row in sw.provider_watch.inventory(json.loads((self.r / 'src/targets.json').read_text())):
            names = sw.lines(self.r / 'docs/review/providers' / row['baseline'])
            inc = [l.split('|', 1)[0] for l in sw.lines(self.r / 'src/patches' / row['patch_dir'] / 'include-patches')]
            self.base[row['target'] + '/' + row['name']] = sorted(set(names) | set(inc))

    def observe(self, changes):
        def fn(row):
            key = row['target'] + '/' + row['name']
            names = set(self.base[key])
            for n in changes.get(key, {}).get('remove', []):
                names.discard(n)
            names |= set(changes.get(key, {}).get('add', []))
            if changes.get(key) == 'fail':
                raise ValueError('down')
            return dict(names=sorted(names))
        return fn

    def releases(self, path):
        return [dict(tag_name='v2', published_at='2026-10-10T00:00:00Z', html_url='u', body='- Added patch X\n- chore'),
                dict(tag_name='v1', published_at='2026-10-01T00:00:00Z', html_url='u', body='old')]

    def collect(self, changes, state=None):
        return sw.collect(self.r, self.out, self.observe(changes), reader=self.releases, state_text=state)

    def test_gone_chosen_name_is_removed_and_committed(self):
        p = self.collect({'instagram/piko': {'remove': ['Copy comment'], 'add': ['Brand new']}})
        self.assertEqual(p['edits']['instagram-piko']['include'], ['Copy comment'])
        self.assertEqual([w['name'] for w in p['waiting'] if w['provider'] == 'piko'], ['Brand new'])
        self.assertEqual(sw.apply(self.r, self.out, push=False), 'COMMITTED')
        inc = (self.r / 'src/patches/instagram-piko/include-patches').read_text().splitlines()
        self.assertNotIn('Copy comment', inc)
        self.assertIn('Copy comment', subprocess.run(['git', 'log', '-1', '--format=%B'], cwd=self.r,
                                                     capture_output=True, text=True).stdout)
        state = (self.out / 'state.json').read_text()
        again = self.collect({'instagram/piko': {'remove': ['Copy comment'], 'add': ['Brand new']}}, state)
        self.assertEqual([w['name'] for w in again['waiting'] if w['provider'] == 'piko'], ['Brand new'])

    def test_open_mode_new_name_ships_by_default_and_never_waits(self):
        # W14: YouTube (no include list) waited on Force system font, which already ships
        p = self.collect({'youtube/morphe': {'add': ['Brand new open patch']}})
        self.assertEqual([w['name'] for w in p['waiting'] if w['target'] == 'youtube'], [])
        self.assertEqual([w['name'] for w in p['defaults']], ['Brand new open patch'])
        text = (self.out / 'report.md').read_text()
        self.assertIn("## New in open-mode apps (1)", text)
        self.assertIn('patches `-Brand new open patch`', text)
        self.assertNotIn('youtube/morphe', json.loads((self.out / 'state.json').read_text())['pending'].__repr__())

    def test_reminder_fires_on_the_provider_version(self):
        # W14: "revisit HushGram as primary after 0.1" became a reminder, not a memory
        rows = [dict(repo='SysAdminDoc/HushGram', at_least='0.1.0', say='revisit')]
        (self.r / 'src/etc/reminders.json').write_text(json.dumps(rows))
        self.assertEqual(sw.reminders(self.r, {'SysAdminDoc/HushGram': 'v0.0.9'}), [])
        self.assertEqual(sw.reminders(self.r, {'SysAdminDoc/HushGram': 'v0.1.0'}), ['SysAdminDoc/HushGram v0.1.0: revisit'])
        self.assertEqual(len(sw.reminders(self.r, {'SysAdminDoc/HushGram': 'v1.2'})), 1)
        committed = json.loads((ROOT / 'src/etc/reminders.json').read_text())
        self.assertTrue(any(r['repo'] == 'SysAdminDoc/HushGram' for r in committed))

    def test_mass_loss_is_blocked_not_removed(self):
        inc = sw.lines(self.r / 'src/patches/instagram-piko/include-patches')
        p = self.collect({'instagram/piko': {'remove': inc[:20]}})
        self.assertNotIn('instagram-piko', p['edits'])
        self.assertTrue(any('instagram/piko' in b for b in p['blocked']))

    def test_unreadable_provider_changes_nothing(self):
        p = self.collect({'instagram/piko': 'fail'})
        self.assertNotIn('instagram-piko', p['edits'])
        self.assertTrue(any('instagram/piko' in f for f in p['findings']))

    def test_digest_first_run_shows_newest_then_only_new(self):
        self.collect({})
        text = (self.out / 'report.md').read_text()
        self.assertIn('v2', text)
        self.assertIn('Added patch X', text)
        self.assertNotIn('chore', text)
        state = (self.out / 'state.json').read_text()
        self.collect({}, state)
        self.assertNotIn('**MorpheApp/morphe-patches v2', (self.out / 'report.md').read_text())

    def test_ranking_line_per_enabled_app(self):
        rank = sw.ranking(self.r, json.loads((self.r / 'src/targets.json').read_text()))
        self.assertTrue(any(r.startswith('instagram: ') for r in rank))

    def test_ranking_reads_both_shapes_and_skips_fallbacks(self):
        # W13 pf-t1: Facebook showed the fallback De-Vanced as "now" and HushFacebook offering 0
        rank = sw.ranking(self.r, json.loads((self.r / 'src/targets.json').read_text()))
        fb = [r for r in rank if r.startswith('facebook: ')][0]
        self.assertIn('now SysAdminDoc/Hushfacebook', fb)
        self.assertNotIn('De-Vanced', fb)
        self.assertNotIn('(0 offered', fb)
        ig = [r for r in rank if r.startswith('instagram: ')][0]
        self.assertNotIn('HushGram', ig)


if __name__ == '__main__':
    unittest.main()
