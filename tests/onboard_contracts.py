"""Onboarding gate contracts (packet W1, 8 Oct 2026).

New apps, providers and patch names need a record and an agent review. These tests pin
the deterministic checker, the reviewer's counting rules and the workflow's trust split.
"""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'etc'))
sys.path.insert(0, str(ROOT / 'src' / 'council'))
import onboard_check  # noqa: E402
import onboard_review  # noqa: E402
import council  # noqa: E402


def tree(root, targets, selections=None, records=None, banned='', confirm=''):
    root = Path(root)
    (root / 'src' / 'patches').mkdir(parents=True, exist_ok=True)
    (root / 'src' / 'targets.json').write_text(json.dumps(targets))
    (root / 'src' / 'patches' / 'BANNED').write_text(banned)
    (root / 'src' / 'patches' / 'CONFIRM').write_text(confirm)
    for pd, (inc, exc) in (selections or {}).items():
        d = root / 'src' / 'patches' / pd
        d.mkdir(parents=True, exist_ok=True)
        (d / 'include-patches').write_text(''.join(n + '\n' for n in inc))
        (d / 'exclude-patches').write_text(''.join(n + '\n' for n in exc))
    for tid, text in (records or {}).items():
        d = root / 'docs' / 'review' / 'onboarding'
        d.mkdir(parents=True, exist_ok=True)
        (d / (tid + '.md')).write_text(text)
    return root


def target(tid, owner='prov', repo='patches', pd=None, enabled=True, extra=None):
    t = {'id': tid, 'enabled': enabled, 'package': 'com.example.' + tid,
         'candidates': [{'name': owner, 'owner': owner, 'repo': repo, 'patch_dir': pd or tid + '-' + owner}]}
    if extra:
        t['extra_bundles'] = extra
    return t


class Checker(unittest.TestCase):
    def run_pair(self, base, head):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            tree(a, **base)
            tree(b, **head)
            return onboard_check.check(a, b)

    def test_unchanged_repository_is_not_onboarding(self):
        state = {'targets': [target('app')], 'selections': {'app-prov': (['Hide ads'], [])}}
        m = self.run_pair(state, state)
        self.assertFalse(m['onboarding'])
        self.assertEqual(m['problems'], [])

    def test_new_target_without_record_fails(self):
        m = self.run_pair({'targets': [target('app')]},
                          {'targets': [target('app'), target('new')], 'selections': {'new-prov': (['Hide ads'], [])}})
        self.assertTrue(m['onboarding'])
        self.assertTrue(any('record docs/review/onboarding/new.md is missing' in p for p in m['problems']))

    def test_record_must_name_provider_and_each_added_patch(self):
        head = {'targets': [target('new')], 'selections': {'new-prov': (['Hide ads', 'Skip intro'], [])},
                'records': {'new': 'Provider: prov/patches\n- Hide ads: client-side\n'}}
        m = self.run_pair({'targets': []}, head)
        self.assertEqual(len(m['problems']), 1)
        self.assertIn("'Skip intro'", m['problems'][0])
        head['records'] = {'new': 'Provider: prov/patches\n- Hide ads: x\n- Skip intro: y\n'}
        self.assertEqual(self.run_pair({'targets': []}, head)['problems'], [])

    def test_todo_in_record_fails(self):
        head = {'targets': [target('new')], 'selections': {'new-prov': ([], [])},
                'records': {'new': 'Provider: prov/patches\nTODO list-patches\n'}}
        self.assertTrue(any('TODO' in p for p in self.run_pair({'targets': []}, head)['problems']))

    def test_added_patch_on_existing_target_needs_a_record(self):
        base = {'targets': [target('app')], 'selections': {'app-prov': (['Hide ads'], [])}}
        head = {'targets': [target('app')], 'selections': {'app-prov': (['Hide ads', 'Hide shorts'], [])}}
        m = self.run_pair(base, head)
        self.assertEqual(m['patch_changes'][0]['added_include'], ['Hide shorts'])
        self.assertTrue(m['problems'])
        head['records'] = {'app': '- Hide shorts: owner asked, client-side layout\n'}
        self.assertEqual(self.run_pair(base, head)['problems'], [])

    def test_removal_only_is_listed_not_blocked(self):
        base = {'targets': [target('app')], 'selections': {'app-prov': (['Hide ads', 'Hide shorts'], [])}}
        head = {'targets': [target('app')], 'selections': {'app-prov': (['Hide ads'], ['Hide shorts'])}}
        m = self.run_pair(base, head)
        self.assertFalse(m['onboarding'])
        self.assertEqual(m['problems'], [])
        self.assertEqual(m['patch_changes'][0]['removed_include'], ['Hide shorts'])

    def test_comment_lines_and_options_are_not_names(self):
        base = {'targets': [target('app')], 'selections': {'app-prov': ([], [])}}
        head = {'targets': [target('app')], 'selections': {'app-prov': (['# note', 'Theme|dark'], [])},
                'records': {'app': '- Theme: owner choice\n'}}
        m = self.run_pair(base, head)
        self.assertEqual(m['patch_changes'][0]['added_include'], ['Theme'])
        self.assertEqual(m['problems'], [])

    def test_confirm_needs_owner_line_and_banned_always_fails(self):
        base = {'targets': [target('app')], 'selections': {'app-prov': ([], [])}, 'confirm': 'spoof\n', 'banned': 'signature\n'}
        head = dict(base, selections={'app-prov': (['Spoof client', 'Spoof signature'], [])},
                    records={'app': '- Spoof client: x\n- Spoof signature: y\n'})
        problems = self.run_pair(base, head)['problems']
        self.assertTrue(any('BANNED' in p and 'Spoof signature' in p for p in problems))
        self.assertTrue(any('Owner approved: Spoof client' in p for p in problems))
        head['records'] = {'app': '- Spoof client: x\nOwner approved: Spoof client\n'}
        head['selections'] = {'app-prov': (['Spoof client'], [])}
        self.assertEqual(self.run_pair(base, head)['problems'], [])

    def test_enabling_and_new_extra_provider_count(self):
        base = {'targets': [target('app', enabled=False)], 'selections': {'app-prov': ([], [])}}
        extra = [{'name': 'gl', 'host': 'gitlab', 'project_id': 42, 'patch_dir': 'app-gl'}]
        head = {'targets': [target('app', extra=extra)], 'selections': {'app-prov': ([], []), 'app-gl': ([], [])},
                'records': {'app': 'Provider: gitlab:42\n'}}
        m = self.run_pair(base, head)
        self.assertEqual(m['enabled_targets'], ['app'])
        self.assertEqual([p['source'] for p in m['new_providers']], ['gitlab:42'])
        self.assertEqual(m['problems'], [])


