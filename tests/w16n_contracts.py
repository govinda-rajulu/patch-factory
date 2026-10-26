"""W16n review fixes: token pushes fail closed, newest onboarding review decides."""
import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/etc'))
sys.path.insert(0, str(ROOT / 'tests'))


class PushRemote(unittest.TestCase):
    def modules(self):
        return [importlib.import_module('selection_watch'), importlib.import_module('community_watch')]

    def test_outside_actions_origin_even_with_a_token(self):
        with mock.patch.dict(os.environ, {'GH_TOKEN': 't0k', 'GITHUB_REPOSITORY': 'o/r'}, clear=False):
            os.environ.pop('GITHUB_ACTIONS', None)
            for m in self.modules():
                self.assertEqual(m.push_remote(), 'origin')

    def test_in_actions_an_explicit_token_url(self):
        with mock.patch.dict(os.environ, {'GITHUB_ACTIONS': 'true', 'GH_TOKEN': 't0k', 'GITHUB_REPOSITORY': 'o/r'}):
            for m in self.modules():
                self.assertEqual(m.push_remote(), 'https://x-access-token:t0k@github.com/o/r.git')

    def test_in_actions_without_a_token_it_refuses(self):
        env = {k: v for k, v in os.environ.items() if k not in ('GH_TOKEN', 'GITHUB_TOKEN')}
        env.update(GITHUB_ACTIONS='true', GITHUB_REPOSITORY='o/r')
        with mock.patch.dict(os.environ, env, clear=True):
            for m in self.modules():
                with self.assertRaisesRegex(ValueError, 'PUSH_TOKEN_MISSING'):
                    m.push_remote()

    def test_scrub_hides_the_token(self):
        with mock.patch.dict(os.environ, {'GH_TOKEN': 'sekret123'}):
            for m in self.modules():
                out = m.scrub(b'fatal: unable to access https://x-access-token:sekret123@github.com/o/r.git/')
                self.assertNotIn('sekret123', out)
                self.assertIn('x-access-token:***@', out)


class NewestReviewDecides(unittest.TestCase):
    def test_an_older_review_on_another_head_does_not_veto(self):
        import rule_merge_contracts as rc
        w = rc.world()
        w['reviews'] = [dict(w['reviews'][0], created_at='2026-10-22T02:21:00Z', head_sha='0' * 40),
                        dict(w['reviews'][0], created_at='2026-10-22T02:30:00Z', head_sha=rc.HEAD)]
        verdict, why = rc.decide(w)
        self.assertNotEqual(why, 'Onboarding review is for a different PR head')
        self.assertEqual(verdict, 'merge', why)

    def test_the_newest_review_on_another_head_refuses(self):
        import rule_merge_contracts as rc
        w = rc.world()
        w['reviews'] = [dict(w['reviews'][0], created_at='2026-10-22T02:21:00Z', head_sha=rc.HEAD),
                        dict(w['reviews'][0], created_at='2026-10-22T02:30:00Z', head_sha='0' * 40)]
        self.assertEqual(rc.decide(w), ('refuse', 'Onboarding review is for a different PR head'))



