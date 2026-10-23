"""11. Rule merge (W15d, owner 21 Oct 2026): a Selection watch rule pull request merges only
when every check, its Onboarding review and every app's test build are green. Each case
below changes one fact of an all-green pull request and must stop the merge."""
import copy
import importlib.util
import io
import contextlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('rule_merge', ROOT / 'src/etc/rule_merge.py')
rm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rm)
import json
POLICY = json.loads((ROOT / 'src/patches/ADOPT.json').read_text(encoding='utf-8'))
REPO = 'govinda-rajulu/patch-factory'
HEAD = 'a' * 40
TARGETS = {'reddit': {'candidates': [{'name': 'adobo'}, {'name': 'alastor'}]},
           'hotstar': {'candidates': [{'name': 'x'}]}}


def world():
    pr = {'number': 7, 'title': 'Adopt 2 names', 'user': {'login': 'github-actions[bot]'},
          'head': {'sha': HEAD, 'ref': 'adopt/2026-10-22-1', 'repo': {'full_name': REPO}},
          'body': 'Adopted by the rule.\n\n- reddit / alastor: `Hide ads`: ok\n- hotstar / x: `Disable analytics`: ok\n'}
    return {
        'pr': pr,
        'packets': [{'ref': 'refs/heads/packet/w15c', 'object': {'sha': 'c' * 40}}],
        'compare': {'c' * 40: 'ahead', 'e' * 40: 'diverged'},
        'files': [{'filename': 'src/patches/reddit-alastor/include-patches', 'status': 'modified', 'deletions': 0},
                  {'filename': 'docs/review/onboarding/hotstar.md', 'status': 'added', 'deletions': 0},
                  {'filename': 'README.md', 'status': 'modified', 'deletions': 2}],
        'full': {'mergeable': True},
        'checks': [{'name': rm.VALIDATE, 'status': 'completed', 'conclusion': 'success'},
                   {'name': 'patch', 'status': 'completed', 'conclusion': 'success'}],
        'commit': {'commit': {'committer': {'date': '2026-10-22T02:20:00Z'}}},
        'reviews': [{'display_title': 'Onboarding review #7', 'created_at': '2026-10-22T02:21:00Z',
                     'status': 'completed', 'conclusion': 'success', 'html_url': 'u'}],
        'builds': [{'display_title': 'Manual reddit / alastor / publish=false', 'status': 'completed', 'conclusion': 'success', 'html_url': 'b1'},
                   {'display_title': 'Manual hotstar / publish=false', 'status': 'completed', 'conclusion': 'success', 'html_url': 'b2'}],
    }


def api_for(w, calls):
    def api(path, method='GET', fields=None):
        calls.append((method, path, fields))
        if method in ('PUT', 'POST', 'PATCH', 'DELETE'):
            return {}
        if 'matching-refs/heads/packet/' in path:
            return w['packets']
        if path.endswith('/comments?per_page=100'):
            return w.get('comments', [])
        if '/compare/' in path:
            return {'status': w['compare'][path.split('/compare/')[1].split('...')[0]]}
        if path.startswith('repos/%s/pulls?state=open' % REPO):
            return [w['pr']]
        if path.endswith('/files?per_page=100'):
            return w['files']
        if path == 'repos/%s/pulls/7' % REPO:
            return w['full']
        if '/check-runs' in path:
            return {'check_runs': w['checks']}
        if path == 'repos/%s/commits/%s' % (REPO, HEAD):
            return w['commit']
        if 'onboard-review.yml/runs' in path:
            return {'workflow_runs': w['reviews']}
        if 'manual-patch.yml/runs' in path:
            assert 'head_sha=%s' % HEAD in path, path
            return {'workflow_runs': w['builds']}
        raise AssertionError(path)
    return api


def decide(w):
    return rm.decide(REPO, w['pr'], api_for(w, []), POLICY, TARGETS)


