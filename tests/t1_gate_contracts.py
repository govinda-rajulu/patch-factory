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
        self.assertLess(body.index("tested = t1(R['merge']) if PUBLISH_ALL else True"), body.index('previewed = preview()'))

    def test_nightly_runs_after_selection(self):
        keys = [k for k, _, _ in t1.FLOWS]
        self.assertLess(keys.index('selection'), keys.index('nightly'))
        self.assertLess(keys.index('rulemerge'), keys.index('nightly'))
        self.assertEqual(sorted(keys), sorted(['provider', 'community', 'tooling', 'selection', 'rulemerge', 'nightly']))


if __name__ == '__main__':
    unittest.main()