class ReviewRound2(unittest.TestCase):
    """W16n review round 2 fixes (26 Oct 2026)."""

    def test_watch_state_never_echoes_a_token(self):
        import io
        import subprocess
        import tempfile
        from contextlib import redirect_stdout, redirect_stderr
        ws = importlib.import_module('watch_state')
        bad = subprocess.CompletedProcess([], 1, b'', b'HTTP 500 token=SECRET123 https://x-access-token:abc@github.com')
        with mock.patch.dict(os.environ, {'GH_TOKEN': 'SECRET123', 'REPO': 'o/r'}), \
                mock.patch.object(ws, '_run', return_value=bad), tempfile.TemporaryDirectory() as tmp:
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = ws.get('state.json', Path(tmp) / 'state.json')
            text = out.getvalue() + err.getvalue()
        self.assertNotEqual(code, 0)
        self.assertNotIn('SECRET123', text)
        self.assertNotIn(':abc@', text)

    def test_needs_you_malformed_ledger_row_stops(self):
        import json
        import tempfile
        ny = importlib.import_module('needs_you')
        for row in ({'id': 'N-AAAAAA', 'verb': 'take', 'except': 'not-a-list'}, 'text', {'verb': 'take'}):
            with tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp) / 'l.json'
                p.write_text(json.dumps([row]))
                with self.assertRaisesRegex(ValueError, 'malformed row'):
                    ny.load_ledger(p, fail_closed=True)
                self.assertEqual(ny.load_ledger(p), [row])
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'l.json'
            p.write_text(json.dumps([{'id': 'N-AAAAAA', 'verb': 'take', 'except': ['X']}, {'id': 'N-BBBBBB', 'verb': 'drop'}]))
            self.assertEqual(len(ny.load_ledger(p, fail_closed=True)), 2)

    def test_onboard_non_string_id_is_the_controlled_error(self):
        import json
        import tempfile
        oc = importlib.import_module('onboard_check')
        for value in (None, 7, {'a': 1}):
            with tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / 'src').mkdir()
                (Path(tmp) / 'src/targets.json').write_text(json.dumps([{'id': value}]))
                with self.assertRaisesRegex(ValueError, 'invalid target id'):
                    oc.load_targets(tmp)

    def test_scout_gitlab_wiring_and_scalar_fields(self):
        import json
        import tempfile
        sc = importlib.import_module('mcp_scout_check')
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 't.json'
            p.write_text(json.dumps([
                {'id': 'mxplayer', 'extra_bundles': [{'host': 'gitlab', 'owner': 'Paresh', 'repo': 'p'}],
                 'candidates': [{'owner': 'A', 'repo': 'B'}, {'owner': 1, 'repo': 'x'}]},
                {'id': 'youtube', 'candidates': 1, 'extra_bundles': 'x'}]))
            self.assertEqual(sc.target_wiring(p), {'mxplayer': {'a/b'}, 'youtube': set()})

    def test_merge_display_name_and_order_are_order_independent(self):
        import copy
        cm = importlib.import_module('community_model')
        def bundle(repo, updated, name):
            return dict(source='github', repo=repo, name=name, updatedAt=updated, targetApps=['com.example.app'],
                        patches=[dict(name='One', compatiblePackagesKey=0)], patchCount=1)
        data = dict(bundles=[bundle('Owner/Patches', 100, 'A'), bundle('owner/patches', 200, 'B'),
                             bundle('z/r', 1, 'Z'), bundle('Z/R', 2, 'Z2')],
                    compatibilities=[[dict(packageName='com.example.app')]])
        flipped = copy.deepcopy(data)
        flipped['bundles'].reverse()
        a, b = cm.inventory(data), cm.inventory(flipped)
        self.assertEqual(cm.digest(a), cm.digest(b))
        self.assertEqual([m['provider'] for m in a['coverage']['merged_providers']], ['github:owner/patches', 'github:z/r'])
        other = bundle('other/repo', 150, 'O')
        data['bundles'].append(other)
        targets = [dict(id='app', enabled=True, package='com.example.app', candidates=[dict(owner='x', repo='y')])]
        rows = cm.rank_providers(data, targets)[0]['providers']
        self.assertEqual(rows[0]['repo'].lower(), 'owner/patches')
        self.assertEqual(rows[0]['rank'][-1], 200)


class WatchDispatch(unittest.TestCase):
    """W16n: after the merge the controller dispatches the watches once on main and does not wait."""

    def test_watch_dispatch_once_per_merge_and_before_publish(self):
        t = (ROOT / 'docs/review/controllers/packet.tmpl.py').read_text()
        self.assertIn('WATCH_DISPATCH = ()', t)
        body = t[t.index('def watch_dispatch('):t.index('def finish(')]
        self.assertIn("[GH, 'workflow', 'run', wf, '--repo', REPO, '--ref', 'main']", body)
        self.assertIn("pf-%s-watch-%s.done", body)
        self.assertLess(body.index('done.is_file()'), body.index("'workflow', 'run'"))
        self.assertNotIn('time.sleep', body)
        main = t[t.index('def main():'):]
        self.assertLess(main.index('cleanup(R['), main.index('watch_dispatch(R['))
        self.assertLess(main.index('watch_dispatch(R['), main.index('publish_dispatch(R['))
        self.assertIn('and watched and dispatched)', main)


if __name__ == '__main__':
    unittest.main()
