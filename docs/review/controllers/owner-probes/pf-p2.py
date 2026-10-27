#!/usr/bin/env python3
"""pf-p2: read-only probe after W16p (27 Oct 2026). Engineered with Anthropic Claude models (Opus, Sonnet and Haiku; model selection may vary) for the repository owner.
One trip for the handover packet W16t:
  1. this Cloud Shell's W16p controller logs (newest pf-w16p-* and pf-t1-* folders and the nohup
     log), copied, never moved or deleted;
  2. the first live MCP scout run after the merge (40444460398): details, full log, its result
     artifact; the Council probe (40444463398), the W16p pull request review (40440538008) and
     the W16p T1 batch (40441656177, Amazon Music failed at Patch apk, issue #262; only its small
     evidence artifacts, never the test APKs), and prints the store and patch failure lines it finds;
  3. every scheduled run of the last 60 (the 27 Oct morning crons started hours late), Nightly and
     Community watch history, and the live status.json from Pages;
  4. a git bundle --all of a fresh clone of main (the next packet's starting point), verified.
It writes nothing to GitHub and never prints a secret. Everything goes into one zip. W16u also
sanitizes a bounded review of open issues/comments, open PRs, and recent failed/cancelled runs."""
import json, os, pathlib, re, shutil, subprocess, sys, time
from datetime import datetime, timezone
REPO = 'govinda-rajulu/patch-factory'
RUNS = {'40444460398': 'mcp-scout', '40444463398': 'council-probe', '40440538008': 'council-pr261',
        '40441656177': 'batch-t1-w16p'}
HISTORY = {'scheduled': 'repos/%s/actions/runs?event=schedule&per_page=60' % REPO,
           'nightly-watch': 'repos/%s/actions/workflows/watch.yml/runs?per_page=10' % REPO,
           'community-watch': 'repos/%s/actions/workflows/community-watch.yml/runs?per_page=10' % REPO,
           'council': 'repos/%s/actions/workflows/council.yml/runs?per_page=10' % REPO}
# status.yml force-pushes status.json to the `status` branch, not to Pages (curl exit 22 on 27 Oct)
PAGES = 'https://raw.githubusercontent.com/govinda-rajulu/patch-factory/status/status.json'
ARTIFACT_MAX = 5 * 1024 * 1024  # W16q round 3: evidence only; a test APK is never pulled into the zip
SKIP_ARTIFACT = ('test-apk-',)
# failure markers only. W16q run (wrong call 90): DOWNLOAD_DIAGNOSTIC is printed on every store
# page, so 12 of them filled the cap and the patcher's own error stayed off the owner's screen.
CLUES = ('TRANSFER_FAILED', 'STORE_CHAIN', 'DOWNLOAD_FAILURE', 'ATTEMPTS_FAILED', 'PATCH_FAILED',
         'Patching aborted', 'ERROR: FAILED', 'refusing to release', 'stderr was not valid JSON',
         'Error when talking to Gemini', 'TerminalQuotaError', 'status 429', 'status 503', 'denied by policy')
COPY_MAX = 200 * 1024 * 1024  # W16q: a local log folder above this is named, not copied
STAMP = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + ('-%d' % os.getpid())
HOME = pathlib.Path(os.environ.get('PF_HOME', str(pathlib.Path.home())))
OUT = HOME / 'work' / 'run-logs' / ('pf-p2-' + STAMP)
lines, bad = [], [0]
DOWNLOADED = [0]
OUTPUT_MAX = 200 * 1024 * 1024


def say(status, text):
    line = '%s %s' % (status, text)
    print(line, flush=True)
    lines.append(line)
    if status == 'FAIL':
        bad[0] += 1


