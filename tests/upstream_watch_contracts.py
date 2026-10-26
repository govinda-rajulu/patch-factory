"""Upstream watch contracts (packet W15h, 22 Oct 2026; L074): every outside tool and source is
read daily into one standing issue, edited in place, with a comment only when something changed."""
import datetime
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'etc'))
import tooling_watch as tw  # noqa: E402

TODAY = datetime.date(2026, 10, 22)


def rel(tag, when, pre=False, draft=False):
    return {'tag_name': tag, 'published_at': when, 'prerelease': pre, 'draft': draft}


class Reading(unittest.TestCase):
    def test_every_entry_loads_and_every_pin_is_true(self):
        rows = tw.load_upstreams(ROOT / 'src/etc/upstreams.json')
        self.assertEqual(len(rows), 12)
        required_ids = {'obtainium', 'morphe-desktop', 'flaresolverr', 'apkeditor'}
        self.assertTrue(required_ids <= {r['id'] for r in rows})
        self.assertEqual(len({r['id'] for r in rows}), len(rows))
        for r in rows:
            pin = r.get('pin')
            if pin:
                self.assertIn(pin['text'], (ROOT / pin['file']).read_text(), r['id'])
                self.assertIn(pin['tag'].lstrip('vV'), pin['text'], r['id'])

    def test_obtainium_and_the_patcher_are_watched(self):
        repos = {r['repo'] for r in tw.load_upstreams(ROOT / 'src/etc/upstreams.json')}
        for repo in ('ImranR98/Obtainium', 'MorpheApp/morphe-desktop', 'FlareSolverr/FlareSolverr', 'REAndroid/APKEditor'):
            self.assertIn(repo, repos)

    def test_release_row_splits_stable_and_prerelease(self):
        u = {'id': 'x', 'repo': 'o/r', 'kind': 'release', 'role': 'r', 'pin': {'tag': 'v1.0'}}
        data = [rel('v1.1-dev', '2026-10-20T00:00:00Z', pre=True), rel('v1.0', '2026-10-01T00:00:00Z'), rel('v2', '2026-10-21T00:00:00Z', draft=True)]
        row = tw.read_upstream(u, {}, fetch=lambda p: data)
        self.assertEqual((row['latest'], row['newest'], row['date']), ('v1.0', 'v1.1-dev', '2026-10-01'))
        self.assertEqual(tw.upstream_status(row, TODAY), 'OK')

    def test_commit_row_and_quiet_and_unreadable(self):
        u = {'id': 'c', 'repo': 'o/r', 'kind': 'commits', 'role': 'r'}
        row = tw.read_upstream(u, {}, fetch=lambda p: [{'sha': 'abcdef1234', 'commit': {'committer': {'date': '2024-01-01T00:00:00Z'}}}])
        self.assertEqual(row['latest'], 'abcdef1')
        self.assertEqual(tw.upstream_status(row, TODAY), 'QUIET')
        def boom(p):
            raise OSError('down')
        bad = tw.read_upstream(u, {}, fetch=boom)
        self.assertEqual(tw.upstream_status(bad, TODAY), 'UNREADABLE')

    def test_behind_when_the_pin_is_not_the_newest_stable(self):
        u = {'id': 'x', 'repo': 'o/r', 'kind': 'release', 'role': 'r', 'pin': {'tag': 'v1.0'}}
        row = tw.read_upstream(u, {}, fetch=lambda p: [rel('v1.1', '2026-10-20T00:00:00Z')])
        self.assertEqual(tw.upstream_status(row, TODAY), 'BEHIND')


class Body(unittest.TestCase):
    def rows(self, latest='v1.0'):
        return [{'id': 'a', 'repo': 'o/a', 'role': 'r', 'pinned': '', 'latest': latest, 'date': '2026-10-20', 'newest': ''}]

    def test_body_is_stable_and_carries_state(self):
        one, two = tw.upstream_body(self.rows(), TODAY), tw.upstream_body(self.rows(), TODAY)
        self.assertEqual(one, two)
        self.assertEqual(tw.previous_state(one), {'a': 'v1.0'})
        self.assertIn('**Needs you:** nothing', one)

    def test_change_is_marked_new(self):
        body = tw.upstream_body(self.rows('v1.1'), TODAY, {'a': 'v1.0'})
        self.assertIn('NEW v1.0 -> v1.1', body)
        self.assertIn('## To review', body)


class Delivery(unittest.TestCase):
    def fake(self, existing):
        calls = []
        def run(args, **kw):
            calls.append(args)
            if args[1:3] == ['issue', 'list']:
                return SimpleNamespace(returncode=0, stdout=json.dumps(existing), stderr='')
            return SimpleNamespace(returncode=0, stdout='https://github.com/o/r/issues/9\n', stderr='')
        return run, calls

    def go(self, existing, body):
        run, calls = self.fake(existing)
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            try:
                result = tw.deliver('o/r', lambda old: body, '1', run)
            finally:
                os.chdir(cwd)
        return result, [c[1:3] for c in calls]

    def test_first_run_creates_without_comment(self):
        self.assertEqual(self.go([], 'B\n'), ('CREATED', [['issue', 'list'], ['issue', 'create']]))

    def test_unchanged_body_writes_nothing(self):
        self.assertEqual(self.go([{'number': 9, 'title': 'Tooling watch', 'body': 'B\n'}], 'B\n'), ('UNCHANGED', [['issue', 'list']]))

    def test_change_edits_and_comments_once(self):
        # W16j: a comment only when the headline turns to something to review.
        old = {'number': 9, 'title': 'Tooling watch', 'body': '# Tooling watch: OK\nA\n'}
        result, calls = self.go([old], '# Tooling watch: 2 to review\nB\n')
        self.assertEqual(result, 'EDITED')
        self.assertEqual(calls, [['issue', 'list'], ['issue', 'edit'], ['issue', 'comment']])

    def test_reworded_body_or_back_to_ok_edits_quietly(self):
        old = {'number': 9, 'title': 'Tooling watch', 'body': '# Tooling watch: 2 to review\nA\n'}
        self.assertEqual(self.go([old], '# Tooling watch: 2 to review\nB\n'), ('EDITED', [['issue', 'list'], ['issue', 'edit']]))
        self.assertEqual(self.go([old], '# Tooling watch: OK\nB\n'), ('EDITED', [['issue', 'list'], ['issue', 'edit']]))

    def test_other_titles_are_not_the_standing_issue(self):
        result, calls = self.go([{'number': 3, 'title': 'Tooling: update ready', 'body': 'B\n'}], 'B\n')
        self.assertEqual(result, 'CREATED')

    def test_workflow_runs_it_daily_with_issue_rights(self):
        text = (ROOT / '.github/workflows/tooling-watch.yml').read_text()
        self.assertIn('run: python3 src/etc/tooling_watch.py --upstreams', text)
        self.assertIn('issues: write', text)
        self.assertNotIn(' # ${{', text)


if __name__ == '__main__':
    unittest.main()
