#!/usr/bin/env python3
"""Plain-language status of recent Actions runs, per app and per workflow (packet W2).

Owner ask, 8 Oct 2026: the Pages Builds and Watch views did not say what happened. This
reads GitHub's own records with the workflow token (GET only: workflows, runs, jobs, the
error annotations a failed step printed, releases, open "Failing:" issues) and writes one
status.json that docs/status.html shows in plain words: what ran, did it work, where it
stopped and the reason line it printed, the latest release per app, and what each app
needs on a phone (CPU, Android version, MicroG).

    GITHUB_TOKEN=... python3 src/etc/status.py --out status.json

A read that fails is written into "problems" and shown on the page as unknown, never as
fine. Pull-request runs are ignored: their names come from unreviewed files. Every text
field is cleaned (no control characters, token-shaped strings redacted, length capped) and
every link must point into this repository. Standard library only.
"""
import argparse
import base64
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = os.environ.get('PF_REPO') or 'govinda-rajulu/patch-factory'
WEB = 'https://github.com/' + REPO
MICROG = 'https://github.com/MorpheApp/MicroG-RE/releases'
BUILD_FILES = ('.github/workflows/ci.yml', '.github/workflows/manual-patch.yml', '.github/workflows/batch-patch.yml')
JOB_RX = re.compile(r'(?:^|/ )Patch ([a-z0-9][a-z0-9-]*)$')
TAG_RX = re.compile(r'^([a-z0-9-]+)-v([0-9]+(?:\.[0-9]+)*)-b([0-9]+)$')
MARKER = re.compile(r'(?m)^\[pf-release-v1\]: # "([A-Za-z0-9+/=]+)"[ \t]*$')
TOKEN = re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9_]{10,}|github_pat_[A-Za-z0-9_]{10,}|AIza[0-9A-Za-z_-]{20,}|sk-[A-Za-z0-9_-]{20,})')
NOISE = re.compile(r'^(Process completed with exit code \d+\.?|The job was canceled because .*|The operation was canceled\.?)$')
ANDROID = {21: '5.0', 22: '5.1', 23: '6', 24: '7.0', 25: '7.1', 26: '8.0', 27: '8.1', 28: '9', 29: '10', 30: '11',
           31: '12', 32: '12L', 33: '13', 34: '14', 35: '15', 36: '16'}

# What each automation is for, in plain words. Unknown workflows show their own name only.
PURPOSE = {
    'ci.yml': 'Checks the patch providers for new releases and builds the apps that changed (one full run a day, three quick checks).',
    'manual-patch.yml': 'Builds one app on request.',
    'batch-patch.yml': 'Builds several apps on request.',
    'validate.yml': 'Checks every change to the repository before it can be trusted.',
    'agent-watch.yml': 'Provider watch: looks for new or changed patch releases.',
    'watch.yml': 'Nightly watch: one report on the repository and every provider.',
    'community-watch.yml': 'Community watch: scans the community patch index for apps built here.',
    'explore.yml': 'Lists the patch names a provider offers.',
    'add-target.yml': 'Adds, changes, disables or removes an app; opens a pull request.',
    'notify-failure.yml': 'Opens one issue per failing automation and closes it on the next success.',
    'tooling-watch.yml': 'Checks the pinned build tools for new versions, pre-releases included.',
    'onboard-review.yml': 'Agent review of every new app, provider or patch name.',
    'status.yml': 'Writes the data for this page.',
    'council.yml': 'Agent council: scheduled audits posted on the council desk issue.',
    'keepalive.yml': 'Keeps scheduled automations from being paused by GitHub.',
}
STEP = {
    'Set up job': 'GitHub starting the job',
    'Checkout': 'getting the repository files',
    'Preflight before secrets and downloads': 'checking the app settings',
    'Refuse an unknown app id': 'checking the app id',
    'Preparing to patch': 'setting up Java, proxies and download helpers',
    'Check github connection': 'checking GitHub can be reached',
    'Fail if no connection': 'GitHub could not be reached',
    'Patch apk': 'downloading the original app and applying the patches',
    'Verify finished APK identity': 'checking the finished APK is the right app, signed correctly',
    'Verify release handoff (no publishing)': 'checking the release details',
    'Releasing APK files': 'publishing the release',
    'Decode keystore': 'loading the signing key',
}
WORDS = {
    'success': 'Worked', 'failure': 'Failed', 'cancelled': 'Stopped (cancelled)', 'timed_out': 'Ran out of time',
    'skipped': 'Skipped (nothing to do)', 'action_required': 'Waiting for approval', 'neutral': 'Finished (no result)',
    'startup_failure': 'Could not start (workflow file problem)', 'stale': 'Expired', None: 'Unknown',
}
LIVE = {'in_progress': 'Running now', 'queued': 'Waiting to start', 'waiting': 'Waiting for approval',
        'requested': 'Waiting to start', 'pending': 'Waiting to start'}
