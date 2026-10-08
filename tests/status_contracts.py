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
        self.assertTrue(lb['why'][0].startswith('The newest app version needs Android 12 (API 31)'))
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

    def test_hyphens_survive_cleaning(self):
        # W4: a bare '-' in the character class turned every hyphen into a space.
        self.assertEqual(st.clean('manual-patch.yml'), 'manual-patch.yml')
        self.assertEqual(st.clean('adguard-v4.14.68-arm64-v8a.apk'), 'adguard-v4.14.68-arm64-v8a.apk')
        self.assertEqual(st.clean('a\x00b\u202ec'), 'a b c')

    def test_old_failure_is_history_not_a_current_problem(self):
        d = st.build(self.r, TARGETS, now='2026-11-08T07:00:00Z')
        ci = [w for w in d['workflows'] if w['file'] == 'ci.yml'][0]
        self.assertTrue(ci['last']['old'])
        self.assertGreater(ci['last']['age_days'], st.STALE_DAYS)
        self.assertNotIn(ci['name'], d['headline']['workflows'])
        self.assertIn(ci['name'], d['headline']['old_failures'])
        fresh = [w for w in self.d['workflows'] if w['file'] == 'ci.yml'][0]
        self.assertFalse(fresh['last']['old'])

    def test_failed_reads_are_unknown_never_fine(self):
        r = reader(world(), missing={R + '/releases?per_page=100&page=1'})
        d = st.build(r, TARGETS, now='2026-10-08T07:00:00Z')
        self.assertTrue(d['problems'])
        self.assertTrue(d['headline']['text'].startswith('Partly unknown'))
        self.assertFalse({a['id']: a for a in d['apps']}['reddit']['release_known'])

    def test_page_is_read_only_and_never_writes_html(self):
        js = (ROOT / 'docs/status.js').read_text(encoding='utf-8')
        html = (ROOT / 'docs/status.html').read_text(encoding='utf-8')
        for bad in ('innerHTML', 'outerHTML', 'insertAdjacentHTML', 'document.write', 'localStorage', 'sessionStorage',
                    'Authorization', 'method:', 'eval(', 'new Function'):
            self.assertNotIn(bad, js, bad)
        self.assertIn("credentials:'omit'", js)
        self.assertIn('/status/status.json', js)
        self.assertIn('status.js', html)
        self.assertNotIn('<script>', html)
        self.assertNotIn('type="password"', html)
        self.assertRegex(js, re.escape("u.protocol==='https:'&&u.hostname==='github.com'"))


if __name__ == '__main__':
    unittest.main()
