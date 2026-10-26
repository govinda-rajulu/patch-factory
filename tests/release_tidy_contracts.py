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
        self.assertNotIn('## Checks and limitations', new)
        self.assertTrue(new.endswith('[pf-release-v1]: # "eyJhIjoxfQ=="\n'))
        self.assertEqual(t.tidy(new)[1], 'tidy')

    def test_legacy_and_edited_bodies_are_kept(self):
        self.assertEqual(t.tidy('Patch provider(s): x\nBuilt with morphe-desktop.')[1], 'legacy')
        self.assertEqual(t.tidy(OLD.replace('- Not phone-tested', '- Edited'))[1], 'other')
        self.assertEqual(t.tidy(None)[1], 'legacy')


if __name__ == '__main__':
    unittest.main()

class PreviewBinding(unittest.TestCase):
    def test_preview_token_refuses_apply_after_live_plan_changes(self):
        import tempfile
        from unittest import mock
        row = {'id': 17, 'tag_name': 'app-v1', 'body': OLD}
        with tempfile.TemporaryDirectory() as tmp:
            preview = pathlib.Path(tmp) / 'preview.json'
            with mock.patch.object(t, 'releases', return_value=[row]):
                self.assertEqual(t.main(['preview', '--out', str(preview)]), 0)
            token = json.loads(preview.read_text())['token']
            changed = dict(row, body=OLD.replace('## What changed', '## Edited'))
            backup = pathlib.Path(tmp) / 'backup.json'
            with mock.patch.object(t, 'releases', return_value=[changed]):
                with self.assertRaisesRegex(SystemExit, 'does not match the live plan'):
                    t.main(['apply', '--token', token, '--backup', str(backup)])
            self.assertFalse(backup.exists())

    def test_apply_requires_the_preview_token(self):
        import tempfile
        from unittest import mock
        row = {'id': 18, 'tag_name': 'app-v1', 'body': OLD}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(t, 'releases', return_value=[row]):
            with self.assertRaisesRegex(SystemExit, 'needs --token'):
                t.main(['apply', '--backup', str(pathlib.Path(tmp) / 'backup.json')])

    def test_packet_controller_passes_the_token_written_by_preview(self):
        controller = (ROOT / 'docs/review/controllers/packet.tmpl.py').read_text(encoding='utf-8')
        self.assertIn("json.loads((LOGS / 'release-tidy-preview.json').read_text(encoding='utf-8'))['token']", controller)
        apply = controller[controller.index("'src/etc/release_tidy.py', 'apply'"):controller.index("last = (out.decode", controller.index("'src/etc/release_tidy.py', 'apply'"))]
        self.assertIn("'--token', tidy_token", apply)
