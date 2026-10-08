"""Contracts for src/etc/app.py, the one tool behind "5. Add target" (packet W2, 8 Oct 2026).

Runs on a small synthetic repository in a temp folder: no network, no generators.
"""
import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PORTAL = """const LOGOS=new Set(['youtube','photos']);
const GROUPS=[
 ['media','Watch & listen',['youtube']],
 ['social','Social & communities',[]],
 ['tools','Everyday essentials',['photos']]
];
"""


class AppTool(unittest.TestCase):
    def setUp(self):
        self.old = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        os.chdir(self.tmp)
        os.environ['PF_DATE'] = '2026-10-08'
        for d in ('src/patches/youtube-morphe', 'src/patches/gg-photos', 'src/build/helper', 'src/options',
                  'docs/assets/logos', 'src/etc'):
            Path(d).mkdir(parents=True)
        Path('src/patches/BANNED').write_text('# banned\nchange signature\n')
        Path('src/patches/CONFIRM').write_text('spoof\n')
        Path('src/patches/youtube-morphe/include-patches').write_text('')
        Path('src/patches/youtube-morphe/exclude-patches').write_text('Announcements\n')
        Path('src/patches/gg-photos/include-patches').write_text('GmsCore support\nSpoof features\n')
        Path('src/patches/gg-photos/exclude-patches').write_text('')
        targets = [
            {'id': 'youtube', 'enabled': True, 'package': 'com.google.android.youtube', 'pin': 'morphe',
             'candidates': [{'name': 'morphe', 'owner': 'MorpheApp', 'repo': 'morphe-patches', 'channel': 'prerelease',
                             'patch_dir': 'youtube-morphe', 'options': 'morphe'}], 'tag_prefix': 'youtube-morphe',
             'poll': True, 'label': 'YouTube'},
            {'id': 'photos', 'enabled': True, 'package': 'com.google.android.apps.photos', 'pin': None,
             'candidates': [{'name': 'rushiranpise', 'owner': 'rushiranpise', 'repo': 'morphe-patches',
                             'channel': 'prerelease', 'patch_dir': 'gg-photos', 'options': 'rushiranpise'}],
             'tag_prefix': 'gg-photos', 'poll': True, 'exclusive': True, 'label': 'Google Photos'}]
        Path('src/targets.json').write_text(json.dumps(targets, indent=2) + '\n')
        Path('src/build/helper/apps.json').write_text(json.dumps({'apkmirror': {}, 'apkpure': {}}, indent=1) + '\n')
        Path('src/build/helper/source-fallbacks.json').write_text('{\n  "schema": 1,\n  "targets": {}\n}\n')
        Path('docs/portal.js').write_text(PORTAL)
        Path('docs/assets/logos/photos.png').write_bytes(b'png')
        shutil.copy(ROOT / 'src/etc/app.py', 'src/etc/app.py')
        self.app = load('pf_app', Path(self.tmp) / 'src/etc/app.py')

    def tearDown(self):
        os.chdir(self.old)
        shutil.rmtree(self.tmp)
        os.environ.pop('PF_DATE', None)

    def run_app(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = self.app.main(list(argv) + ['--no-regen'])
        return rc, out.getvalue()

    def targets(self):
        return json.loads(Path('src/targets.json').read_text())

    def test_add_is_one_command_and_writes_every_file(self):
        rc, out = self.run_app('add', 'demomusic', '--package', 'com.example.music', '--label', 'Demo Music',
                               '--provider', 'SomeOwner/some-patches', '--patches', 'Hide ads; Unlock HD',
                               '--source', 'apkmirror-bundle', '--store-url', 'https://www.apkmirror.com/apk/amazon/x/',
                               '--group', 'media')
        self.assertEqual(rc, 0, out)
        t = [x for x in self.targets() if x['id'] == 'demomusic'][0]
        self.assertTrue(t['enabled'] and t['poll'] and t['exclusive'])
        self.assertEqual(t['candidates'][0]['patch_dir'], 'demomusic-someowner')
        self.assertEqual(Path('src/patches/demomusic-someowner/include-patches').read_text(), 'Hide ads\nUnlock HD\n')
        self.assertTrue(Path('src/patches/demomusic-someowner/exclude-patches').is_file())
        self.assertEqual(Path('src/options/someowner.json').read_text(), '[]\n')
        apps = json.loads(Path('src/build/helper/apps.json').read_text())
        self.assertEqual(apps['apkmirror']['com.example.music'], {'org': 'amazon', 'name': 'x',
                         'list_url': 'https://www.apkmirror.com/uploads/?appcategory=x'})
        fb = json.loads(Path('src/build/helper/source-fallbacks.json').read_text())
        self.assertEqual(fb['targets']['demomusic']['admissions'], [])
        rec = Path('docs/review/onboarding/demomusic.md').read_text()
        for must in ('SomeOwner/some-patches', '- Hide ads:', '- Unlock HD:', 'com.example.music'):
            self.assertIn(must, rec)
        self.assertNotIn('TODO', rec)
        self.assertIn("['youtube','demomusic']", Path('docs/portal.js').read_text())

    @unittest.skipUnless((ROOT / 'src/etc/onboard_check.py').is_file(), 'onboarding gate not in this tree')
    def test_record_satisfies_the_onboarding_check(self):
        base = Path(self.tmp) / 'base'
        shutil.copytree('src', base / 'src')
        rc, out = self.run_app('add', 'linkedin', '--package', 'com.linkedin.android', '--label', 'LinkedIn',
                               '--provider', 'Owner/repo', '--patches', 'Hide ads',
                               '--store-url', 'https://www.apkmirror.com/apk/linkedin/')
        self.assertEqual(rc, 0, out)
        check = load('pf_onboard', ROOT / 'src/etc/onboard_check.py')
        m = check.check(str(base), self.tmp)
        self.assertTrue(m['onboarding'])
        self.assertEqual(m['problems'], [])

    def test_add_without_patches_stays_disabled(self):
        rc, out = self.run_app('add', 'newapp', '--package', 'com.example.app', '--label', 'New',
                               '--provider', 'Owner/repo')
        self.assertEqual(rc, 0, out)
        t = [x for x in self.targets() if x['id'] == 'newapp'][0]
        self.assertFalse(t['enabled'])
        self.assertIn('DISABLED', out)
        rc, out = self.run_app('enable', 'newapp')
        self.assertEqual(rc, 1)
        self.assertIn('empty include list', out)

    def test_banned_never_and_confirm_needs_the_owner(self):
        rc, out = self.run_app('patch', 'photos', '--patches', 'Change signature check')
        self.assertEqual(rc, 1)
        self.assertIn('BANNED', out)
        rc, out = self.run_app('patch', 'photos', '--patches', 'Spoof device')
        self.assertEqual(rc, 1)
        self.assertIn('approve_confirm', out)
        self.assertNotIn('Spoof device', Path('src/patches/gg-photos/include-patches').read_text())
        rc, out = self.run_app('patch', 'photos', '--patches', 'Spoof device', '--approve-confirm')
        self.assertEqual(rc, 0, out)
        self.assertIn('Owner approved: Spoof device', Path('docs/review/onboarding/photos.md').read_text())

    def test_patch_rule_list_mode_and_defaults_mode(self):
        rc, out = self.run_app('patch', 'photos', '--patches', 'New one; -Spoof features')
        self.assertEqual(rc, 0, out)
        self.assertEqual(Path('src/patches/gg-photos/include-patches').read_text(), 'GmsCore support\nNew one\n')
        rc, out = self.run_app('patch', 'photos', '--patches', '-GmsCore support; -New one')
        self.assertEqual(rc, 1)
        self.assertIn('empty the include list', out)
        rc, out = self.run_app('patch', 'youtube', '--patches', '-Shorts; Announcements')
        self.assertEqual(rc, 0, out)
        self.assertEqual(Path('src/patches/youtube-morphe/exclude-patches').read_text(), 'Shorts\n')
        self.assertEqual(Path('src/patches/youtube-morphe/include-patches').read_text(), '')

    def test_disable_keeps_files_and_hides_logo_enable_restores(self):
        rc, out = self.run_app('disable', 'photos')
        self.assertEqual(rc, 0, out)
        self.assertFalse([x for x in self.targets() if x['id'] == 'photos'][0]['enabled'])
        self.assertIn("new Set(['youtube'])", Path('docs/portal.js').read_text())
        self.assertIn("['photos']", Path('docs/portal.js').read_text())
        rc, out = self.run_app('enable', 'photos')
        self.assertEqual(rc, 0, out)
        self.assertIn("new Set(['photos','youtube'])", Path('docs/portal.js').read_text())

    def test_remove_moves_folders_to_attic_and_keeps_history(self):
        rc, out = self.run_app('remove', 'photos')
        self.assertEqual(rc, 0, out)
        self.assertEqual([x['id'] for x in self.targets()], ['youtube'])
        self.assertFalse(Path('src/patches/gg-photos').exists())
        self.assertTrue(Path('src/patches/_attic/gg-photos/include-patches').is_file())
        js = Path('docs/portal.js').read_text()
        self.assertNotIn("'photos'", js)
        self.assertTrue(Path('docs/assets/logos/photos.png').is_file())

    def test_workflow_inputs_arrive_as_environment_only(self):
        env = {'PF_ACTION': 'patch', 'PF_ID': 'photos', 'PF_PATCHES': 'X', 'PF_SOURCE': 'apkpure',
               'PF_PACKAGE': 'ignored.for.patch', 'PF_APPROVE_CONFIRM': 'false'}
        old = {k: os.environ.get(k) for k in env}
        os.environ.update(env)
        try:
            self.assertEqual(self.app.from_env(), ['patch', 'photos', '--patches', 'X'])
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_refuses_bad_input(self):
        for argv in (['add', 'Bad_ID', '--package', 'com.x.y', '--label', 'X', '--provider', 'a/b'],
                     ['add', 'ok', '--package', 'nopackage', '--label', 'X', '--provider', 'a/b'],
                     ['add', 'ok', '--package', 'com.x.y', '--label', 'X', '--provider', 'not a repo'],
                     ['add', 'youtube', '--package', 'com.x.y', '--label', 'X', '--provider', 'a/b'],
                     ['add', 'ok', '--package', 'com.x.y', '--label', 'X', '--provider', 'a/b',
                      '--store-url', 'http://evil.example/'],
                     ['add', 'ok', '--package', 'com.x.y', '--label', 'X', '--provider', 'gitlab.com/x/y']):
            rc, out = self.run_app(*argv)
            self.assertEqual(rc, 1, argv)
            self.assertIn('REFUSED', out)
        self.assertFalse(Path('src/patches/ok-a').exists())


if __name__ == '__main__':
    unittest.main()