class RuleMerge(unittest.TestCase):
    def test_all_green_merges_with_the_head_pinned_then_starts_validate_and_status(self):
        calls, started = [], []
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rm.run(REPO, api=api_for(world(), calls), dispatch=lambda wf: started.append(wf) or 0, policy=POLICY, targets=TARGETS)
        puts = [c for c in calls if c[0] == 'PUT']
        self.assertEqual(len(puts), 1)
        self.assertEqual(puts[0][2]['sha'], HEAD)
        self.assertEqual(started, ['validate.yml', 'status.yml'])
        self.assertIn('RULE_MERGE #7 merge', out.getvalue())

    def test_a_packet_branch_holds_main_still(self):
        w = world(); w['packets'].append({'ref': 'refs/heads/packet/w15e', 'object': {'sha': 'e' * 40}})
        calls = []
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rm.run(REPO, api=api_for(w, calls), dispatch=lambda wf: 0, policy=POLICY, targets=TARGETS)
        self.assertFalse([c for c in calls if c[0] == 'PUT'])
        self.assertIn('packet/w15e', out.getvalue())

    def cases(self):
        def edit(f):
            w = world(); f(w); return w
        refuse = {
            'human author': lambda w: w['pr']['user'].update(login='someone'),
            'not an adopt branch': lambda w: w['pr']['head'].update(ref='feature/x'),
            'fork': lambda w: w['pr']['head'].update(repo={'full_name': 'evil/patch-factory'}),
            'workflow file': lambda w: w['files'].append({'filename': '.github/workflows/ci.yml', 'status': 'modified', 'deletions': 0}),
            'exclude list': lambda w: w['files'].append({'filename': 'src/patches/reddit-alastor/exclude-patches', 'status': 'modified', 'deletions': 0}),
            'policy file': lambda w: w['files'].append({'filename': 'src/patches/ADOPT.json', 'status': 'modified', 'deletions': 0}),
            'include line removed': lambda w: w['files'][0].update(deletions=1),
            'no names in body': lambda w: w['pr'].update(body='nothing'),
            'paid name on an account app': lambda w: w['pr'].update(body='- reddit / alastor: `Unlock Premium`: x\n'),
            'failed check': lambda w: w['checks'].append({'name': 'lint', 'status': 'completed', 'conclusion': 'failure'}),
            'review failed': lambda w: w['reviews'][0].update(conclusion='failure'),
            'test build failed': lambda w: w['builds'][1].update(conclusion='failure'),
        }
        wait = {
            'mergeability unknown': lambda w: w['full'].update(mergeable=None),
            'check running': lambda w: w['checks'].append({'name': 'x', 'status': 'in_progress', 'conclusion': None}),
            'no validate': lambda w: w['checks'].pop(0),
            'no review': lambda w: w.update(reviews=[]),
            'review before head': lambda w: w['reviews'][0].update(created_at='2026-10-22T02:00:00Z'),
            'review of another pr': lambda w: w['reviews'][0].update(display_title='Onboarding review #8'),
            'review running': lambda w: w['reviews'][0].update(status='in_progress'),
            'no test build of one app': lambda w: w['builds'].pop(1),
            'publishing build only': lambda w: w['builds'][1].update(display_title='Manual hotstar / publish=true'),
            'test build running': lambda w: w['builds'][0].update(status='in_progress'),
            'primary build only for a fallback pair': lambda w: w['builds'][0].update(display_title='Manual reddit / publish=false'),
        }
        return {k: edit(f) for k, f in refuse.items()}, {k: edit(f) for k, f in wait.items()}

    def test_every_red_or_foreign_fact_refuses(self):
        refuse, _ = self.cases()
        for label, w in refuse.items():
            with self.subTest(case=label):
                self.assertEqual(decide(w)[0], 'refuse')

    def test_every_unfinished_fact_waits(self):
        _, wait = self.cases()
        for label, w in wait.items():
            with self.subTest(case=label):
                self.assertEqual(decide(w)[0], 'wait')

    def test_207_unnamed_review_run_falls_back_to_the_bot_pass_comment(self):
        # 22 Oct 2026: run-name lost "#207" to a YAML comment, so no run carried the number (L069).
        w = world()
        w['reviews'][0]['display_title'] = 'Onboarding review'
        w['comments'] = [{'user': {'login': 'github-actions[bot]'}, 'created_at': '2026-10-22T02:23:00Z',
                          'updated_at': '2026-10-22T02:23:47Z', 'body': ' \n## Onboarding review: PASS\n\nseats'}]
        self.assertEqual(decide(w)[0], 'merge')
        blocked = copy.deepcopy(w)
        blocked['comments'][0]['body'] = '## Onboarding review: BLOCK\n'
        self.assertEqual(decide(blocked)[0], 'refuse')
        stranger = copy.deepcopy(w)
        stranger['comments'][0]['user']['login'] = 'someone'
        self.assertEqual(decide(stranger)[0], 'wait')
        old = copy.deepcopy(w)
        old['comments'][0].update(created_at='2026-10-22T02:00:00Z', updated_at='2026-10-22T02:00:00Z')
        self.assertEqual(decide(old)[0], 'wait')

    def test_patience_waits_for_running_builds_then_merges(self):
        w = world()
        w['builds'][0]['status'] = 'in_progress'
        calls, naps = [], []
        def nap(seconds):
            naps.append(seconds)
            w['builds'][0]['status'] = 'completed'
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rm.run(REPO, api=api_for(w, calls), dispatch=lambda wf: 0, policy=POLICY, targets=TARGETS, patience=600, sleep=nap)
        self.assertEqual(naps, [60])
        self.assertTrue(any(m == 'PUT' for m, _, _ in calls))
        self.assertIn('RULE_MERGE waiting 60 s', out.getvalue())

    def test_no_patience_means_one_pass(self):
        w = world()
        w['builds'][0]['status'] = 'in_progress'
        naps = []
        with contextlib.redirect_stdout(io.StringIO()):
            rm.run(REPO, api=api_for(w, []), dispatch=lambda wf: 0, policy=POLICY, targets=TARGETS, patience=0, sleep=naps.append)
        self.assertEqual(naps, [])

    def test_workflow_waits_and_the_review_wakes_it(self):
        text = (ROOT / '.github/workflows/rule-merge.yml').read_text(encoding='utf-8')
        self.assertIn('PF_RULE_MERGE_PATIENCE: "1200"', text)
        self.assertEqual(text.count('- cron: '), 2)
        review = (ROOT / '.github/workflows/onboard-review.yml').read_text(encoding='utf-8')
        self.assertIn('gh workflow run rule-merge.yml --repo "$PF_REPO" --ref main', review)
        self.assertIn('actions: write', review.split('  wake:')[1])

    def test_the_real_adopt_pull_request_files_are_all_allowed(self):
        # The 16 files of adopt PR #202 (read from the API on 21 Oct 2026); L064: measure on real data.
        real = ['docs/review/onboarding/%s.md' % a for a in ('facebook', 'hotstar', 'instagram', 'mxplayer', 'photos', 'reddit')]
        real += ['docs/review/providers/%s.names' % n for n in ('hushfacebook-com.facebook.katana', 'hushgram-com.instagram.android',
                                                                'morphe-com.google.android.youtube')]
        real += ['src/patches/%s/include-patches' % f for f in ('facebook-derevanced', 'gg-photos', 'hotstar-chiggi',
                                                                 'instagram-hushgram', 'instagram-piko', 'mxplayer-ftl', 'reddit-adobo')]
        self.assertEqual(len(real), 16)
        for name in real:
            with self.subTest(file=name):
                self.assertTrue(any(p.fullmatch(name) for p in rm.ALLOWED))

    def test_a_conflict_closes_and_deletes_so_the_watch_rebuilds_it(self):
        w = world(); w['full']['mergeable'] = False
        self.assertEqual(decide(w)[0], 'stale')
        calls = []
        with contextlib.redirect_stdout(io.StringIO()):
            rm.run(REPO, api=api_for(w, calls), dispatch=lambda wf: 0, policy=POLICY, targets=TARGETS)
        writes = [(m, p) for m, p, _ in calls if m != 'GET']
        self.assertEqual(writes, [('POST', 'repos/%s/issues/7/comments' % REPO), ('PATCH', 'repos/%s/pulls/7' % REPO),
                                  ('DELETE', 'repos/%s/git/refs/heads/adopt/2026-10-22-1' % REPO)])

    def test_a_refusal_is_told_once_and_a_merge_deletes_its_branch(self):
        w = world(); w['builds'][1]['conclusion'] = 'failure'
        calls = []
        with contextlib.redirect_stdout(io.StringIO()):
            rm.run(REPO, api=api_for(w, calls), dispatch=lambda wf: 0, policy=POLICY, targets=TARGETS)
        posts = [c for c in calls if c[0] == 'POST']
        self.assertEqual(len(posts), 1)
        self.assertIn(rm.MARK, posts[0][2]['body'])
        self.assertIn('Manual hotstar / publish=false', posts[0][2]['body'])
        w['comments'] = [{'body': posts[0][2]['body']}]
        calls = []
        with contextlib.redirect_stdout(io.StringIO()):
            rm.run(REPO, api=api_for(w, calls), dispatch=lambda wf: 0, policy=POLICY, targets=TARGETS)
        self.assertFalse([c for c in calls if c[0] != 'GET'])
        calls = []
        with contextlib.redirect_stdout(io.StringIO()):
            rm.run(REPO, api=api_for(world(), calls), dispatch=lambda wf: 0, policy=POLICY, targets=TARGETS)
        self.assertEqual([(m, p) for m, p, _ in calls if m in ('PUT', 'DELETE')],
                         [('PUT', 'repos/%s/pulls/7/merge' % REPO), ('DELETE', 'repos/%s/git/refs/heads/adopt/2026-10-22-1' % REPO)])

    def test_build_titles_match_the_manual_patch_run_name(self):
        wf = (ROOT / '.github/workflows/manual-patch.yml').read_text(encoding='utf-8')
        self.assertIn("run-name: Manual ${{ inputs.target }}${{ inputs.provider && format(' / {0}', inputs.provider) || '' }} / publish=${{ inputs.publish }}", wf)
        real = {t['id']: t for t in json.loads((ROOT / 'src/targets.json').read_text(encoding='utf-8'))}
        ig = real['instagram']['candidates'][0]['name']
        self.assertEqual(rm.build_title(real, 'instagram', ig), 'Manual instagram / publish=false')
        self.assertEqual(rm.build_title(real, 'instagram', 'hushgram'), 'Manual instagram / hushgram / publish=false')

    def test_offline_app_paid_name_may_merge(self):
        w = world(); w['pr']['body'] = '- esfile / ftl: `Unlock VIP Lifetime`: x\n'
        w['builds'] = [{'display_title': 'Manual esfile / publish=false', 'status': 'completed', 'conclusion': 'success'}]
        self.assertIn('esfile', POLICY['paid_ok_targets'])
        self.assertEqual(rm.decide(REPO, w['pr'], api_for(w, []), POLICY, {'esfile': {'candidates': [{'name': 'ftl'}]}})[0], 'merge')

    def test_workflow_runs_main_code_with_no_stored_credentials(self):
        text = (ROOT / '.github/workflows/rule-merge.yml').read_text(encoding='utf-8')
        self.assertIn('          ref: main\n          persist-credentials: false\n', text)
        self.assertNotIn('pull_request', text)
        self.assertIn('group: rule-merge', text)
        self.assertIn('run: python3 src/etc/rule_merge.py', text)


if __name__ == '__main__':
    unittest.main()
