"""W16z: Repo setup applies labels and files seed issues once, never deletes, stops on API errors."""
import importlib.util, json, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('repo_setup', ROOT / 'src/etc/repo_setup.py')
rs = importlib.util.module_from_spec(spec); spec.loader.exec_module(rs)


class Fake:
    def __init__(self, labels=(), bodies='', fail=None):
        self.labels, self.bodies, self.fail, self.calls = list(labels), bodies, fail, []

    def __call__(self, argv, **kw):
        self.calls.append(argv)
        a = ' '.join(argv)
        class R: pass
        r = R(); r.returncode, r.stdout, r.stderr = 0, '', ''
        if self.fail and self.fail in a:
            r.returncode = 1; return r
        if '/labels?per_page' in a:
            r.stdout = '\n'.join(json.dumps(x) for x in self.labels)
        elif 'issues?state=all' in a:
            r.stdout = self.bodies
        return r


class RepoSetup(unittest.TestCase):
    def test_files_are_valid_and_small(self):
        labels, seeds = rs.load()
        self.assertLessEqual(len(labels), 8)
        self.assertEqual({s['id'] for s in seeds}, {'w17-owner-console', 'android-auto'})

    def test_first_run_creates_and_files(self):
        f = Fake(labels=[['bug', 'd73a4a', "Something isn't working"]])
        self.assertEqual(rs.main(run=f), 0)
        posts = [c for c in f.calls if 'POST' in c]
        self.assertEqual(len(posts), len(rs.load()[0]))
        self.assertEqual(sum(1 for c in f.calls if c[1:3] == ['issue', 'create']), 2)
        self.assertFalse(any('DELETE' in c for c in f.calls))
        created = [c for c in f.calls if c[1:3] == ['issue', 'create']]
        self.assertTrue(all(any(rs.marker(i) in x for x in c) for c, i in zip(created, ['w17-owner-console', 'android-auto'])))

    def test_rerun_changes_nothing(self):
        labels, seeds = rs.load()
        f = Fake(labels=[[l['name'], l['color'], l['description']] for l in labels],
                 bodies='\n'.join(s['body'] + rs.marker(s['id']) for s in seeds))
        self.assertEqual(rs.main(run=f), 0)
        self.assertFalse(any(('POST' in c or 'PATCH' in c or c[1:3] == ['issue', 'create']) for c in f.calls))

    def test_changed_label_is_patched_not_recreated(self):
        labels, seeds = rs.load()
        rows = [[l['name'], l['color'], l['description']] for l in labels]; rows[0][1] = '000000'
        f = Fake(labels=rows, bodies=''.join(rs.marker(s['id']) for s in seeds))
        self.assertEqual(rs.main(run=f), 0)
        self.assertEqual(sum(1 for c in f.calls if 'PATCH' in c), 1)

    def test_unreadable_issue_list_files_nothing(self):
        f = Fake(fail='issues?state=all')
        self.assertEqual(rs.main(run=f), 1)
        self.assertFalse(any(c[1:3] == ['issue', 'create'] for c in f.calls))

    def test_workflow_is_push_only_and_scoped(self):
        wf = (ROOT / '.github/workflows/repo-setup.yml').read_text()
        self.assertIn('permissions: {}', wf)
        self.assertIn('  push:\n    branches: [main]', wf)
        self.assertNotIn('workflow_dispatch', wf); self.assertNotIn('schedule', wf); self.assertNotIn('pull_request', wf)
        self.assertIn('issues: write', wf); self.assertIn('persist-credentials: false', wf)

    def test_issue_forms_exist(self):
        for f in ('owner-action.yml', 'verified-bug.yml', 'config.yml'):
            self.assertTrue((ROOT / '.github/ISSUE_TEMPLATE' / f).is_file(), f)


if __name__ == '__main__':
    unittest.main()
