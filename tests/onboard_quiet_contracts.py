"""W16k (owner, 25 Oct 2026): agents stop saying block/ignore for things the owner decided,
rule 4 means one build, repeated findings show once, seat plumbing folds away, and an
unchanged review is not re-posted."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/etc'))
sys.path.insert(0, str(ROOT / 'src/council'))
import onboard_check as oc  # noqa: E402
import onboard_review as orv  # noqa: E402


def tree(paid, takes, targets, files):
    root = Path(tempfile.mkdtemp())
    (root / 'src/patches').mkdir(parents=True)
    (root / 'src/patches/ADOPT.json').write_text(json.dumps({'paid_ok_targets': paid}))
    (root / 'src/patches/DECISIONS.json').write_text(json.dumps({'names': [
        {'target': t, 'name': n, 'call': 'take'} for t, n in takes]}))
    (root / 'src/targets.json').write_text(json.dumps(targets))
    for rel, text in files.items():
        p = root / 'src/patches' / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return root


T = [{'id': 'photos', 'enabled': True, 'candidates': [
        {'name': 'rushi', 'owner': 'r', 'repo': 'p', 'patch_dir': 'photos-rushi'},
        {'name': 'akash', 'owner': 'a', 'repo': 'p', 'patch_dir': 'photos-akash', 'fallback': True}],
      'extra_bundles': [{'name': 'extra', 'owner': 'e', 'repo': 'p', 'patch_dir': 'photos-extra'}]}]
EMPTY = {'photos-rushi/include-patches': '', 'photos-rushi/exclude-patches': '',
         'photos-akash/include-patches': '', 'photos-akash/exclude-patches': '',
         'photos-extra/include-patches': '', 'photos-extra/exclude-patches': ''}


class OwnerPolicy(unittest.TestCase):
    def test_head_policy_only_for_the_owner(self):
        base = tree(['amazonmusic'], [], T, EMPTY)
        head = tree(['amazonmusic', 'facebook'], [('facebook', 'Unlock app icons')], T, EMPTY)
        self.assertEqual(oc.owner_policy(base)['paid_unlock_ok_offline_apps'], ['amazonmusic'])
        self.assertEqual(oc.owner_policy(base)['owner_takes'], [])
        p = oc.owner_policy(base, head)
        self.assertEqual(p['paid_unlock_ok_offline_apps'], ['amazonmusic', 'facebook'])
        self.assertEqual(p['owner_takes'], ['facebook: Unlock app icons'])
        self.assertIn('repository owner wrote', p['source'])
        self.assertEqual(oc.manifest(base, head)['owner_policy']['paid_unlock_ok_offline_apps'], ['amazonmusic'])
        self.assertEqual(oc.manifest(base, head, True)['owner_policy']['paid_unlock_ok_offline_apps'], ['amazonmusic', 'facebook'])

    def test_workflow_passes_the_flag_only_for_the_owner_on_this_repo(self):
        text = (ROOT / '.github/workflows/onboard-review.yml').read_text()
        self.assertIn('if [ "$PR_AUTHOR" = "$REPO_OWNER" ] && [ "$HEAD_REPO" = "$THIS_REPO" ]; then OWNER_FLAG="--owner-pr"; fi', text)
        self.assertIn('REPO_OWNER: ${{ github.repository_owner }}', text)
        self.assertIn('if ! grep -q -- "--owner-pr" base/src/etc/onboard_check.py; then OWNER_FLAG=""; fi', text)
        self.assertIn('owner_takes', (ROOT / 'docs/council/ONBOARD.md').read_text())


class SameBuild(unittest.TestCase):
    def test_fallback_and_exclude_are_not_duplicates(self):
        files = dict(EMPTY)
        files['photos-rushi/exclude-patches'] = 'AMOLED dark theme\n'
        files['photos-akash/include-patches'] = 'AMOLED dark theme\n'
        base, head = tree([], [], T, EMPTY), tree([], [], T, files)
        self.assertEqual(oc.manifest(base, head)['same_build_duplicates'], [])

    def test_candidate_plus_extra_is_a_duplicate(self):
        files = dict(EMPTY)
        files['photos-rushi/include-patches'] = 'Hide ads\n'
        files['photos-extra/include-patches'] = 'Hide ads\n'
        base, head = tree([], [], T, EMPTY), tree([], [], T, files)
        self.assertEqual(oc.manifest(base, head)['same_build_duplicates'],
                         [{'target': 'photos', 'name': 'Hide ads', 'bundles': ['rushi', 'extra']}])


def row(seat, verdict, findings=(), status='OK'):
    if status != 'OK':
        return {'seat': seat, 'model': '', 'status': status, 'answer': None}
    return {'seat': seat, 'model': 'm', 'status': 'OK', 'answer': {
        'verdict': verdict, 'summary': seat + ' says', 'findings': list(findings), 'dropped': 0, 'unshipped': 0, 'counted': True}}


class Render(unittest.TestCase):
    F = {'severity': 'high', 'item': 'Unlock app icons', 'quote': 'Unlock app icons', 'issue': 'rule 1'}

    def test_one_line_per_finding_and_plumbing_folds(self):
        rows = [row('gpt', 'block', [self.F]), row('kilo', 'block', [dict(self.F, severity='low')]),
                row('groq', 'approve'), row('open', '', status='UNAVAILABLE no listed model answered')]
        body = orv.render(rows, False, '2 of 3 counted verdicts say block', {'problems': []})
        self.assertEqual(body.count('`Unlock app icons`'), 1)
        self.assertIn('(quote: "Unlock app icons"; gpt, kilo)', body)
        self.assertIn('1 seat(s) did not answer (seat plumbing, not about this change)', body)
        self.assertNotIn('| open |', body)

    def test_unchanged_review_is_not_reposted(self):
        rows = [row('gpt', 'approve')]
        body = orv.render(rows, True, '1 counted verdict(s), 0 block', {'problems': []})
        calls = []

        def gh(env, method, path, body=None):
            calls.append(method)
            if method == 'GET':
                return [{'id': 7, 'body': body_old, 'user': {'type': 'Bot'}}]
            return {}
        body_old = body.replace('gpt says', 'gpt said it differently')
        real = orv.gh
        orv.gh = gh
        try:
            orv.post({}, 'o/r', '1', body)
        finally:
            orv.gh = real
        self.assertEqual(calls, ['GET'])


if __name__ == '__main__':
    unittest.main()