def gh(args, dest=None, timeout=900):
    try:
        r = subprocess.run(['gh'] + args, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, b''
    if dest is not None:
        dest.write_bytes(r.stdout)
        if r.returncode != 0:
            (dest.parent / (dest.name + '.err')).write_bytes(r.stderr)
    return r.returncode, r.stdout


def run_details(run, name):
    code, out = gh(['run', 'view', run, '-R', REPO, '--json',
                    'name,displayTitle,event,status,conclusion,createdAt,startedAt,updatedAt,headSha,url,jobs'],
                   OUT / ('%s-%s.json' % (name, run)))
    say('OK' if code == 0 else 'FAIL', '%s run %s details (%d bytes)' % (name, run, len(out)))


def run_log(run, name):
    code, out = gh(['run', 'view', run, '-R', REPO, '--log'], OUT / ('%s-%s.log' % (name, run)))
    if code != 0 or not out:
        code, out = gh(['run', 'view', run, '-R', REPO, '--log-failed'], OUT / ('%s-%s.failed.log' % (name, run)))
    say('OK' if code == 0 and out else 'FAIL', '%s run %s log (%d bytes)' % (name, run, len(out)))
    clues(name, out)


def clues(name, out, limit=12):
    """Print the few log lines that name a cause, so the owner's screen already answers why."""
    more = 0
    for l in (out or b'').decode('utf-8', 'replace').splitlines():
        if any(c in l for c in CLUES):
            if limit:
                clue = TOKENISH.sub('[REDACTED]', l.strip()[-300:]) if 'TOKENISH' in globals() else l.strip()[-300:]
                say('CLUE', '%s: %s' % (name, clue))
                limit -= 1
            else:
                more += 1
    if more:
        say('CLUE', '%s: %d more in the log' % (name, more))


def artifacts(run, name):
    code, out = gh(['api', 'repos/%s/actions/runs/%s/artifacts?per_page=100' % (REPO, run)], OUT / ('%s-%s.artifacts.json' % (name, run)))
    if code != 0:
        say('FAIL', '%s run %s artifact list' % (name, run))
        return
    data = loads(out, None)
    if not (isinstance(data, dict) and isinstance(data.get('artifacts'), list)):
        say('FAIL', '%s run %s artifact list unreadable' % (name, run))
        return
    rows = data['artifacts']
    for a in rows:
        if str(a.get('name', '')).startswith(SKIP_ARTIFACT):
            continue
        if a.get('expired'):
            say('NOTE', '%s artifact %s expired' % (name, a.get('name')))
            continue
        if a.get('size_in_bytes', 0) > ARTIFACT_MAX:
            say('NOTE', '%s artifact %s is %d bytes, not downloaded' % (name, a.get('name'), a.get('size_in_bytes', 0)))
            continue
        safe = pathlib.Path(str(a.get('name') or ''))
        if safe.name != str(safe) or str(safe) in ('', '.', '..') or not re.fullmatch(r'[A-Za-z0-9._-]{1,160}', str(safe)):
            say('FAIL', '%s artifact name is unsafe: %r' % (name, a.get('name')))
            continue
        size = int(a.get('size_in_bytes') or 0)
        if DOWNLOADED[0] + size > OUTPUT_MAX:
            say('NOTE', '%s artifact %s would exceed the %d MB probe budget; not downloaded' % (name, safe, OUTPUT_MAX // 2**20))
            continue
        dest = OUT / ('%s-%s-artifacts' % (name, run))
        dest.mkdir(exist_ok=True)
        code, _ = gh(['run', 'download', run, '-R', REPO, '-n', str(safe), '-D', str(dest / str(safe))])
        if code == 0:
            DOWNLOADED[0] += size
        say('OK' if code == 0 else 'FAIL', '%s artifact %s (%d bytes)' % (name, safe, size))
    if not rows:
        say('NOTE', '%s run %s has no artifacts' % (name, run))


MAX_TEXT = 800
CASE_WINDOW = '2026-10-20T00:00:00Z'
TOKENISH = re.compile(r'(?i)(ghp_[A-Za-z0-9_\-]+|github_pat_[A-Za-z0-9_\-]+|bearer\s+[A-Za-z0-9._\-]+|(?:token|secret|api[_-]?key)\s*[:=]\s*[^\s,;]+)')


def clean_text(value, limit=MAX_TEXT):
    text = re.sub(r'[\x00-\x1f\x7f\u202a-\u202e\u2066-\u2069]', ' ', str(value or ''))
    text = TOKENISH.sub('[REDACTED]', text)
    return text[:limit]


def api_json(path, timeout=120):
    code, out = gh(['api', path, '-H', 'Accept: application/vnd.github+json',
                    '-H', 'X-GitHub-Api-Version: 2022-11-28'], timeout=timeout)
    return code, loads(out, None)


def pages(path, limit=100):
    rows, page = [], 1
    while page <= 10:
        url = '%s&per_page=%d&page=%d' % (path, limit, page) if '?' in path else '%s?per_page=%d&page=%d' % (path, limit, page)
        code, data = api_json(url)
        if code != 0 or not isinstance(data, list):
            return code, rows, False
        rows.extend(data)
        if len(data) < limit:
            return 0, rows, True
        page += 1
    return 0, rows, False


def person(row):
    u = row.get('user') or {}
    return {'login': clean_text(u.get('login'), 120), 'type': clean_text(u.get('type'), 40)}


def project_issue(row):
    return {'number': row.get('number'), 'title': clean_text(row.get('title'), 300),
            'body': clean_text(row.get('body')), 'state': row.get('state'),
            'updated_at': row.get('updated_at'), 'created_at': row.get('created_at'),
            'comments_count': row.get('comments', 0), 'labels': [clean_text(x.get('name'), 100) for x in row.get('labels', [])],
            'author': person(row), 'html_url': row.get('html_url')}


def project_comment(row):
    return {'id': row.get('id'), 'body': clean_text(row.get('body')), 'created_at': row.get('created_at'),
            'updated_at': row.get('updated_at'), 'author': person(row), 'html_url': row.get('html_url')}


def project_pr(row):
    base, head = row.get('base') or {}, row.get('head') or {}
    return {'number': row.get('number'), 'title': clean_text(row.get('title'), 300), 'body': clean_text(row.get('body')),
            'state': row.get('state'), 'draft': row.get('draft'), 'updated_at': row.get('updated_at'),
            'base': {'ref': clean_text(base.get('ref'), 100), 'sha': base.get('sha')},
            'head': {'ref': clean_text(head.get('ref'), 100), 'sha': head.get('sha')},
            'author': person(row), 'html_url': row.get('html_url')}


def project_run(row):
    return {'id': row.get('id'), 'run_number': row.get('run_number'), 'run_attempt': row.get('run_attempt'),
            'name': clean_text(row.get('name'), 300), 'path': row.get('path'), 'event': row.get('event'),
            'status': row.get('status'), 'conclusion': row.get('conclusion'), 'head_branch': clean_text(row.get('head_branch'), 160),
            'head_sha': row.get('head_sha'), 'created_at': row.get('created_at'), 'updated_at': row.get('updated_at'),
            'html_url': row.get('html_url')}


def case_review():
    """Bounded, sanitized owner handover: cases, conversations, PRs, and recent bad runs."""
    result = {'schema': 1, 'generated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), 'repo': REPO,
              'coverage': {'errors': [], 'window_from': CASE_WINDOW}, 'issues': [], 'pull_requests': [],
              'recent_runs': [], 'counts': {}}
    code, rows = api_json('repos/%s/issues?state=open&sort=updated&direction=desc&per_page=100&page=1' % REPO)
    if code == 0 and isinstance(rows, list):
        for row in rows:
            if 'pull_request' not in row:
                item = project_issue(row)
                cc, comments, complete = pages('repos/%s/issues/%s/comments' % (REPO, row.get('number')))
                item['comments'] = [project_comment(x) for x in comments] if cc == 0 and isinstance(comments, list) else []
                item['comments_complete'] = cc == 0 and complete
                if not item['comments_complete']:
                    result['coverage']['errors'].append('issue comments incomplete #%s' % row.get('number'))
                result['issues'].append(item)
    else:
        result['coverage']['errors'].append('open issues unreadable')
    code, rows, complete = pages('repos/%s/pulls?state=open&sort=updated&direction=desc' % REPO)
    if code == 0 and isinstance(rows, list):
        for row in rows:
            item = project_pr(row)
            cc, comments, comments_complete = pages('repos/%s/issues/%s/comments' % (REPO, row.get('number')))
            item['comments'] = [project_comment(x) for x in comments] if cc == 0 and isinstance(comments, list) else []
            item['comments_complete'] = cc == 0 and comments_complete
            if not item['comments_complete']:
                result['coverage']['errors'].append('PR comments incomplete #%s' % row.get('number'))
            result['pull_requests'].append(item)
        if not complete:
            result['coverage']['errors'].append('open PR collection capped')
    else:
        result['coverage']['errors'].append('open PRs unreadable')
    code, rows = api_json('repos/%s/actions/runs?created=>=%s&per_page=100&page=1' % (REPO, CASE_WINDOW))
    if code == 0 and isinstance(rows, dict):
        for row in rows.get('workflow_runs', []):
            if row.get('conclusion') in ('failure', 'cancelled', 'timed_out', 'action_required'):
                item = project_run(row)
                jc, jobs = api_json('repos/%s/actions/runs/%s/attempts/%s/jobs?per_page=100&page=1' % (REPO, row.get('id'), row.get('run_attempt') or 1))
                if jc == 0 and isinstance(jobs, dict):
                    item['bad_jobs'] = [{'id': j.get('id'), 'name': clean_text(j.get('name'), 240), 'conclusion': j.get('conclusion'),
                                         'failed_steps': [clean_text(x.get('name'), 160) for x in j.get('steps', []) if x.get('conclusion') in ('failure', 'cancelled', 'timed_out')]} for j in jobs.get('jobs', []) if j.get('conclusion') in ('failure', 'cancelled', 'timed_out')]
                result['recent_runs'].append(item)
    else:
        result['coverage']['errors'].append('recent runs unreadable')
    result['counts'] = {'open_issues': len(result['issues']), 'open_prs': len(result['pull_requests']),
                        'issue_comments': sum(len(x['comments']) for x in result['issues']),
                        'pr_comments': sum(len(x['comments']) for x in result['pull_requests']),
                        'recent_bad_runs': len(result['recent_runs'])}
    dest = OUT / 'case-review.json'
    dest.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    if result['coverage']['errors']:
        say('NOTE', 'case review partial: ' + ', '.join(result['coverage']['errors']))
    say('OK', 'CASE REVIEW: issues=%d; prs=%d; comments=%d; recent_bad_runs=%d; file=%d bytes' %
        (result['counts']['open_issues'], result['counts']['open_prs'], result['counts']['issue_comments'] + result['counts']['pr_comments'],
         result['counts']['recent_bad_runs'], dest.stat().st_size))


def git_bundle():
    url = os.environ.get('PF_REMOTE', 'https://github.com/%s.git' % REPO)
    tmp = OUT / 'clone'
    dest = OUT / ('pf-main-%s.bundle' % STAMP)
    steps = (['git', 'clone', '-q', '--no-checkout', url, str(tmp)],
             ['git', '-C', str(tmp), 'bundle', 'create', str(dest), '--all'],
             ['git', '-C', str(tmp), 'bundle', 'verify', str(dest)])
    for cmd in steps:
        r = subprocess.run(cmd, capture_output=True, timeout=900)
        if r.returncode != 0:
            say('FAIL', 'bundle step %s: %s' % (cmd[4] if cmd[1] == '-C' else 'clone', r.stderr.decode('utf-8', 'replace').strip()[-200:]))
            shutil.rmtree(tmp, ignore_errors=True)
            return
    head = subprocess.run(['git', '-C', str(tmp), 'rev-parse', 'refs/remotes/origin/main'], capture_output=True, text=True).stdout.strip()
    listed = subprocess.run(['git', 'bundle', 'list-heads', str(dest)], capture_output=True, text=True).stdout
    shutil.rmtree(tmp, ignore_errors=True)
    if not re.fullmatch('[0-9a-f]{40}', head) or (head + ' refs/remotes/origin/main') not in listed:
        say('FAIL', 'bundle %s has no main ref (%r)' % (dest.name, head[:40]))
        return
    say('OK', 'bundle %s: main %s, %d bytes, verified' % (dest.name, head, dest.stat().st_size))


def local_logs():
    """Copy (never move) the newest W16p and T1 log folders and the nohup log of this Cloud Shell."""
    logs = HOME / 'work' / 'run-logs'
    dest = OUT / 'local'
    dest.mkdir(exist_ok=True)
    for prefix in ('pf-w16p-', 'pf-t1-'):
        rows = sorted(p for p in logs.glob(prefix + '*') if p.is_dir() and not p.is_symlink()
                      and re.fullmatch(r'\d{8}T\d{6}Z', p.name[len(prefix):]))
        if not rows:
            say('NOTE', 'no %s* folder in %s' % (prefix, logs))
            continue
        if any(x.is_symlink() for x in rows[-1].rglob('*')):
            say('FAIL', '%s contains symlinks; not copied' % rows[-1].name)
            continue
        files = [x for x in rows[-1].rglob('*') if x.is_file()]
        size = sum(x.stat().st_size for x in files)
        # W16q review: never double a big folder on a small disk; the owner can zip it himself.
        if size > COPY_MAX or size > shutil.disk_usage(str(HOME)).free // 4:
            say('NOTE', '%s is %d MB, not copied (zip it yourself if needed)' % (rows[-1].name, size // 2**20))
            continue
        shutil.copytree(str(rows[-1]), str(dest / rows[-1].name), symlinks=False)
        say('OK', 'copied %s (%d files, %d bytes)' % (rows[-1].name, len(files), size))
    nohup = logs / 'pf-w16p-nohup.log'
    if nohup.is_file() and not nohup.is_symlink():
        shutil.copy2(str(nohup), str(dest / nohup.name))
        say('OK', 'copied %s (%d bytes)' % (nohup.name, nohup.stat().st_size))
    else:
        say('NOTE', 'no pf-w16p-nohup.log')


def status_json():
    """The live status page data (public). A miss is a NOTE: Pages may be mid-deploy."""
    dest = OUT / 'status.json'
    try:
        r = subprocess.run(['curl', '-fsS', '--proto', '=https', '--max-time', '60', '-o', str(dest), PAGES],
                           capture_output=True, timeout=90)
        code = r.returncode
    except subprocess.TimeoutExpired:
        code = 124
    if code == 0 and dest.is_file():
        say('OK', 'status.json from Pages (%d bytes)' % dest.stat().st_size)
    else:
        say('NOTE', 'status.json not read (curl exit %s)' % code)


def loads(data, default):
    try:
        return json.loads(data or b'null') or default
    except ValueError:
        return default


def seconds(r):
    try:
        a = datetime.strptime(r.get('run_started_at') or r['created_at'], '%Y-%m-%dT%H:%M:%SZ')
        b = datetime.strptime(r['updated_at'], '%Y-%m-%dT%H:%M:%SZ')
        return int((b - a).total_seconds())
    except (KeyError, TypeError, ValueError):
        return -1


def main():
    free = shutil.disk_usage(str(HOME)).free
    if free < 500 * 1024 * 1024:
        print('RESULT STOP: only %d MB free in your home folder; free 500 MB, then run the same command again. Script kept.' % (free // 2**20))
        return 1
    try:
        OUT.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print('RESULT STOP: probe output already exists; nothing ran. Script kept.')
        return 1
    try:
        return reads()
    except Exception as e:  # keep whatever was read: zip it and stop
        say('FAIL', 'probe error %s: %s' % (type(e).__name__, str(e)[:200]))
        return finish()


def reads():
    code, _ = gh(['auth', 'status'])
    if code != 0:
        say('STOP', 'gh is not logged in; nothing read')
        print('RESULT STOP: run gh auth login, then the same command again. Script kept.')
        return 1
    say('OK', 'gh logged in; folder ' + str(OUT))
    git_bundle()  # first, so a later failure still leaves the next packet's starting point
    local_logs()
    for run, name in RUNS.items():
        run_details(run, name)
        run_log(run, name)
        artifacts(run, name)
    for name, path in HISTORY.items():
        code, out = gh(['api', path], OUT / ('history-%s.json' % name))
        data = loads(out, None) if code == 0 else None
        ok = isinstance(data, dict) and isinstance(data.get('workflow_runs'), list)
        say('OK' if ok else 'FAIL', 'history %s (%d bytes%s)' % (name, len(out), '' if ok else ', unreadable'))
    status_json()
    case_review()
    return finish()


def finish():
    (OUT / 'P2-RESULT.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    try:
        z = shutil.make_archive(str(OUT), 'zip', root_dir=str(OUT.parent), base_dir=OUT.name)
        size = pathlib.Path(z).stat().st_size
    except OSError as e:
        print('RESULT STOP: zip failed (%s); the folder %s keeps everything read. Script kept.' % (e, OUT))
        return 1
    if bad[0]:
        print('RESULT STOP: %d read(s) failed; upload %s (%d bytes) anyway. Script kept.' % (bad[0], z, size))
        return 1
    me = pathlib.Path(__file__).resolve()
    if me.parent == HOME and me.name.startswith('pf-p2-'):
        me.unlink()
    print('RESULT OK. Upload %s (%d bytes). Script removed.' % (z, size))
    return 0


if __name__ == '__main__':
    sys.exit(main())
