"""Cleanup: preview and apply build the same list; apply refuses a changed list (W4).

W9: Pages deployment records (newest 5 stay) and merged packet branches are in the same list.
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
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


def dep(i, day, env='github-pages'):
    return {'id': 9000 + i, 'environment': env, 'created_at': '2026-10-%02dT00:00:00Z' % day,
            'sha': '%040x' % (0xd00 + i), 'ref': 'main', 'task': 'deploy'}


IN_MAIN, NOT_IN_MAIN = 'a' * 40, 'b' * 40


class Fake:
    """GitHub as cleanup.py sees it: gh api paths and git ls-remote. Records every DELETE."""
    def __init__(self, releases, tagnames):
        self.releases, self.tags, self.deleted = releases, tagnames, []
        self.deploys, self.branches, self.pulls, self.fail_on = [], [], [], None
        self.reads = []

    def page(self, rows, path):
        return rows if path.endswith('page=1') else []

    def __call__(self, cmd, **kw):
        out = ''
        if cmd[:2] == ['git', 'ls-remote']:
            out = ''.join('%040x\trefs/tags/%s\n' % (n, t) for n, t in enumerate(self.tags))
        elif cmd[:3] == ['gh', 'api', '-X']:
            if self.fail_on and self.fail_on in cmd[4]:
                return subprocess.CompletedProcess(cmd, 1, '', 'HTTP 422: refused')
            self.deleted.append(cmd[4])
        elif cmd[:2] == ['gh', 'api']:
            path = cmd[2]
            self.reads.append(path)
            if '/compare/' in path:
                out = 'ahead\n' if path.split('/compare/')[1].startswith(IN_MAIN) else 'diverged\n'
            elif '/deployments' in path:
                out = json.dumps(self.page(self.deploys, path))
            elif '/branches' in path:
                out = json.dumps(self.page(self.branches, path))
            elif '/pulls' in path:
                out = json.dumps(self.page(self.pulls, path))
            else:
                out = json.dumps(self.page(self.releases, path))
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

    def test_only_two_newest_per_app_stay_whatever_layout_author_or_marker(self):
        odd = rel(5, 5)
        odd['assets'].append({'name': 'microg.apk', 'size': 10, 'id': 9})
        mine = rel(6, 6)
        mine['author'] = {'login': 'govinda-rajulu', 'id': 285203866}
        frozen = rel(7, 7)
        frozen['body'] = MARK + ' keep forever'
        other = rel(1, 1, prefix='tc-combo')
        odd_tag = dict(rel(2, 2), tag_name='v1.0-manual', id=20)
        self.fake.releases[:] = [odd, mine, frozen, rel(8, 8), rel(9, 9), other, odd_tag]
        p = self.preview()
        self.assertEqual([r['tag'] for r in p['releases']],
                         ['adguard-v1.5-b20260905', 'adguard-v1.6-b20260906', 'adguard-v1.7-b20260907'])
        kept = {k['tag']: k['reason'] for k in p['kept']}
        self.assertEqual(kept, {'adguard-v1.8-b20260908': 'two newest of adguard',
                                'adguard-v1.9-b20260909': 'two newest of adguard',
                                'tc-combo-v1.1-b20260901': 'two newest of tc-combo',
                                'v1.0-manual': 'not an app build tag'})

    def test_a_new_release_after_preview_changes_the_token(self):
        p = self.preview()
        self.fake.releases.append(rel(4, 4))
        self.fake.tags.append('adguard-v1.4-b20260904')
        self.assertEqual(cl.main(['apply', '--token', p['token']], run=self.fake), 1)
        self.assertEqual(self.fake.deleted, [])


    # W9: Pages deployment records and merged packet branches join the same preview and token.
    def with_more(self):
        self.fake.deploys[:] = [dep(i, i) for i in range(1, 8)]
        self.fake.branches[:] = [{'name': 'main', 'commit': {'sha': IN_MAIN}},
                                 {'name': 'status', 'commit': {'sha': NOT_IN_MAIN}},
                                 {'name': 'feature', 'commit': {'sha': IN_MAIN}},
                                 {'name': 'packet/w8', 'commit': {'sha': IN_MAIN}},
                                 {'name': 'packet/w10', 'commit': {'sha': NOT_IN_MAIN}},
                                 {'name': 'packet/open', 'commit': {'sha': IN_MAIN}}]
        self.fake.pulls[:] = [{'id': 70007, 'number': 7, 'head': {'ref': 'packet/open', 'repo': {'full_name': cl.REPO}}}]

    def test_pages_deployments_keep_the_newest_five(self):
        self.with_more()
        p = self.preview()
        self.assertEqual(p['deployments'], [9001, 9002])
        self.assertEqual([k['id'] for k in p['kept_deployments']], [9007, 9006, 9005, 9004, 9003])
        self.assertTrue(all('environment=github-pages' in r for r in self.fake.reads if '/deployments' in r))

    def test_only_merged_packet_branches_without_an_open_pull_request_go(self):
        self.with_more()
        p = self.preview()
        self.assertEqual(p['branches'], [{'name': 'packet/w8', 'sha': IN_MAIN}])
        kept = {k['name']: k['reason'] for k in p['kept_branches']}
        self.assertEqual(kept, {'feature': 'not a packet branch', 'main': 'not a packet branch',
                                'status': 'not a packet branch', 'packet/w10': 'head is not in main',
                                'packet/open': 'an open pull request uses it'})
        compared = [r for r in self.fake.reads if '/compare/' in r]
        self.assertEqual(len(compared), 2)

    def test_apply_deletes_in_order_and_the_receipt_can_restore_branches(self):
        self.with_more()
        p = self.preview()
        self.assertEqual(cl.main(['apply', '--token', p['token'], '--receipt', 'r.json'], run=self.fake), 0)
        R = 'repos/%s/' % cl.REPO
        self.assertEqual(self.fake.deleted, [R + 'releases/1', R + 'git/refs/tags/adguard-v0.9-b20260801',
                                             R + 'git/refs/tags/adguard-v1.1-b20260901',
                                             R + 'deployments/9001', R + 'deployments/9002',
                                             R + 'git/refs/heads/packet/w8'])
        rec = json.loads(Path('r.json').read_text())
        self.assertEqual([d['id'] for d in rec['deployments']], [9001, 9002])
        self.assertEqual(rec['deployments'][0]['sha'], '%040x' % 0xd01)
        self.assertEqual(rec['branches'][0]['restore'], 'git push origin %s:refs/heads/packet/w8' % IN_MAIN)
        self.assertEqual(len(rec['kept_deployments']), 5)

    def test_a_failed_delete_stops_there_and_says_how_far_it_got(self):
        self.with_more()
        p = self.preview()
        self.fake.fail_on = 'deployments/9002'
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(cl.main(['apply', '--token', p['token'], '--receipt', 'r.json'], run=self.fake), 1)
        self.assertIn('STOP: deleted 4 of 6; failed at deployment 9002', out.getvalue())
        self.assertNotIn('repos/%s/git/refs/heads/packet/w8' % cl.REPO, self.fake.deleted)
        self.assertTrue(Path('r.json').is_file())

    def test_a_new_deployment_after_preview_changes_the_token(self):
        self.with_more()
        p = self.preview()
        self.fake.deploys.append(dep(8, 8))
        self.assertEqual(cl.main(['apply', '--token', p['token']], run=self.fake), 1)
        self.assertEqual(self.fake.deleted, [])

    def test_an_unreadable_deployment_list_deletes_nothing(self):
        self.with_more()
        self.fake.deploys[:] = [dep(1, 1), dep(2, 2, env='production')]
        with self.assertRaises(SystemExit):
            cl.main(['preview'], run=self.fake)
        self.fake.deploys[:] = [dep(1, 1), dep(1, 1)]
        with self.assertRaises(SystemExit):
            cl.main(['preview'], run=self.fake)
        self.assertEqual(self.fake.deleted, [])


if __name__ == '__main__':
    unittest.main()
