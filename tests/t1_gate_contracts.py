"""pf-t1 (W15d): live main may sit on top of PF_MAIN only by the workflow bot's watch commits;
anything else stops the all-flows test. The Nightly watch runs after the Selection watch."""
import importlib.util
import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('PF_MAIN', 'a' * 40)
spec = importlib.util.spec_from_file_location('pf_t1', ROOT / 'docs/review/controllers/pf-t1.py')
t1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t1)
BOT = {'login': 'github-actions[bot]'}


WEB = {'login': 'web-flow'}


def commit(author=BOT, committer=BOT, parents=1):
    return {'author': author, 'committer': committer, 'parents': [{'sha': 'p'}] * parents}


class Gate(unittest.TestCase):
    def check(self, cmp):
        old = t1.must
        t1.must = lambda path, phase: cmp
        try:
            return t1.bot_only('a' * 40, 'b' * 40)
        finally:
            t1.must = old

    def test_bot_commits_only_pass(self):
        self.assertTrue(self.check({'status': 'ahead', 'total_commits': 2, 'commits': [commit(), commit()]}))

    def test_rule_merge_commit_passes(self):
        # W15f (L072): Rule merge #207 on 22 Oct: bot author, GitHub (web-flow) committer, two parents.
        self.assertTrue(self.check({'status': 'ahead', 'total_commits': 2, 'commits': [commit(), commit(BOT, WEB, 2)]}))

    def test_anything_else_stops(self):
        human = {'login': 'govinda-rajulu'}
        for label, cmp in {
            'owner commit': {'status': 'ahead', 'total_commits': 2, 'commits': [commit(), commit(human, human)]},
            'owner committed a bot-authored commit': {'status': 'ahead', 'total_commits': 1, 'commits': [commit(BOT, human)]},
            'diverged': {'status': 'diverged', 'total_commits': 1, 'commits': [commit()]},
            'behind': {'status': 'behind', 'total_commits': 0, 'commits': []},
            'list cut short': {'status': 'ahead', 'total_commits': 300, 'commits': [commit()]},
            'no author': {'status': 'ahead', 'total_commits': 1, 'commits': [{'author': None, 'committer': BOT}]},
            'owner merge by GitHub': {'status': 'ahead', 'total_commits': 1, 'commits': [commit(human, WEB, 2)]},
            'GitHub-committed bot commit that is not a merge': {'status': 'ahead', 'total_commits': 1, 'commits': [commit(BOT, WEB, 1)]},
        }.items():
            with self.subTest(case=label):
                self.assertFalse(self.check(cmp))

    def test_publish_switch_reaches_the_batch(self):
        # W15f (owner 22 Oct): every release was gone; the controller's T1 publishes a fresh set.
        src = (ROOT / 'docs/review/controllers/pf-t1.py').read_text()
        self.assertIn("PUBLISH = os.environ.get('PF_T1_PUBLISH') == '1'", src)
        self.assertIn("('publish', flag)", src)
        self.assertFalse(t1.PUBLISH)
        tmpl = (ROOT / 'docs/review/controllers/packet.tmpl.py').read_text()
        self.assertIn("PF_T1_PUBLISH='1' if PUBLISH_ALL else ''", tmpl)
        body = tmpl[tmpl.index('def main():'):]
        self.assertLess(body.index("tested = t1(R['merge']) if early else True"), body.index('previewed = preview()'))
        self.assertIn('early = PUBLISH_ALL or bool(PUBLISH_APPS)', body)

    def test_w16c_publish_only_named_apps_that_built_on_their_primary(self):
        saved = (t1.dispatch_and_wait, t1.read_apps, t1.save, t1.R, t1.PUBLISH_APPS, t1.say)
        calls, said = [], []
        t1.R = {'apps': {'reddit': {'batch': {'result': 'success'}},
                         'instagram': {'batch': {'result': 'success', 'fallback': 'hushgram'}},
                         'photos': {'batch': {'result': 'success'}}}, 'phases': [], 'flows': {}}
        t1.dispatch_and_wait = lambda phase, file, main, fields, limit, want=None: calls.append((phase, file, fields, want)) or {
            'id': 7, 'conclusion': 'success', 'display_title': 'Batch reddit / publish=true'}
        t1.read_apps = lambda phase, r: {'reddit': {'result': 'success'}}
        t1.save = lambda: None
        t1.say = lambda phase, status, text: said.append((phase, status, text))
        try:
            t1.PUBLISH_APPS = ['reddit', 'instagram']
            t1.publish('m' * 40, ['reddit', 'instagram', 'photos'])
            self.assertEqual(len(calls), 1)
            phase, file, fields, want = calls[0]
            self.assertEqual((phase, file, fields), ('publish', 'batch-patch.yml', [('targets', 'reddit'), ('publish', 'true')]))
            self.assertTrue(want({'display_title': 'Batch reddit / publish=true'}))
            self.assertFalse(want({'display_title': 'Batch reddit / publish=false'}))
            self.assertIn(('publish', 'FINDING', 'not published, failed or on a fallback in the test batch: instagram'), said)
            self.assertEqual(said[-1][:2], ('publish', 'OK'))
            calls.clear()
            t1.PUBLISH_APPS = []
            t1.publish('m' * 40, ['reddit'])
            self.assertEqual(calls, [])
            t1.PUBLISH_APPS = ['nope']
            with self.assertRaises(SystemExit):
                t1.publish('m' * 40, ['reddit'])
            self.assertEqual(calls, [])
        finally:
            t1.dispatch_and_wait, t1.read_apps, t1.save, t1.R, t1.PUBLISH_APPS, t1.say = saved

    def test_nightly_runs_after_selection(self):
        keys = [k for k, _, _ in t1.FLOWS]
        self.assertLess(keys.index('selection'), keys.index('nightly'))
        self.assertLess(keys.index('rulemerge'), keys.index('nightly'))
        self.assertEqual(sorted(keys), sorted(['provider', 'community', 'tooling', 'selection', 'rulemerge', 'nightly', 'needsyou']))
        # W16c: Needs you reads every collector's newest artifact, so it runs last.
        self.assertEqual(keys[-1], 'needsyou')


    def test_w15i_fallback_builds_are_a_finding(self):
        # L077: 23 Oct "17 of 17 worked" while Facebook and Instagram built on their fallbacks.
        saved = (t1.dispatch_and_wait, t1.read_apps, t1.save, t1.R)
        said = []
        t1.R = {'apps': {}, 'phases': [], 'flows': {}}
        t1.dispatch_and_wait = lambda *a, **k: {'id': 9}
        t1.read_apps = lambda phase, r: {
            'youtube': {'run': 9, 'result': 'success', 'coverage': 'COVERAGE youtube ok'},
            'facebook': {'run': 9, 'result': 'success', 'fallback': '##[warning]PROVIDER_FALLBACK facebook: Built with fallback provider derevanced'}}
        t1.save = lambda: None
        old_say = t1.say
        t1.say = lambda phase, status, detail: said.append((phase, status, detail))
        try:
            t1.batch('m' * 40, ['youtube', 'facebook'])
        finally:
            t1.dispatch_and_wait, t1.read_apps, t1.save, t1.R = saved
            t1.say = old_say
        self.assertEqual(said[0][1], 'FINDING')
        self.assertIn('2 of 2 apps worked', said[0][2])
        self.assertIn('on a fallback provider: facebook', said[0][2])


if __name__ == '__main__':
    unittest.main()
