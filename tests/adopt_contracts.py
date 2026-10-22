"""W15b auto-adopt (owner rule 17 Oct, details 20 Oct 2026): name AND index description, unsure
means wait, one pull request, the bot never merges, the right provider folder gets the name."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/etc'))
import selection_watch as sw  # noqa: E402

POLICY = sw.adopt_policy(ROOT)
DESC = {('sysadmindoc/hushgram', 'Install next to Instagram'): [({'com.instagram.android'}, 'Installs this build as a second Instagram beside your normal one, with its own data and sign-in. Pick its package name and app name.')],
        ('sysadmindoc/hushgram', 'Hide paid partnership Reels'): [({'com.instagram.android'}, 'Leaves out reels with a Paid partnership label, and reels Instagram marks as boosted. Starts off.')],
        ('rushiranpise/morphe-patches', 'Unlock VIP Lifetime'): [({'com.estrongs.android.pop'}, 'Unlocks VIP lifetime features in ES File Explorer Phone and TV.')],
        ('rushiranpise/morphe-patches', 'Unlock Premium'): [({'org.telegram.messenger'}, 'Unlocks premium features.')],
        ('sysadmindoc/hushgram', 'Glass tab bar'): [({'com.whatsapp'}, 'For another app.')]}


def row(target, owner, repo):
    return {'target': target, 'owner': owner, 'repo': repo}


class Classify(unittest.TestCase):
    def call(self, r, pkg, name, flag=''):
        return sw.classify(POLICY, DESC, r, pkg, name, flag)[0]

    def test_owner_calls_of_20_oct_hold(self):
        ig = row('instagram', 'SysAdminDoc', 'HushGram')
        self.assertEqual(self.call(ig, 'com.instagram.android', 'Install next to Instagram'), 'hold')
        self.assertEqual(self.call(ig, 'com.instagram.android', 'Hide paid partnership Reels'), 'adopt')

    def test_reserved_name_waits_for_its_owner_given_provider(self):
        # W15d: owner E1 gave Photos "AMOLED dark theme" to Akash-Sriram; adopt PR #202 put it on rushiranpise.
        d = {('rushiranpise/morphe-patches', 'AMOLED dark theme'): [({'com.google.android.apps.photos'}, 'Pure black dark theme.')],
             ('akash-sriram/morphe-google-photos', 'AMOLED dark theme'): [({'com.google.android.apps.photos'}, 'Pure black dark theme.')]}
        rush = dict(row('photos', 'rushiranpise', 'morphe-patches'), name='rushiranpise')
        akash = dict(row('photos', 'Akash-Sriram', 'morphe-google-photos'), name='akash')
        call, why = sw.classify(POLICY, d, rush, 'com.google.android.apps.photos', 'AMOLED dark theme', '')
        self.assertEqual((call, why.split(':')[0]), ('hold', 'reserved for akash-sriram by the owner'))
        self.assertEqual(sw.classify(POLICY, d, akash, 'com.google.android.apps.photos', 'AMOLED dark theme', '')[0], 'adopt')
        other = dict(row('facebook', 'RookieEnough', 'De-Vanced'), name='derevanced')
        d2 = {('rookieenough/de-vanced', 'AMOLED dark theme'): [({'com.facebook.katana'}, 'Pure black dark theme.')]}
        self.assertEqual(sw.classify(POLICY, d2, other, 'com.facebook.katana', 'AMOLED dark theme', '')[0], 'adopt')

    def test_paid_words_only_on_offline_apps(self):
        self.assertEqual(self.call(row('esfile', 'rushiranpise', 'morphe-patches'), 'com.estrongs.android.pop', 'Unlock VIP Lifetime'), 'adopt')
        self.assertEqual(self.call(row('telegram', 'rushiranpise', 'morphe-patches'), 'org.telegram.messenger', 'Unlock Premium'), 'hold')

    def test_unsure_means_wait(self):
        ig = row('instagram', 'SysAdminDoc', 'HushGram')
        self.assertEqual(sw.classify(POLICY, DESC, ig, 'com.instagram.android', 'Brand new', ''), ('hold', 'no description in the community index'))
        self.assertEqual(self.call(ig, 'com.instagram.android', 'Glass tab bar'), 'hold')  # described for another package only
        self.assertEqual(self.call(ig, 'com.instagram.android', 'Hide paid partnership Reels', 'BAN'), 'hold')
        self.assertEqual(self.call(ig, 'com.instagram.android', 'Hide paid partnership Reels', 'CFM'), 'hold')

    def test_policy_keeps_the_owner_veto_and_offline_list(self):
        self.assertEqual(sorted(POLICY['paid_ok_targets']), ['esfile', 'keymapper', 'mxplayer'])
        targets = {t['id'] for t in json.loads((ROOT / 'src/targets.json').read_text())}
        self.assertTrue(set(POLICY['paid_ok_targets']) <= targets)
        for w in ('package name', 'clone', 'signature', 'spoof', 'version code'):
            self.assertIn(w, POLICY['hold_words'])


class Holds(unittest.TestCase):
    """W15b holds read from data (owner, 20 Oct 2026: older names go through the rule too)."""
    def test_same_name_under_another_bundle_waits(self):
        r = row('instagram', 'SysAdminDoc', 'HushGram')
        self.assertEqual(sw.classify(POLICY, DESC, r, 'com.instagram.android', 'Hide paid partnership Reels', '',
                                     {'Hide paid partnership Reels'})[0], 'hold')

    def test_always_on_content_hide_waits_but_a_switch_or_ad_target_passes(self):
        d = {('a/b', 'Hide all stories'): [({'p'}, 'Hides all stories from the tray in the feed page.')],
             ('a/b', 'Hide comments'): [({'p'}, 'Takes the Comment button off. Starts off. Turn it on in X settings > Comments.')],
             ('a/b', 'Hide sponsored posts'): [({'p'}, 'Hides sponsored posts.')]}
        r = row('instagram', 'a', 'b')
        self.assertEqual(sw.classify(POLICY, d, r, 'p', 'Hide all stories', '')[0], 'hold')
        self.assertEqual(sw.classify(POLICY, d, r, 'p', 'Hide comments', '')[0], 'adopt')
        self.assertEqual(sw.classify(POLICY, d, r, 'p', 'Hide sponsored posts', '')[0], 'adopt')

    def test_universal_toolbox_patch_waits(self):
        d = {('a/b', 'Add Save Data'): [(set(), 'Unpacks bundled save-data zip(s) into the app storage.')]}
        self.assertEqual(sw.classify(POLICY, d, row('esfile', 'a', 'b'), 'com.estrongs.android.pop', 'Add Save Data', '')[1],
                         'universal patch: the index ties it to no app, so it was not written for this one')

    def test_real_index_keeps_the_owner_calls(self):
        real = sw.index_descriptions(ROOT)
        ig = row('instagram', 'SysAdminDoc', 'HushGram')
        self.assertEqual(sw.classify(POLICY, real, ig, 'com.instagram.android', 'Install next to Instagram', '')[0], 'hold')
        self.assertEqual(sw.classify(POLICY, real, ig, 'com.instagram.android', 'Hide paid partnership Reels', '')[0], 'adopt')
        es = row('esfile', 'rushiranpise', 'morphe-patches')
        self.assertEqual(sw.classify(POLICY, real, es, 'com.estrongs.android.pop', 'Unlock VIP Lifetime', '')[0], 'adopt')
        hs = row('hotstar', 'durgesh0505', 'chiggi_morphe_patches')
        self.assertEqual(sw.classify(POLICY, real, hs, 'in.startv.hotstar', 'Premium unlock', '')[0], 'hold')


class Adopt(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.out = Path(self.t.name)
        self.calls = []

    def plan(self, waiting):
        (self.out / 'plan.json').write_text(json.dumps({'waiting': waiting}))

    def runner(self, prs='[]', fail=None):
        def run(cmd, **k):
            self.calls.append(cmd)
            out = prs if cmd[:3] == ['gh', 'pr', 'list'] else ('42' if cmd[:3] == ['gh', 'pr', 'view'] else '')
            code = 1 if fail and fail(cmd) else 0
            return subprocess.CompletedProcess(cmd, code, out, 'refused' if code else '')
        return run

    # The branch name carries GITHUB_RUN_ID; Actions sets it, so the test pins it (W15b validate red, 20 Oct).
    @mock.patch.dict('os.environ', {'GITHUB_RUN_ID': 'T1'})
    def test_one_pull_request_with_reasons_and_checks_started(self):
        self.plan([{'target': 'instagram', 'provider': 'hushgram', 'name': 'Accent color', 'call': 'adopt', 'why': 'rule'},
                   {'target': 'instagram', 'provider': 'hushgram', 'name': 'Install next to Instagram', 'call': 'hold', 'why': 'hold word'}])
        self.assertEqual(sw.adopt(ROOT, self.out, 'o/r', self.runner(), stamp='2026-10-21'), 0)
        app = [c for c in self.calls if c[:2] == ['python3', 'src/etc/app.py']]
        self.assertEqual(len(app), 1)
        self.assertEqual(app[0][3:8], ['instagram', '--bundle', 'hushgram', '--patches', 'Accent color'])
        self.assertNotIn('Install next to Instagram', ' '.join(sum(self.calls, [])))
        self.assertIn(['gh', 'workflow', 'run', 'validate.yml', '--repo', 'o/r', '--ref', 'adopt/2026-10-21-T1'], self.calls)
        self.assertTrue(any(c[:4] == ['gh', 'workflow', 'run', 'onboard-review.yml'] and 'pr=42' in c for c in self.calls))
        self.assertFalse(any('merge' in c for c in self.calls))
        # hushgram is Instagram's fallback, so its test build names the provider; never publishes.
        self.assertIn(['gh', 'workflow', 'run', 'manual-patch.yml', '--repo', 'o/r', '--ref', 'adopt/2026-10-21-T1',
                       '-f', 'target=instagram', '-f', 'publish=false', '-f', 'provider=hushgram'], self.calls)

    def test_waits_while_an_adopt_pull_request_is_open(self):
        self.plan([{'target': 'linkedin', 'provider': 'heyymichii', 'name': 'Material You', 'call': 'adopt', 'why': 'rule'}])
        self.assertEqual(sw.adopt(ROOT, self.out, 'o/r', self.runner('[{"number": 7, "headRefName": "adopt/x"}]')), 0)
        self.assertFalse(any(c[:2] == ['python3', 'src/etc/app.py'] for c in self.calls))

    def test_nothing_adopted_opens_nothing(self):
        self.plan([{'target': 'linkedin', 'provider': 'heyymichii', 'name': 'X', 'call': 'hold', 'why': 'h'}])
        self.assertEqual(sw.adopt(ROOT, self.out, 'o/r', self.runner()), 0)
        self.assertEqual(self.calls, [])

    def pending(self, create_code):
        self.plan([{'target': 'linkedin', 'provider': 'heyymichii', 'name': 'Material You', 'call': 'adopt', 'why': 'rule'}])
        (self.out / 'report.md').write_text('# report\n')
        def run(cmd, **k):
            self.calls.append(cmd)
            if cmd[:2] == ['git', 'ls-remote']:
                return subprocess.CompletedProcess(cmd, 0, 'abc\trefs/heads/adopt/2026-10-20-39485415276\n', '')
            if cmd[:3] == ['gh', 'pr', 'create']:
                return subprocess.CompletedProcess(cmd, create_code, '', 'GraphQL: GitHub Actions is not permitted' if create_code else '')
            if cmd[:3] == ['gh', 'pr', 'view']:
                return subprocess.CompletedProcess(cmd, 0, '43', '')
            return subprocess.CompletedProcess(cmd, 0, '[]', '')
        return sw.adopt(ROOT, self.out, 'o/r', run, stamp='2026-10-21')

    def test_a_pushed_branch_without_a_pull_request_waits_and_never_pushes_another(self):
        # W15c (20 Oct 2026): GitHub refused the bot's pull request; no second branch the next day.
        self.assertEqual(self.pending(1), 0)
        self.assertFalse(any(c[:2] == ['python3', 'src/etc/app.py'] or c[:2] == ['git', 'push'] for c in self.calls))
        text = (self.out / 'report.md').read_text()
        self.assertIn('adopt/2026-10-20-39485415276 has no pull request', text)
        self.assertIn('compare/main...adopt/2026-10-20-39485415276', text)

    def test_a_pending_branch_gets_its_pull_request_once_github_allows_it(self):
        self.assertEqual(self.pending(0), 0)
        self.assertFalse(any(c[:2] == ['git', 'push'] for c in self.calls))
        self.assertIn(['gh', 'workflow', 'run', 'validate.yml', '--repo', 'o/r', '--ref', 'adopt/2026-10-20-39485415276'], self.calls)
        self.assertTrue(any(c[:3] == ['gh', 'pr', 'create'] and 'adopt/2026-10-20-39485415276' in c for c in self.calls))

    def test_the_first_refusal_is_red_once(self):
        self.plan([{'target': 'linkedin', 'provider': 'heyymichii', 'name': 'Material You', 'call': 'adopt', 'why': 'rule'}])
        def run(cmd, **k):
            self.calls.append(cmd)
            if cmd[:3] == ['gh', 'pr', 'create']:
                return subprocess.CompletedProcess(cmd, 1, '', 'refused')
            return subprocess.CompletedProcess(cmd, 0, '[]' if cmd[:3] == ['gh', 'pr', 'list'] else '', '')
        self.assertEqual(sw.adopt(ROOT, self.out, 'o/r', run, stamp='2026-10-21'), 1)
        self.assertTrue(any(c[:2] == ['git', 'push'] for c in self.calls))

    def test_a_branch_whose_pull_request_was_closed_or_merged_does_not_block(self):
        self.plan([{'target': 'linkedin', 'provider': 'heyymichii', 'name': 'Material You', 'call': 'adopt', 'why': 'rule'}])
        def run(cmd, **k):
            self.calls.append(cmd)
            if cmd[:2] == ['git', 'ls-remote']:
                return subprocess.CompletedProcess(cmd, 0, 'abc\trefs/heads/adopt/old\n', '')
            if cmd[:3] == ['gh', 'pr', 'list'] and '--head' in cmd:
                return subprocess.CompletedProcess(cmd, 0, '[{"number": 5}]', '')
            return subprocess.CompletedProcess(cmd, 0, '[]' if cmd[:3] == ['gh', 'pr', 'list'] else ('42' if cmd[:3] == ['gh', 'pr', 'view'] else ''), '')
        self.assertEqual(sw.adopt(ROOT, self.out, 'o/r', run, stamp='2026-10-21'), 0)
        self.assertTrue(any(c[:2] == ['git', 'push'] for c in self.calls))
        # W15d: the spent branch is deleted, and only that one.
        self.assertIn(['git', 'push', 'origin', '--delete', 'adopt/old'], self.calls)
        self.assertEqual(sum(1 for c in self.calls if '--delete' in c), 1)

    def test_a_workflow_change_is_never_pushed(self):
        self.plan([{'target': 'linkedin', 'provider': 'heyymichii', 'name': 'Material You', 'call': 'adopt', 'why': 'rule'}])
        rc = sw.adopt(ROOT, self.out, 'o/r', self.runner(fail=lambda c: c[:3] == ['git', 'diff', '--quiet']))
        self.assertEqual(rc, 1)
        self.assertFalse(any(c[:2] == ['git', 'push'] for c in self.calls))


class Bundle(unittest.TestCase):
    def test_patch_lands_in_the_named_provider_folder_with_its_reason(self):
        with tempfile.TemporaryDirectory() as d:
            for part in ('src', 'docs/review/onboarding'):
                shutil.copytree(ROOT / part, Path(d) / part, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns('__pycache__', 'community'))
            r = subprocess.run([sys.executable, 'src/etc/app.py', 'patch', 'instagram', '--bundle', 'hushgram',
                                '--patches', 'Test only name', '--why', '{"Test only name": "by the adopt rule (test)"}', '--no-regen'],
                               cwd=d, capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            hush = (Path(d) / 'src/patches/instagram-hushgram/include-patches').read_text()
            piko = (Path(d) / 'src/patches/instagram-piko/include-patches').read_text()
            self.assertIn('Test only name', hush.splitlines())
            self.assertNotIn('Test only name', piko.splitlines())
            self.assertIn('- Test only name: added', (Path(d) / 'docs/review/onboarding/instagram.md').read_text())
            self.assertIn('by the adopt rule (test)', (Path(d) / 'docs/review/onboarding/instagram.md').read_text())
            bad = subprocess.run([sys.executable, 'src/etc/app.py', 'patch', 'instagram', '--bundle', 'nope',
                                  '--patches', 'X', '--no-regen'], cwd=d, capture_output=True, text=True, timeout=120)
            self.assertNotEqual(bad.returncode, 0)


if __name__ == '__main__':
    unittest.main()


class RecordDecision(unittest.TestCase):
    """W15d: a record the adopt rule creates says the rule made it, not an owner "5. Add target" request."""

    def write(self, **kw):
        import importlib
        app = importlib.import_module('app')
        t = {'id': 'demo', 'label': 'Demo', 'package': 'com.demo', 'candidates': []}
        with tempfile.TemporaryDirectory() as td, mock.patch.object(app, 'RECORDS', Path(td)):
            app.write_record(t, **kw)
            return (Path(td) / 'demo.md').read_text(encoding='utf-8')

    def test_rule_record_names_the_rule(self):
        text = self.write(decision='Selection watch adopt rule (src/patches/ADOPT.json) on 2026-10-22.')
        self.assertIn('## Decision\nSelection watch adopt rule', text)
        self.assertNotIn('5. Add target', text)

    def test_owner_record_keeps_the_add_target_text(self):
        self.assertIn('Owner request through "5. Add target" on', self.write())

    def test_cmd_patch_passes_the_rule_decision_only_with_why(self):
        src = (ROOT / 'src/etc/app.py').read_text(encoding='utf-8')
        self.assertIn("'only when every check, the Onboarding review and every test build are green.' % today()) if why else None", src)
        self.assertIn('write_record(t, [n for n in added if list_mode], approved, why=why, decision=decision)', src)
