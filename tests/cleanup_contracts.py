"""Cleanup: preview and apply build the same list; apply refuses a changed list (W4)."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/etc'))
spec = importlib.util.spec_from_file_location('cleanup', ROOT / 'src/etc/cleanup.py')
cl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cl)
WEB = 'https://github.com/' + cl.REPO
MARK = 'Built in public CI with [morphe-desktop](https://github.com/MorpheApp/morphe-desktop).'


def rel(i, day, prefix='adguard'):
    tag = '%s-v1.%d-b202609%02d' % (prefix, i, day)
    name = '%s-v1.%d-arm64-v8a.apk' % (prefix, i)
    return {'id': i, 'tag_name': tag, 'name': tag, 'draft': False, 'prerelease': False, 'body': MARK,
            'published_at': '2026-09-%02dT00:00:00Z' % day, 'html_url': WEB + '/releases/tag/' + tag,
            'assets': [{'name': name, 'size': 2000000, 'digest': 'sha256:' + 'a' * 64}]}


class Fake:
    def __init__(self, releases, tagnames):
        self.releases, self.tags, self.deleted = releases, tagnames, []

    def __call__(self, cmd, **kw):
        out = ''
        if cmd[:2] == ['git', 'ls-remote']:
            out = ''.join('%040x\trefs/tags/%s\n' % (n, t) for n, t in enumerate(self.tags))
        elif cmd[:3] == ['gh', 'api', '-X']:
            self.deleted.append(cmd[4])
        elif cmd[:2] == ['gh', 'api']:
            out = json.dumps(self.releases if cmd[2].endswith('page=1') else [])
        return subprocess.CompletedProcess(cmd, 0, out, '')


class Cleanup(unittest.TestCase):
    def setUp(self):
        self.old = os.getcwd()
        self.tmp = tempfile.TemporaryDirectory()
        os.chdir(self.tmp.name)
        Path('src').mkdir()
        Path('src/targets.json').write_text(json.dumps([{'id': 'adguard', 'enabled': True}]))
        rows = [rel(1, 1), rel(2, 2), rel(3, 3)]
        self.fake = Fake(rows, [r['tag_name'] for r in rows] + ['adguard-v0.9-b20260801', 'v1.0-manual'])

    def tearDown(self):
        os.chdir(self.old)
        self.tmp.cleanup()

    def preview(self):
        out = Path('p.json')
        self.assertEqual(cl.main(['preview', '--out', str(out)], run=self.fake), 0)
        return json.loads(out.read_text())

    def test_keeps_two_newest_and_non_build_tags(self):
        p = self.preview()
        self.assertEqual([r['tag'] for r in p['releases']], ['adguard-v1.1-b20260901'])
        self.assertEqual(p['tags'], ['adguard-v0.9-b20260801', 'adguard-v1.1-b20260901'])
        self.assertNotIn('v1.0-manual', p['tags'])
        self.assertEqual(self.fake.deleted, [])

    def test_apply_needs_the_preview_token_and_writes_a_receipt_first(self):
        p = self.preview()
        self.assertEqual(cl.main(['apply', '--token', 'wrong'], run=self.fake), 1)
        self.assertEqual(self.fake.deleted, [])
        self.assertEqual(cl.main(['apply', '--token', p['token'], '--receipt', 'r.json'], run=self.fake), 0)
        rec = json.loads(Path('r.json').read_text())
        self.assertEqual(rec['releases'][0]['assets'][0]['digest'], 'sha256:' + 'a' * 64)
        self.assertEqual(self.fake.deleted, ['repos/%s/releases/1' % cl.REPO,
                                             'repos/%s/git/refs/tags/adguard-v0.9-b20260801' % cl.REPO,
                                             'repos/%s/git/refs/tags/adguard-v1.1-b20260901' % cl.REPO])

    def test_a_new_release_after_preview_changes_the_token(self):
        p = self.preview()
        self.fake.releases.append(rel(4, 4))
        self.fake.tags.append('adguard-v1.4-b20260904')
        self.assertEqual(cl.main(['apply', '--token', p['token']], run=self.fake), 1)
        self.assertEqual(self.fake.deleted, [])


if __name__ == '__main__':
    unittest.main()