def answer(canary, verdict='approve', findings=()):
    return {'canary': canary, 'verdict': verdict, 'summary': 'ok',
            'findings': [dict(severity='high', item='x', issue='y', quote=q) for q in findings]}


class Reviewer(unittest.TestCase):
    def test_quotes_must_come_from_the_manifest_and_canary_must_match(self):
        a = onboard_review.check_answer(answer('c1', 'block', ['Unlock premium', 'invented']), 'c1', '"Unlock premium"')
        self.assertEqual([f['quote'] for f in a['findings']], ['Unlock premium'])
        self.assertEqual(a['dropped'], 1)
        self.assertTrue(a['counted'])
        a = onboard_review.check_answer(answer('c1', 'block', ['invented']), 'c1', 'manifest')
        self.assertFalse(a['counted'])
        with self.assertRaises(ValueError):
            onboard_review.check_answer(answer('other'), 'c1', 'manifest')

    def test_quorum_and_majority_block(self):
        def row(verdict, counted=True):
            return {'answer': {'verdict': verdict, 'counted': counted}}
        self.assertFalse(onboard_review.decide([row('approve')], True)[0])
        self.assertTrue(onboard_review.decide([row('approve'), row('changes')], True)[0])
        self.assertFalse(onboard_review.decide([row('approve'), row('block')], True)[0])
        self.assertTrue(onboard_review.decide([row('approve'), row('approve'), row('block')], True)[0])
        self.assertFalse(onboard_review.decide([row('approve'), row('approve')], False)[0])
        self.assertFalse(onboard_review.decide([row('approve'), {'answer': None}, row('block', False)], True)[0])

    def test_seat_answer_through_council_transport(self):
        seat = {'id': 's', 'provider': next(iter(council.PROVIDERS)), 'models': ['m1'], 'max_input_chars': 100000}
        env = {council.PROVIDERS[seat['provider']]['key']: 'k' * 12}
        saved = council.complete, council.candidates
        try:
            council.candidates = lambda s, e: ['m1']
            council.complete = lambda *a, **k: json.dumps(answer('c9'))
            row = onboard_review.ask_seat(seat, 'sys', 'user', env, 'c9', 'manifest')
            self.assertEqual(row['status'], 'OK')
            council.complete = lambda *a, **k: 'no json here'
            self.assertTrue(onboard_review.ask_seat(seat, 'sys', 'user', env, 'c9', 'm')['status'].startswith('INVALID'))
            self.assertEqual(onboard_review.ask_seat(seat, 'sys', 'user', {}, 'c9', 'm')['status'], 'SKIPPED_NO_KEY')
        finally:
            council.complete, council.candidates = saved

    def test_prompt_has_the_council_sentinel(self):
        self.assertIn('canary', onboard_review.instructions())


class Workflow(unittest.TestCase):
    TEXT = (ROOT / '.github' / 'workflows' / 'onboard-review.yml').read_text(encoding='utf-8')

    def test_actions_are_pinned_by_sha(self):
        refs = re.findall(r'uses:\s*([^\s#]+)', self.TEXT)
        self.assertTrue(refs)
        for ref in refs:
            self.assertRegex(ref, r'@[0-9a-f]{40}$')

    def test_code_runs_from_base_and_keys_never_meet_the_head(self):
        record, agents = self.TEXT.split('\n  agents:\n')
        self.assertIn('python3 base/src/etc/onboard_check.py', record)
        self.assertNotIn('secrets.', record)
        self.assertNotIn('head.sha', agents)
        self.assertIn('ref: ${{ needs.record.outputs.base }}', agents)
        self.assertNotIn('pull_request_target', self.TEXT)

    def test_agents_job_refuses_forks(self):
        self.assertIn("needs.record.outputs.head_repo != github.repository", self.TEXT)


if __name__ == '__main__':
    unittest.main()