BAD = {'failure', 'timed_out', 'startup_failure', 'action_required', 'cancelled'}
# A failure stays listed until a later run of the same workflow or app works (owner, 8 Oct 2026).
# Age is shown, never used to hide it. STALE_DAYS only words the label.
STALE_DAYS = 14


def clean(value, cap=300):
    if not isinstance(value, str):
        return ''
    value = TOKEN.sub('[redacted]', value)
    # W4 (8 Oct 2026): the class began with a bare '-', so every hyphen became a space
    # ("manual patch.yml", "arm64 v8a"). Control and bidi characters only.
    value = re.sub(r'[\x00-\x08\x0b-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]', ' ', value)
    value = ' '.join(value.split())
    return value[:cap - 1] + '…' if len(value) > cap else value


def link(url, kind='repo'):
    if not isinstance(url, str):
        return None
    m = re.fullmatch(r'https://github\.com/([^/?#]+/[^/?#]+)(/[^?#]*)?', url)
    if not m or m[1] != REPO:
        return None
    if kind == 'download' and not (m[2] or '').startswith('/releases/download/'):
        return None
    return url


def plain_reason(text):
    """A few known error lines rewritten for people; anything else is shown as printed."""
    m = re.search(r'needs SDK (\d+), device is (\d+)', text)
    if m:
        return ('The newest app version needs Android %s (API %s); the phone cap here is Android %s (API %s). '
                'Fix: set max_app_version for this app in src/targets.json.' % (
                    ANDROID.get(int(m[1]), '?'), m[1], ANDROID.get(int(m[2]), '?'), m[2]))
    if 'rate-limited' in text or 'rate limit' in text.lower():
        return 'GitHub limited how often this could read; it retries on the next run. (' + text + ')'
    return text


class Reader:
    """GET-only GitHub API reader. Failures are recorded, not raised."""

    def __init__(self, token, fetch=None):
        self.token, self.problems, self.calls = token, [], 0
        self.fetch = fetch or self._http

    def _http(self, path):
        req = urllib.request.Request('https://api.github.com/' + path, headers={
            'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
            'User-Agent': 'pf-status', **({'Authorization': 'Bearer ' + self.token} if self.token else {})})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read(16 * 1024 * 1024).decode('utf-8'))

    def get(self, path, what):
        self.calls += 1
        if self.calls > 400:
            self.problems.append('Stopped reading at 400 requests; ' + what + ' is unknown.')
            return None
        try:
            return self.fetch(path)
        except urllib.error.HTTPError as e:
            self.problems.append('Could not read %s (HTTP %s).' % (what, e.code))
        except Exception as e:  # network, JSON, timeout: unknown, never fine
            self.problems.append('Could not read %s (%s).' % (what, clean(type(e).__name__, 60)))
        return None


def when(run):
    return run.get('updated_at') or run.get('run_started_at') or run.get('created_at')


def result_of(obj):
    status = obj.get('status')
    if status != 'completed':
        return status or 'unknown', LIVE.get(status, 'Unknown state')
    c = obj.get('conclusion')
    return c or 'unknown', WORDS.get(c, clean(str(c), 40))


def failed_step(job):
    for s in job.get('steps') or []:
        if s.get('conclusion') in BAD:
            name = clean(s.get('name'), 120)
            return name, STEP.get(name, name)
    return None, None


def reasons(reader, job_id, cap=3):
    rows = reader.get('repos/%s/check-runs/%s/annotations?per_page=50' % (REPO, job_id), 'the error lines of job %s' % job_id)
    out = []
    for a in rows or []:
        if a.get('annotation_level') not in ('failure', 'warning'):
            continue
        msg = clean(a.get('message'), 400)
        if not msg or NOISE.match(msg) or msg in out:
            continue
        out.append(plain_reason(msg))
        if len(out) >= cap:
            break
    return out


def runs_of(reader, wf, n):
    data = reader.get('repos/%s/actions/workflows/%s/runs?per_page=%d' % (REPO, wf['id'], n), 'recent runs of ' + wf['name'])
    rows = []
    for r in (data or {}).get('workflow_runs') or []:
        if r.get('event') in ('pull_request', 'pull_request_target'):
            continue
        if not isinstance(r.get('id'), int) or not isinstance(r.get('run_attempt'), int):
            continue
        rows.append(r)
    return rows


