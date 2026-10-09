"""Contracts for the plain-language status page (packet W2, 8 Oct 2026).

src/etc/status.py runs against a fake GitHub; docs/status.js is checked for the same
read-only page rules the portal follows. No network.
"""
import base64
import importlib.util
import json
import re
import unittest
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pf_status', ROOT / 'src/etc/status.py')
st = importlib.util.module_from_spec(spec)
spec.loader.exec_module(st)
R = 'repos/' + st.REPO
WEB = st.WEB


def run(rid, name, conclusion, event='schedule', status='completed', when='2026-10-08T06:00:00Z'):
    return {'id': rid, 'run_attempt': 1, 'name': name, 'status': status, 'conclusion': conclusion, 'event': event,
            'updated_at': when, 'html_url': WEB + '/actions/runs/%d' % rid}


def job(jid, name, conclusion, step=None, when='2026-10-08T06:10:00Z'):
    steps = [{'name': 'Set up job', 'conclusion': 'success', 'number': 1}]
    if step:
        steps.append({'name': step, 'conclusion': conclusion, 'number': 2})
    return {'id': jid, 'name': name, 'status': 'completed', 'conclusion': conclusion, 'completed_at': when,
            'html_url': WEB + '/actions/runs/1/job/%d' % jid, 'steps': steps}


def marker(min_sdk):
    doc = base64.b64encode(json.dumps({'min_sdk': min_sdk, 'arch': 'arm64-v8a'}).encode()).decode()
    return 'notes\n\n[pf-release-v1]: # "%s"\n' % doc


TARGETS = [
    {'id': 'youtube', 'enabled': True, 'label': 'YouTube', 'tag_prefix': 'youtube-morphe', 'needs_microg': True, 'min_sdk_ceiling': 29},
    {'id': 'reddit', 'enabled': True, 'label': 'Reddit', 'tag_prefix': 'reddit', 'min_sdk_ceiling': 29},
    {'id': 'facebook', 'enabled': True, 'label': 'Facebook', 'tag_prefix': 'facebook', 'min_sdk_ceiling': 30},
    {'id': 'old', 'enabled': False, 'label': 'Old'}]


def world():
    return {
        R + '/actions/workflows?per_page=100': {'workflows': [
            {'id': 1, 'name': '2. Check new patch', 'path': '.github/workflows/ci.yml', 'state': 'active'},
            {'id': 2, 'name': '7. Nightly watch', 'path': '.github/workflows/watch.yml', 'state': 'active'},
            {'id': 3, 'name': 'Gone', 'path': '.github/workflows/gone.yml', 'state': 'disabled_manually'}]},
        R + '/actions/workflows/1/runs?per_page=10': {'workflow_runs': [
            run(11, '2. Check new patch', 'failure'), run(12, '2. Check new patch', 'success', when='2026-10-07T06:00:00Z'),
            run(13, 'ATTACKER NAME', 'success', event='pull_request')]},
        R + '/actions/workflows/2/runs?per_page=5': {'workflow_runs': [run(21, '7. Nightly watch', 'success')]},
        R + '/actions/runs/11/attempts/1/jobs?per_page=100': {'jobs': [
            job(101, 'build (reddit) / Patch reddit', 'failure', 'Patch apk'),
            job(102, 'build (youtube) / Patch youtube', 'skipped'),
            job(103, 'Resolve shadow dependencies (youtube)', 'success')]},
        R + '/actions/runs/12/attempts/1/jobs?per_page=100': {'jobs': [
            job(201, 'build (youtube) / Patch youtube', 'success', when='2026-10-07T06:10:00Z')]},
        R + '/check-runs/101/annotations?per_page=50': [
            {'annotation_level': 'failure', 'message': 'needs SDK 31, device is 29. Set max_app_version in src/targets.json.'},
            {'annotation_level': 'failure', 'message': 'Process completed with exit code 1.'},
            {'annotation_level': 'failure', 'message': 'leaked ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123 here'}],
        R + '/releases?per_page=100&page=1': [
            {'tag_name': 'youtube-morphe-v21.36.45-b2026100700000000000000001100000001', 'draft': False,
             'published_at': '2026-10-07T07:00:00Z', 'html_url': WEB + '/releases/tag/youtube-morphe-v21.36.45-b1',
             'body': marker(28), 'assets': [{'name': 'youtube-v21.36.45-arm64-v8a.apk', 'size': 90000000,
                                             'browser_download_url': WEB + '/releases/download/t/youtube-v21.36.45-arm64-v8a.apk'}]},
            {'tag_name': 'reddit-v2026.1.0-b20260901', 'draft': False, 'published_at': '2026-09-01T00:00:00Z',
             'html_url': 'https://evil.example/x', 'body': '', 'assets': []}],
        R + '/issues?state=open&per_page=100': [
            {'title': 'Failing: 2. Check new patch', 'html_url': WEB + '/issues/200', 'number': 200},
            {'title': 'something else', 'html_url': WEB + '/issues/201', 'number': 201}],
    }


