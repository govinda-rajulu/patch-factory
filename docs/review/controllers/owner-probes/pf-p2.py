#!/usr/bin/env python3
"""pf-p2: read-only owner probe for W16v (27 Oct 2026). Engineered with Anthropic Claude models (Opus, Sonnet and Haiku; model selection may vary) for the repository owner.
One trip for the W16v handover packet:
  1. this Cloud Shell's retained W16p controller logs (newest pf-w16p-* and pf-t1-* folders and
     the nohup log), copied, never moved or deleted;
  2. the fixed live MCP scout run (40444460398): details, full log, its result artifact; the
     Council probe (40444463398), the W16p pull request review (40440538008) and the W16p T1
     batch (40441656177, Amazon Music failed at Patch apk, issue #262; only its small evidence
     artifacts, never the test APKs), and prints the store and patch failure lines it finds;
  3. every scheduled run of the last 60 (the 27 Oct morning crons started hours late), Nightly and
     Community watch history, and the live status.json from Pages;
  4. a git bundle --all of a fresh clone of main (the next packet's starting point), verified.
It writes nothing to GitHub and never prints a secret. Everything goes into one zip. W16v also
sanitizes a bounded review of open issues/comments, open PRs, and recent failed/cancelled runs."""
import hashlib, json, os, pathlib, re, shutil, struct, subprocess, sys, time
from datetime import datetime, timezone
REPO = 'govinda-rajulu/patch-factory'
# W16w (owner, 28 Oct 2026: the same old CLUE lines on every run read as new failures): the four
# fixed 26 to 27 Oct runs are already in the repo records, so the probe no longer re-reads them.
RUNS = {}
# W16w: all 9 icons are in the repository since W16v; the icon check runs only when asked.
ICONS = os.environ.get('PF_P2_ICONS') == '1'
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
CLUES = ('TRANSFER_FAILED', 'STORE_CHAIN', 'STORE_DOWNGRADE_REFUSED', 'DOWNLOAD_FAILURE', 'ATTEMPTS_FAILED', 'PATCH_FAILED',
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
                # W16v review: redact the whole line first, then shorten it (a cut can hide the key name).
                clue = TOKENISH.sub('[REDACTED]', l.strip())
                at = min([clue.find(c) for c in CLUES if c in clue] or [0])
                clue = clue[at:at + 300] if len(clue) > 300 else clue  # the marker stays on screen
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
# W16v review (27 Oct 2026): every GitHub token prefix, auth headers, key=value secrets,
# credentials inside URLs and private key blocks.
TOKENISH = re.compile(
    r'(?is)(-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)'
    r'|gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+|(?:bearer|basic)\s+[A-Za-z0-9._~+/=\-]+'
    r'|authorization\s*:\s*\S+(?:\s+\S+)?|://[^/\s:@]+:[^/\s@]+@'
    # W16v round 2: bounded key names (no runaway scan on a 2 MB line), spaced aliases, and the
    # workflow words `secrets: inherit` / `tokens: read|write|none` stay readable.
    r'|(?<![A-Za-z0-9_])[A-Za-z0-9_]{0,40}?(?:token|secret|password|passwd|api[ _-]?key|access[ _-]?key|private[ _-]?key|client[ _-]?secret)[A-Za-z0-9_]{0,40}'
    r'\s*[:=]\s*(?!(?:inherit|read|write|none)\b)[^\s,;]+)')


def clean_text(value, limit=MAX_TEXT):
    text = re.sub(r'[\x00-\x1f\x7f\u202a-\u202e\u2066-\u2069]', ' ', str(value or ''))
    text = TOKENISH.sub('[REDACTED]', text)
    return text[:limit]


def api_json(path, timeout=120):
    code, out = gh(['api', path, '-H', 'Accept: application/vnd.github+json',
                    '-H', 'X-GitHub-Api-Version: 2022-11-28'], timeout=timeout)
    return code, loads(out, None)


def pages(path, limit=100, key=None):
    """Read at most ten pages, preserving valid empty JSON collections.

    GitHub returns bare lists for issues, pulls, and comments, but wraps workflow
    runs and jobs in an object.  A collection is complete only after a short
    page; a full tenth page is a truthful cap, not proof that there are no more.
    """
    rows, page = [], 1
    while page <= 10:
        url = '%s&per_page=%d&page=%d' % (path, limit, page) if '?' in path else '%s?per_page=%d&page=%d' % (path, limit, page)
        code, data = api_json(url)
        if code != 0:
            return code, rows, False
        if key is None:
            batch = data if isinstance(data, list) else None
        else:
            batch = data.get(key) if isinstance(data, dict) else None
            if not isinstance(batch, list):
                batch = None
        if batch is None:
            # api_json can have a successful HTTP/gh status but no decoded JSON;
            # that is unreadable, not evidence that the ten-page cap was reached.
            return 1, rows, False
        rows.extend(batch)
        if len(batch) < limit:
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
    code, rows, complete = pages('repos/%s/issues?state=open&sort=updated&direction=desc' % REPO)
    if code == 0 and isinstance(rows, list):
        for row in rows:
            if 'pull_request' not in row:
                item = project_issue(row)
                cc, comments, comments_complete = pages('repos/%s/issues/%s/comments' % (REPO, row.get('number')))
                item['comments'] = [project_comment(x) for x in comments] if cc == 0 and isinstance(comments, list) else []
                item['comments_complete'] = cc == 0 and comments_complete
                if not item['comments_complete']:
                    result['coverage']['errors'].append('issue comments incomplete #%s' % row.get('number'))
                result['issues'].append(item)
        if not complete:
            result['coverage']['errors'].append('open issues collection capped')
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
    code, rows, complete = pages('repos/%s/actions/runs?created=>=%s' % (REPO, CASE_WINDOW), key='workflow_runs')
    if code == 0 and isinstance(rows, list):
        for row in rows:
            if row.get('conclusion') in ('failure', 'cancelled', 'timed_out', 'action_required'):
                item = project_run(row)
                jc, jobs, jobs_complete = pages('repos/%s/actions/runs/%s/attempts/%s/jobs' % (REPO, row.get('id'), row.get('run_attempt') or 1), key='jobs')
                if jc == 0 and isinstance(jobs, list):
                    item['bad_jobs'] = [{'id': j.get('id'), 'name': clean_text(j.get('name'), 240), 'conclusion': j.get('conclusion'),
                                         'failed_steps': [clean_text(x.get('name'), 160) for x in j.get('steps', []) if x.get('conclusion') in ('failure', 'cancelled', 'timed_out')]} for j in jobs if j.get('conclusion') in ('failure', 'cancelled', 'timed_out')]
                    if not jobs_complete:
                        result['coverage']['errors'].append('run jobs collection capped #%s' % row.get('id'))
                else:
                    result['coverage']['errors'].append('run jobs unreadable #%s' % row.get('id'))
                result['recent_runs'].append(item)
        if not complete:
            result['coverage']['errors'].append('recent runs collection capped')
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
    """Copy (never move) the newest packet and T1 log folders and the two newest nohup logs of this Cloud Shell.
    W16v round 3: the old W16p-only names and the seconds-only stamp missed every later packet folder
    (pf-w16u-20261027T111847693701Z-4573)."""
    logs = HOME / 'work' / 'run-logs'
    dest = OUT / 'local'
    dest.mkdir(exist_ok=True)
    stamp = r'-\d{8}T\d{6,12}Z(-\d+)?'
    # Any packet name (w16u, h12), never this probe's own output (pf-p2-) or T1, which has its own row.
    for prefix, pat in (('pf-', r'pf-(?!t1-|p2-)[a-z][a-z0-9]*' + stamp), ('pf-t1-', r'pf-t1' + stamp)):
        rows = sorted((p for p in logs.glob(prefix + '*') if p.is_dir() and not p.is_symlink()
                       and re.fullmatch(pat, p.name)), key=lambda p: p.stat().st_mtime)
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
    nohups = sorted((p for p in logs.glob('pf-*-nohup*.log') if p.is_file() and not p.is_symlink()
                     and p.stat().st_size <= COPY_MAX), key=lambda p: p.stat().st_mtime)[-2:]
    for nohup in nohups:
        if nohup.stat().st_size > shutil.disk_usage(str(HOME)).free // 4:
            say('NOTE', '%s not copied: low disk' % nohup.name)
            continue
        shutil.copy2(str(nohup), str(dest / nohup.name))
        say('OK', 'copied %s (%d bytes)' % (nohup.name, nohup.stat().st_size))
    if not nohups:
        say('NOTE', 'no pf-*-nohup*.log in %s' % logs)


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


ICON_SOURCES = (
    ('amazonmusic', 'https://play-lh.googleusercontent.com/9v2z1-7g8pWbxek8IW3Q9gGsAqD-YkTvy_rmyd4Cfb-OkpVR2T6jt-Ev2eKDcvx72njhCQ_4fEd9qg8-T9AaDA'),
    ('hotstar', 'https://play-lh.googleusercontent.com/02xiO0ptbXjD8NR3sbS2StP1P9aytDN56dDR15zqM_i66Vwq5W_hD-98CoFxvRVoUS4uV_xMSv-iQh3nQFeDeQ'),
    ('mxplayer', 'https://play-lh.googleusercontent.com/pL-FlnQwdyKetEhT_Uzre61MnGKhMgLC7wnV12KgC_wrQbU0UbSkYs4T5fQQWL_QLZZ48fl1mBmN-cNbc1wSZA'),
    ('linkedin', 'https://play-lh.googleusercontent.com/oij55bxj3e-4JrhGntpki0lnQyE8yQn8X5FPEzZ0t7cLppeiSINynEk7n9COoh7QSaCOZ_yiPO31NVaW4SDbWg'),
    ('reddit', 'https://play-lh.googleusercontent.com/8FVS0kvM60JwqZWRNzBIlwrZZxJa8vpli8IWaaTo8QXRe1PHmCNJ8UpWoXkGPV3jKEaTY2OVAeYoisOnGJXY'),
    ('ccleaner', 'https://play-lh.googleusercontent.com/4TzP6UEY4IJCNntREn5fm1eojCC1MeBvR5B2Hl2-IICBAtU8HT5HrM1wcruwtLbVCQbfezTbonVbv-pgf8-UUg'),
    ('esfile', 'https://img.utdstc.com/icon/826/725/82672572ac96972a9e4e56717258c0651d296e707ae49309ce6bf81630ce3159'),
    ('edge', 'https://play-lh.googleusercontent.com/4Z1Nt1I9HUDevt5VJ7BmgpqSTUpsC0Ei1K-IiXSmkH5Dzorz_isDzq4qdpb75RA1SfOV7v6csav-atWBur1wJQM'),
    ('photos', 'https://play-lh.googleusercontent.com/kErBTF4VcGwhtKbCr80Bs2R1lNZiYkHbKcf1i3ZF6dg_5LqDAlCI4wU-nzwvo7PAbxeBXM_tv1hc11gr4aIIW-Q'),
)
ICON_HOSTS = {'play-lh.googleusercontent.com', 'img.utdstc.com'}
ICON_MAX = 2 * 1024 * 1024
ICON_CURL_TIMEOUT = 75


def icon_dimensions(data):
    """Return (format, extension, width, height) from a bounded image header."""
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        if len(data) < 24 or data[12:16] != b'IHDR':
            raise ValueError('invalid PNG header')
        width, height = struct.unpack('>II', data[16:24])
        if not width or not height:
            raise ValueError('invalid PNG dimensions')
        return 'PNG', 'png', width, height
    if data.startswith(b'\xff\xd8'):
        # JPEG dimensions live in a Start Of Frame segment. APP/COM segments may
        # occur first; SOS/EOI before SOF means the header is incomplete.
        i = 2
        sof = set(range(0xc0, 0xc4)) | set(range(0xc5, 0xc8)) | set(range(0xc9, 0xcc)) | set(range(0xcd, 0xd0))
        while i < len(data):
            while i < len(data) and data[i] == 0xff:
                i += 1
            if i >= len(data):
                break
            marker = data[i]
            i += 1
            if marker in (0x01, 0xd8, 0xd9) or 0xd0 <= marker <= 0xd7:
                continue
            if marker == 0xda:
                break
            if i + 2 > len(data):
                break
            size = struct.unpack('>H', data[i:i + 2])[0]
            if size < 2 or i + size > len(data):
                break
            if marker in sof:
                if size < 7:
                    break
                height, width = struct.unpack('>HH', data[i + 3:i + 7])
                if not width or not height:
                    break
                return 'JPEG', 'jpg', width, height
            i += size
        raise ValueError('invalid JPEG header')
    if len(data) >= 12 and data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        # W16v review: the RIFF size must cover the container; chunks may not run past it.
        riff_end = 8 + struct.unpack('<I', data[4:8])[0]
        if riff_end < 12 or riff_end > len(data):
            raise ValueError('invalid WebP container size')
        data = data[:riff_end]
        i = 12
        while i + 8 <= len(data):
            kind = data[i:i + 4]
            size = struct.unpack('<I', data[i + 4:i + 8])[0]
            start, end = i + 8, i + 8 + size
            if end > len(data):
                break
            payload = data[start:end]
            if kind == b'VP8X' and len(payload) >= 10:
                width = 1 + int.from_bytes(payload[4:7], 'little')
                height = 1 + int.from_bytes(payload[7:10], 'little')
                return 'WebP', 'webp', width, height
            if kind == b'VP8 ' and len(payload) >= 10 and payload[3:6] == b'\x9d\x01\x2a':
                width = struct.unpack('<H', payload[6:8])[0] & 0x3fff
                height = struct.unpack('<H', payload[8:10])[0] & 0x3fff
                if width and height:
                    return 'WebP', 'webp', width, height
            if kind == b'VP8L' and len(payload) >= 5 and payload[0] == 0x2f:
                width = 1 + (payload[1] | ((payload[2] & 0x3f) << 8))
                height = 1 + (((payload[2] >> 6) & 0x03) | (payload[3] << 2) | ((payload[4] & 0x0f) << 10))
                return 'WebP', 'webp', width, height
            i = end + (size & 1)
        raise ValueError('invalid WebP header')
    raise ValueError('unsupported image magic')


def icons():
    """Fetch owner-supplied app icons into the packet, never following untrusted hosts."""
    from urllib.parse import urlsplit
    dest = OUT / 'icons'
    dest.mkdir(exist_ok=True)
    records = []
    for app_id, source_url in ICON_SOURCES:
        tmp = None
        try:
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', str(app_id)):
                raise ValueError('icon id is not a plain name')
            parsed = urlsplit(source_url)
            if parsed.scheme != 'https' or parsed.hostname not in ICON_HOSTS or parsed.username or parsed.password or parsed.port:
                raise ValueError('URL host or scheme is not allowlisted')
            fetch_url = source_url + ('=w240-h480' if parsed.hostname == 'play-lh.googleusercontent.com' else '')
            ext_path = dest / (app_id + '.download')
            if ext_path.exists():
                ext_path.unlink()
            tmp = ext_path
            # W16v review: curl streams to this process, which stops at ICON_MAX + 1 bytes, so a
            # reply without Content-Length cannot pass the cap (--max-filesize alone does not hold).
            p = subprocess.Popen(
                ['curl', '--fail', '--silent', '--show-error', '--proto', '=https',
                 '--max-filesize', str(ICON_MAX), '--connect-timeout', '20', '--max-time', '60',
                 '--output', '-', fetch_url], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            chunks, size, start = [], 0, time.time()
            try:
                while True:
                    chunk = p.stdout.read(65536)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > ICON_MAX:
                        break
                    chunks.append(chunk)
                    if time.time() - start > ICON_CURL_TIMEOUT:
                        raise ValueError('download took longer than %d s' % ICON_CURL_TIMEOUT)
            finally:
                if p.poll() is None:
                    p.kill()
                code = p.wait()
                if p.stdout is not None:
                    p.stdout.close()
            if size > ICON_MAX:
                raise ValueError('download is over %d bytes' % ICON_MAX)
            if code != 0:
                raise ValueError('curl exit %d' % code)
            if not size:
                raise ValueError('download is empty')
            data = b''.join(chunks)
            tmp.write_bytes(data)
            fmt, ext, width, height = icon_dimensions(data)
            final = dest / (app_id + '.' + ext)
            if final.exists():
                final.unlink()
            tmp.replace(final)
            tmp = None
            records.append({'id': app_id, 'url': source_url, 'bytes': size,
                            'sha256': hashlib.sha256(data).hexdigest(), 'format': fmt,
                            'width': width, 'height': height})
            say('OK', 'icon %s (%s, %dx%d, %d bytes)' % (app_id, fmt, width, height, size))
        except Exception as e:
            say('NOTE', 'icon %s FAIL: %s' % (app_id, str(e)[:180]))
        finally:
            if tmp is not None:
                try:
                    tmp.unlink()
                except OSError:
                    pass
    (dest / 'icons.json').write_text(json.dumps(records, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return records


def loads(data, default):
    """Decode JSON without turning valid empty collections into the default."""
    if not data:
        return default
    try:
        value = json.loads(data)
    except (TypeError, ValueError):
        return default
    return default if value is None else value


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
    got = icons() if ICONS else []
    ICON_COUNT[0] = len(got)
    case_review()
    return finish()


ICON_COUNT = [0]


def finish():
    try:
        (OUT / 'P2-RESULT.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        z = shutil.make_archive(str(OUT), 'zip', root_dir=str(OUT.parent), base_dir=OUT.name)
        size = pathlib.Path(z).stat().st_size
    except Exception as e:  # W16v round 2: any failure here still ends in one RESULT line
        print('RESULT STOP: zip failed (%s); the folder %s keeps everything read. Script kept.' % (e, OUT))
        return 1
    if bad[0]:
        print('RESULT STOP: %d read(s) failed; upload %s (%d bytes) anyway. Script kept.' % (bad[0], z, size))
        return 1
    me, gone = pathlib.Path(__file__).resolve(), False
    if me.parent == HOME and me.name.startswith('pf-p2-'):
        try:
            me.unlink()
            gone = True
        except OSError:
            pass
    icon_note = (' Icons %d of %d.' % (ICON_COUNT[0], len(ICON_SOURCES))) if ICONS else ''
    print('RESULT OK. Upload %s (%d bytes).%s%s' % (z, size, icon_note, ' Script removed.' if gone else ''))
    return 0


def entry():
    """W16v review: one RESULT line even when setup fails (home folder unusable, disk check)."""
    try:
        return main()
    except Exception as e:
        print('RESULT STOP: probe setup error %s: %s. Script kept.' % (type(e).__name__, str(e)[:200]), flush=True)
        return 1


if __name__ == '__main__':
    sys.exit(entry())
