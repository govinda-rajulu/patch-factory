"""Owner decision memory (packet W16j): one decision per app and name, any provider."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/etc'))
import decisions  # noqa: E402
import selection_watch  # noqa: E402

MEM = {'names': [dict(target='instagram', name='Hide notes tray', call='take', id='N-1', date='d'),
                 dict(target='instagram', name='Allow user network certificate', call='drop', id='N-2', date='d'),
                 dict(target='photos', name='Spoof Widevine / DRM level', call='take', id='N-3', date='d')],
       'watch': [dict(target='facebook', repo='andrewliang25/morphe-patches', take=['x'])],
       'drop_providers': [dict(target='reddit', repo='Santodan/santodan-patches')]}


class Memory(unittest.TestCase):
    def test_norm_ignores_tags_versions_case(self):
        self.assertEqual(decisions.norm('[Feed] Block feed auto refresh'), 'block feed auto refresh')
        self.assertEqual(decisions.norm('Block Facebook Feed ads (573)'), 'block facebook feed ads')
        self.assertEqual(decisions.norm('Hide  Notes-tray'), 'hide notes tray')

    def test_take_adopts_a_rule_hold_from_any_provider(self):
        w = dict(target='instagram', name='hide notes tray', provider='brosssh', tag='', call='hold', why='no description in the community index')
        selection_watch.remember(MEM, [w])
        self.assertEqual(w['call'], 'adopt')
        self.assertIn('DECISIONS.json', w['why'])

    def test_drop_skips_quietly_and_take_never_beats_banned_or_one_bundle_rule(self):
        d = dict(target='instagram', name='Allow user network certificate', tag='', call='hold', why='hold word "certificate"')
        b = dict(target='instagram', name='Hide notes tray', tag='BAN', call='hold', why='matches BANNED')
        o = dict(target='instagram', name='Hide notes tray', tag='', call='hold', why='another bundle of this app offers the same name')
        selection_watch.remember(MEM, [d, b, o])
        self.assertEqual((d['call'], b['call'], o['call']), ('skip', 'hold', 'hold'))

    def test_confirm_take_carries_the_approval(self):
        w = dict(target='photos', name='Spoof Widevine / DRM level', tag='CFM', call='hold', why='matches CONFIRM: owner decides')
        selection_watch.remember(MEM, [w])
        self.assertEqual((w['call'], w.get('approved')), ('adopt', True))

    def test_provider_state(self):
        self.assertEqual(decisions.provider_state(MEM, 'reddit', 'santodan/SANTODAN-patches')[0], 'drop')
        self.assertEqual(decisions.provider_state(MEM, 'facebook', 'andrewliang25/morphe-patches')[0], 'watch')
        self.assertEqual(decisions.provider_state(MEM, 'facebook', 'other/x')[0], None)

    def test_repo_file_is_valid_and_targets_exist(self):
        m = decisions.load(ROOT)
        ids = {t['id'] for t in json.loads((ROOT / 'src/targets.json').read_text())}
        self.assertTrue(m['names'] and m['watch'] and m['drop_providers'])
        for row in m['names'] + m['watch'] + m['drop_providers']:
            self.assertIn(row['target'], ids, row)
        for row in m['names']:
            self.assertIn(row['call'], ('take', 'drop'))


if __name__ == '__main__':
    unittest.main()