def jobs_of(reader, run):
    data = reader.get('repos/%s/actions/runs/%d/attempts/%d/jobs?per_page=100' % (REPO, run['id'], run['run_attempt']),
                      'the jobs of run %d' % run['id'])
    return (data or {}).get('jobs') or []


def age_days(stamp, now):
    try:
        a = datetime.datetime.fromisoformat(str(stamp).replace('Z', '+00:00'))
        b = datetime.datetime.fromisoformat(str(now).replace('Z', '+00:00'))
    except ValueError:
        return None
    return max(0, (b - a).days)


def mark_age(row, now):
    """Adds age_days and old (a failure older than STALE_DAYS, still unresolved) to a row."""
    if not row:
        return row
    row['age_days'] = age_days(row.get('when'), now)
    row['old'] = bool(row.get('result') in BAD and row['age_days'] is not None and row['age_days'] > STALE_DAYS)
    return row


def changed_since(reader, path, stamp):
    """True when the workflow file was changed on main after the failed run: a fix may be in,
    and one run confirms it. Unknown (read failed) is None, shown as unknown."""
    data = reader.get('repos/%s/commits?path=%s&since=%s&per_page=1' % (REPO, path, stamp), 'changes to ' + path)
    if data is None:
        return None
    return bool(data)


def run_row(run):
    code, words = result_of(run)
    return {'when': when(run), 'result': code, 'words': words, 'event': clean(run.get('event'), 30),
            'url': link(run.get('html_url'))}


def android(api):
    if not isinstance(api, int):
        return None
    return {'api': api, 'version': ANDROID.get(api, 'API %d' % api)}


def releases(reader, prefixes):
    latest = {}
    for page in range(1, 6):
        data = reader.get('repos/%s/releases?per_page=100&page=%d' % (REPO, page), 'the release list')
        if data is None:
            return latest, False
        for r in data:
            if r.get('draft'):
                continue
            m = TAG_RX.match(r.get('tag_name') or '')
            if not m or m[1] not in prefixes:
                continue
            have = latest.get(m[1])
            if have and (have['published_at'] or '') >= (r.get('published_at') or ''):
                continue
            apks = [a for a in r.get('assets') or [] if str(a.get('name', '')).endswith('.apk')]
            row = {'tag': m[0], 'version': m[2], 'published_at': r.get('published_at'), 'url': link(r.get('html_url')),
                   'apk': None, 'min_android': None, 'native': None}
            if len(apks) == 1:
                row['apk'] = {'name': clean(apks[0].get('name'), 120), 'bytes': apks[0].get('size'),
                              'url': link(apks[0].get('browser_download_url'), 'download')}
            hit = MARKER.findall(r.get('body') or '')
            if len(hit) == 1:
                try:
                    doc = json.loads(base64.b64decode(hit[0], validate=True))
                    row['min_android'] = android(doc.get('min_sdk'))
                    row['native'] = clean(doc.get('arch'), 40) or None
                except (ValueError, TypeError):
                    pass
            latest[m[1]] = row
        if len(data) < 100:
            return latest, True
    reader.problems.append('More than 500 releases; older apps may show no release.')
    return latest, False