def reader(w, missing=()):
    def fetch(path):
        if path not in missing and path not in w and path.startswith(R + '/commits?'):
            return [{'sha': 'f' * 40}] if 'ci.yml' in path else []
        if path in missing or path not in w:
            raise urllib.error.HTTPError('u', 404, 'nf', {}, None)
        return w[path]
    return st.Reader(None, fetch)


class Status(unittest.TestCase):
    def setUp(self):
        self.r = reader(world())
        self.d = st.build(self.r, TARGETS, now='2026-10-08T07:00:00Z')
        self.apps = {a['id']: a for a in self.d['apps']}

    def test_failed_build_says_where_and_why_in_plain_words(self):
        lb = self.apps['reddit']['last_build']
        self.assertEqual(lb['words'], 'Failed')
        self.assertEqual(lb['step'], 'Patch apk')
        self.assertEqual(lb['step_plain'], 'downloading the original app and applying the patches')
        self.assertTrue(lb['why'][0].startswith('This app version needs Android 12 (API 31)'))
        self.assertIn('tries up to 3 lower versions', lb['why'][0])
        self.assertFalse(any('exit code' in w for w in lb['why']))
        self.assertTrue(any('[redacted]' in w for w in lb['why']))
        self.assertFalse(any('ghp_' in w for w in lb['why']))

    def test_skipped_check_does_not_hide_the_last_real_build(self):
        y = self.apps['youtube']
        self.assertEqual(y['last_check']['words'], 'Skipped (nothing to do)')
        self.assertEqual(y['last_build']['words'], 'Worked')
        self.assertTrue(y['needs_microg'])
        self.assertEqual(y['release']['version'], '21.36.45')
        self.assertEqual(y['release']['min_android'], {'api': 28, 'version': '9'})

    def test_disabled_apps_and_pull_request_runs_are_left_out(self):
        self.assertNotIn('old', self.apps)
        text = json.dumps(self.d)
        self.assertNotIn('ATTACKER', text)
        self.assertNotIn('Gone', [w['name'] for w in self.d['workflows']])

    def test_foreign_links_are_dropped(self):
        self.assertIsNone(self.apps['reddit']['release']['url'])
        self.assertNotIn('evil.example', json.dumps(self.d))

    def test_workflow_rows_explain_purpose_and_failures(self):
        ci = [w for w in self.d['workflows'] if w['file'] == 'ci.yml'][0]
        self.assertIn('builds the apps that changed', ci['purpose'])
        self.assertEqual(ci['last']['words'], 'Failed')
        self.assertEqual(ci['last']['jobs'][0]['step_plain'], 'downloading the original app and applying the patches')
        self.assertEqual(len(ci['recent']), 2)
        self.assertEqual(self.d['issues'], [{'title': 'Failing: 2. Check new patch', 'url': WEB + '/issues/200', 'number': 200}])
        self.assertIn('need a look', self.d['headline']['text'])
        self.assertEqual(self.apps['facebook']['android_cap'], {'api': 30, 'version': '11'})

    def test_version_step_down_reads_in_plain_words(self):
        text = st.plain_reason('VERSION_STEP_DOWN step=1 from=4.1.1258 to=4.1.1255.1 source=provider ceiling=29')
        self.assertEqual(text, 'Version 4.1.1258 needed a newer Android, so the build tried 4.1.1255.1 instead (step 1 of 3).')

    def test_hyphens_survive_cleaning(self):
        # W4: a bare '-' in the character class turned every hyphen into a space.
        self.assertEqual(st.clean('manual-patch.yml'), 'manual-patch.yml')
        self.assertEqual(st.clean('adguard-v4.14.68-arm64-v8a.apk'), 'adguard-v4.14.68-arm64-v8a.apk')
        self.assertEqual(st.clean('a\x00b\u202ec'), 'a b c')

    def test_failure_stays_listed_until_a_later_run_works(self):
        # Owner, 8 Oct 2026: age never hides a failure; only a later success clears it.
        d = st.build(self.r, TARGETS, now='2026-11-08T07:00:00Z')
        ci = [w for w in d['workflows'] if w['file'] == 'ci.yml'][0]
        self.assertTrue(ci['last']['old'])
        self.assertGreater(ci['last']['age_days'], st.STALE_DAYS)
        # W6: only the Reddit job failed, so the Reddit row carries it, not the automation.
        self.assertIn('Reddit', d['headline']['apps'])
        self.assertTrue(ci['last']['per_app'])
        self.assertEqual(ci['last']['apps'], ['reddit'])
        self.assertNotIn(ci['name'], d['headline']['workflows'])
        self.assertIs(ci['last']['changed_since'], True)
        self.assertIn(ci['name'], d['headline']['run_once_to_confirm'])

    def test_build_failure_outside_an_app_job_keeps_the_workflow_listed(self):
        # W6: a Plan or resolve failure belongs to no app, so the automation row stays red.
        w = world()
        w[R + '/actions/runs/11/attempts/1/jobs?per_page=100']['jobs'].append(job(104, 'Plan', 'failure', 'Plan'))
        d = st.build(reader(w), TARGETS, now='2026-10-08T07:00:00Z')
        ci = [x for x in d['workflows'] if x['file'] == 'ci.yml'][0]
        self.assertNotIn('per_app', ci['last'])
        self.assertIn(ci['name'], d['headline']['workflows'])
        self.assertIn('Reddit', d['headline']['apps'])

    def test_failure_of_an_unknown_or_disabled_app_keeps_the_workflow_listed(self):
        for name in ('build (old) / Patch old', 'Patch nosuchapp'):
            with self.subTest(name=name):
                w = world()
                w[R + '/actions/runs/11/attempts/1/jobs?per_page=100']['jobs'] = [job(101, name, 'failure', 'Refuse an unknown app id')]
                d = st.build(reader(w), TARGETS, now='2026-10-08T07:00:00Z')
                ci = [x for x in d['workflows'] if x['file'] == 'ci.yml'][0]
                self.assertNotIn('per_app', ci['last'])
                self.assertIn(ci['name'], d['headline']['workflows'])

    def test_unreadable_jobs_never_mark_a_failure_per_app(self):
        r = reader(world(), missing={R + '/actions/runs/11/attempts/1/jobs?per_page=100'})
        d = st.build(r, TARGETS, now='2026-10-08T07:00:00Z')
        ci = [x for x in d['workflows'] if x['file'] == 'ci.yml'][0]
        self.assertNotIn('per_app', ci['last'])
        self.assertIn(ci['name'], d['headline']['workflows'])

    def test_a_later_build_of_another_app_does_not_clear_a_failed_app(self):
        # W6: the 9 Oct case. Manual Patch: Amazon Music failed after LinkedIn worked.
        t = TARGETS + [{'id': 'amazonmusic', 'enabled': True, 'label': 'Amazon Music', 'min_sdk_ceiling': 29},
                       {'id': 'linkedin', 'enabled': True, 'label': 'LinkedIn', 'min_sdk_ceiling': 29}]
        w = world()
        w[R + '/actions/workflows?per_page=100']['workflows'].append(
            {'id': 4, 'name': '1. Manual Patch', 'path': '.github/workflows/manual-patch.yml', 'state': 'active'})
        w[R + '/actions/workflows/4/runs?per_page=10'] = {'workflow_runs': [
            run(41, '1. Manual Patch', 'success', event='workflow_dispatch', when='2026-10-08T06:30:00Z'),
            run(42, '1. Manual Patch', 'failure', event='workflow_dispatch', when='2026-10-08T06:20:00Z')]}
        w[R + '/actions/runs/41/attempts/1/jobs?per_page=100'] = {'jobs': [
            job(411, 'Patch linkedin', 'success', when='2026-10-08T06:30:00Z')]}
        w[R + '/actions/runs/42/attempts/1/jobs?per_page=100'] = {'jobs': [
            job(421, 'Patch amazonmusic', 'failure', 'Verify finished APK identity', when='2026-10-08T06:20:00Z')]}
        d = st.build(reader(w), t, now='2026-10-08T07:00:00Z')
        apps = {a['id']: a for a in d['apps']}
        self.assertEqual(apps['amazonmusic']['last_build']['result'], 'failure')
        self.assertEqual(apps['linkedin']['last_build']['result'], 'success')
        self.assertIn('Amazon Music', d['headline']['apps'])
        self.assertNotIn('LinkedIn', d['headline']['apps'])

    def test_a_cancel_replaced_by_a_newer_run_is_not_a_failure(self):
        # W12: "Status page data" cancels its own older run (cancel-in-progress); run
        # 37982178420 on 9 Oct showed as a red automation although nothing failed.
        w = world()
        w[R + '/actions/workflows/2/runs?per_page=5'] = {'workflow_runs': [
            run(24, '7. Nightly watch', None, status='in_progress', when='2026-10-08T06:30:00Z'),
            run(23, '7. Nightly watch', 'cancelled', when='2026-10-08T06:20:00Z'),
            run(22, '7. Nightly watch', 'success', when='2026-10-08T06:10:00Z')]}
        d = st.build(reader(w), TARGETS, now='2026-10-08T07:00:00Z')
        nw = [x for x in d['workflows'] if x['file'] == 'watch.yml'][0]
        self.assertEqual(nw['last']['words'], 'Worked')
        self.assertNotIn('7. Nightly watch', d['headline']['workflows'])
        self.assertEqual(len(nw['recent']), 3)

    def test_the_newest_cancel_still_counts(self):
        # Nothing newer replaced it, so it stays visible.
        w = world()
        w[R + '/actions/workflows/2/runs?per_page=5'] = {'workflow_runs': [
            run(23, '7. Nightly watch', 'cancelled', when='2026-10-08T06:20:00Z'),
            run(22, '7. Nightly watch', 'success', when='2026-10-08T06:10:00Z')]}
        w[R + '/actions/runs/23/attempts/1/jobs?per_page=100'] = {'jobs': []}
        d = st.build(reader(w), TARGETS, now='2026-10-08T07:00:00Z')
        self.assertIn('7. Nightly watch', d['headline']['workflows'])

    def test_failed_reads_are_unknown_never_fine(self):
        r = reader(world(), missing={R + '/releases?per_page=100&page=1'})
        d = st.build(r, TARGETS, now='2026-10-08T07:00:00Z')
        self.assertTrue(d['problems'])
        self.assertTrue(d['headline']['text'].startswith('Partly unknown'))
        self.assertFalse({a['id']: a for a in d['apps']}['reddit']['release_known'])

    def test_page_is_read_only_and_never_writes_html(self):
        # W4: Builds and Watch in docs/portal.js show this data. W7: the old status.html
        # redirect page is gone; the app shelf's #builds and #watch tabs are the only views.
        js = (ROOT / 'docs/portal.js').read_text(encoding='utf-8')
        for bad in ('innerHTML', 'outerHTML', 'insertAdjacentHTML', 'document.write', 'localStorage', 'sessionStorage',
                    'Authorization', 'method:', 'eval(', 'new Function'):
            self.assertNotIn(bad, js, bad)
        self.assertIn("credentials:'omit'", js)
        self.assertIn("u.pathname==='/'+REPO+'/status/status.json'", js)
        self.assertFalse((ROOT / 'docs/status.js').exists())
        self.assertFalse((ROOT / 'docs/status.html').exists())


if __name__ == '__main__':
    unittest.main()
