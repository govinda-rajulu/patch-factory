"""W16k (owner, 25 Oct 2026): a packet never dispatches a third smoke of one app (the Manual Patch
queue cancelled Instagram oxbow), and a publish after merge is dispatched, not waited for (the
W16j controller died in an idle Cloud Shell while it waited)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = (ROOT / 'docs/review/controllers/packet.tmpl.py').read_text()


class Controller(unittest.TestCase):
    def test_third_smoke_of_an_app_stops_the_gate_first(self):
        self.assertIn('SMOKES_PER_APP = 2', T)
        gate = T[T.index('def gate():'):T.index("code, out, err = run([GH, 'auth', 'status'], timeout=60)")]
        self.assertIn("per[t.split('/', 1)[0]]", gate)
        self.assertIn("stop('gate', 'more than %d smokes", gate)

    def test_publish_is_dispatched_last_and_not_awaited(self):
        body = T[T.index('def publish_dispatch('):T.index('def finish(')]
        self.assertIn("'batch-patch.yml', '--repo', REPO, '--ref', 'main'", body)
        self.assertIn("'-f', 'publish=true'", body)
        self.assertNotIn('dispatch_and_wait', body)
        self.assertLessEqual(body.count('time.sleep(10)'), 1)
        self.assertIn("pf-%s-publish.done", body)
        self.assertLess(body.index("str(r.get('display_title', '')).endswith('/ publish=true')"), body.index("'workflow', 'run', 'batch-patch.yml'"))
        main = T[T.index('def main():'):]
        self.assertLess(main.index('cleanup(R['), main.index('publish_dispatch(R['))
        self.assertIn('and dispatched)', main)


class Branches(unittest.TestCase):
    def test_merged_branches_go_and_main_never(self):
        body = T[T.index('def delete_branches():'):T.index('def close_issues():')]
        self.assertIn("'DELETE'", body)
        self.assertIn("if name in ('main', 'status', 'gh-pages')", body)
        main = T[T.index('def main():'):]
        self.assertLess(main.index('merge(pr)'), main.index('delete_branches()'))


if __name__ == '__main__':
    unittest.main()