def build(reader, targets, now=None):
    now = now or datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    out = {'schema': 1, 'generated_at': now, 'repo': REPO, 'apps': [], 'workflows': [], 'issues': [], 'problems': reader.problems}
    wfs = (reader.get('repos/%s/actions/workflows?per_page=100' % REPO, 'the workflow list') or {}).get('workflows') or []
    build_jobs = {}
    for wf in sorted(wfs, key=lambda w: str(w.get('name'))):
        if wf.get('state') != 'active' or not isinstance(wf.get('id'), int):
            continue
        path = str(wf.get('path') or '')
        file = path.rsplit('/', 1)[-1]
        runs = runs_of(reader, wf, 10 if path in BUILD_FILES else 5)
        row = {'file': clean(file, 80), 'name': clean(wf.get('name'), 80), 'purpose': PURPOSE.get(file, ''),
               'url': link(WEB + '/actions/workflows/' + file), 'recent': [run_row(r) for r in runs[:5]], 'last': None}
        done = [r for r in runs if r.get('status') == 'completed']
        if done:
            last = run_row(done[0])
            if done[0].get('conclusion') in BAD:
                last['jobs'] = []
                for j in jobs_of(reader, done[0]):
                    if j.get('conclusion') not in BAD:
                        continue
                    step, plain = failed_step(j)
                    last['jobs'].append({'name': clean(j.get('name'), 120), 'step': step, 'step_plain': plain,
                                         'why': reasons(reader, j['id']) if isinstance(j.get('id'), int) else [],
                                         'url': link(j.get('html_url'))})
                    if len(last['jobs']) >= 4:
                        break
            row['last'] = mark_age(last, now)
            if done[0].get('conclusion') in BAD and last.get('when'):
                last['changed_since'] = changed_since(reader, path, last['when'])
        out['workflows'].append(row)
        if path in BUILD_FILES:
            for r in runs:
                for j in jobs_of(reader, r):
                    m = JOB_RX.search(str(j.get('name') or ''))
                    if not m:
                        continue
                    build_jobs.setdefault(m[1], []).append((j, r, file))
    enabled = [t for t in targets if t.get('enabled')]
    prefixes = {(t.get('tag_prefix') or t['id']): t['id'] for t in enabled}
    latest, complete = releases(reader, prefixes)
    for t in sorted(enabled, key=lambda x: (x.get('label') or x['id']).lower()):
        tid = t['id']
        jobs = sorted(build_jobs.get(tid, []), key=lambda x: str(x[0].get('completed_at') or x[0].get('started_at') or ''), reverse=True)
        real = [x for x in jobs if x[0].get('conclusion') != 'skipped']
        app = {'id': tid, 'label': clean(t.get('label') or tid, 60), 'needs_microg': bool(t.get('needs_microg')),
               'cpu': 'ARM64', 'android_cap': android(t.get('min_sdk_ceiling')),
               'release': latest.get(t.get('tag_prefix') or tid), 'release_known': complete or bool(latest.get(t.get('tag_prefix') or tid)),
               'last_build': None, 'last_check': None}
        if jobs:
            j, r, file = jobs[0]
            app['last_check'] = {'when': j.get('completed_at') or j.get('started_at') or when(r), 'words': result_of(j)[1],
                                 'workflow': clean(r.get('name'), 80), 'url': link(j.get('html_url')) or link(r.get('html_url'))}
        if real:
            j, r, file = real[0]
            code, words = result_of(j)
            lb = {'when': j.get('completed_at') or j.get('started_at') or when(r), 'result': code, 'words': words,
                  'workflow': clean(r.get('name'), 80), 'url': link(j.get('html_url')) or link(r.get('html_url'))}
            if code in BAD:
                lb['step'], lb['step_plain'] = failed_step(j)
                lb['why'] = reasons(reader, j['id']) if isinstance(j.get('id'), int) else []
            app['last_build'] = mark_age(lb, now)
        out['apps'].append(app)
    iss = reader.get('repos/%s/issues?state=open&per_page=100' % REPO, 'open issues')
    for i in iss or []:
        title = clean(i.get('title'), 160)
        if i.get('pull_request') or not title.startswith('Failing: '):
            continue
        out['issues'].append({'title': title, 'url': link(i.get('html_url')), 'number': i.get('number')})
    bad_apps = [a['label'] for a in out['apps'] if a['last_build'] and a['last_build']['result'] in BAD]
    bad_wfs = [w['name'] for w in out['workflows'] if w['last'] and w['last']['result'] in BAD]
    confirm = [w['name'] for w in out['workflows'] if w['last'] and w['last'].get('changed_since')]
    if out['problems']:
        head = 'Partly unknown: some GitHub reads failed (listed at the bottom).'
    elif bad_apps or bad_wfs:
        head = '%d app build(s) and %d automation(s) need a look.' % (len(bad_apps), len(bad_wfs))
    else:
        head = 'Everything that ran recently worked.'
    out['headline'] = {'text': head, 'apps': bad_apps, 'workflows': bad_wfs, 'run_once_to_confirm': confirm}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n', 1)[0])
    ap.add_argument('--out', default='status.json')
    ap.add_argument('--targets', default='src/targets.json')
    a = ap.parse_args(argv)
    targets = json.loads(Path(a.targets).read_text(encoding='utf-8'))
    reader = Reader(os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN'))
    data = build(reader, targets)
    text = json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + '\n'
    if len(text.encode()) > 2000000:
        print('::error::status.json would exceed 2 MB; refusing')
        return 1
    Path(a.out).write_text(text, encoding='utf-8')
    for p in data['problems']:
        print('::warning::status: ' + p)
    print('status: %s (%d apps, %d workflows, %d API reads)' % (data['headline']['text'], len(data['apps']),
                                                                 len(data['workflows']), reader.calls))
    return 0


if __name__ == '__main__':
    sys.exit(main())
