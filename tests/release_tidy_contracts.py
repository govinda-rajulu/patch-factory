import json, pathlib, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/etc')); sys.path.insert(0, str(ROOT / 'src/build'))
import release_tidy as t

OLD = ('## What changed\n- x\n\n</details>\n\n' + t.CHECKS + '## Download evidence\nFile: `a.apk`\n\n'
       '## Help and stable information\n[Install, updates, source types and status meanings](' + t.WEB + '/blob/' + 'a' * 40 + '/docs/guide.md)\n'
       'No automatic uninstall, import migration or device-protection bypass is required or recommended.\n\n[pf-release-v1]: # "eyJhIjoxfQ=="\n')


class Tidy(unittest.TestCase):
    def test_structured_body_loses_both_blocks_and_keeps_marker(self):
        new, why = t.tidy(OLD)
        self.assertEqual(why, 'change')
        self.assertNotIn('## Checks and limitations', new); self.assertNotIn('## Help and stable', new)
        self.assertIn('#about-these-builds)', new)
        self.assertTrue(new.endswith('[pf-release-v1]: # "eyJhIjoxfQ=="\n'))
        self.assertEqual(t.tidy(new)[1], 'tidy')

    def test_legacy_and_edited_bodies_are_kept(self):
        self.assertEqual(t.tidy('Patch provider(s): x\nBuilt with morphe-desktop.')[1], 'legacy')
        self.assertEqual(t.tidy(OLD.replace('- Not phone-tested', '- Edited'))[1], 'other')
        self.assertEqual(t.tidy(None)[1], 'legacy')


if __name__ == '__main__':
    unittest.main()
