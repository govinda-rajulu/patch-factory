#!/usr/bin/env python3
"""pf-t1.py: test every flow of govinda-rajulu/patch-factory once (10 Oct 2026, IST).

The all-flows test (packet W13: committed here, gated on a given main). Run it after a
merge: PF_MAIN=<full sha of main> python3 pf-t1.py (a packet controller passes it).
Nothing is merged or deleted. One dispatch at a time, each waited for. Phases:
  gate       gh logged in; live main is PF_MAIN (a rerun after a STOP accepts the main
             the first attempt recorded, because Community and Selection watch push to main)
  batch      9. Batch Patch, publish=false, every enabled app: builds all apps with the new
             version rule and publishes nothing
  check      2. Check new patch: the daily flow, run now (it publishes only apps whose
             provider or store changed, exactly as the 17:53 IST schedule does)
  provider   6. Provider watch    nightly  7. Nightly watch
  community  8. Community watch   tooling  Tooling watch   selection  10. Selection watch
  status     waits for "Status page data" after the last run; lists what is still red
Per app it records: worked or not, app version, the last COVERAGE line, lost and dropped
patches, a provider fallback, version step-downs, and the first error line. A rerun after a STOP reuses the runs it already dispatched.
RESULT OK means every run finished and was read; app failures are listed as findings.
"""
import datetime
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time

REPO = 'govinda-rajulu/patch-factory'
MAIN = os.environ.get('PF_MAIN', '')
GH = os.environ.get('PF_GH', 'gh')
POLL = int(os.environ.get('PF_POLL', '30'))
BUILD_WAIT = int(os.environ.get('PF_BUILD_WAIT', '9000'))
WAIT = int(os.environ.get('PF_WAIT', '3600'))
JOB = re.compile(r'(?:^|/ )Patch ([a-z0-9][a-z0-9-]*)$')
FLOWS = [('provider', 'agent-watch.yml', '6. Provider watch'), ('nightly', 'watch.yml', '7. Nightly watch'),
         ('community', 'community-watch.yml', '8. Community watch'), ('tooling', 'tooling-watch.yml', 'Tooling watch'),
         ('selection', 'selection-watch.yml', '10. Selection watch')]

STAMP = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
HOME = pathlib.Path(os.environ.get('PF_HOME', str(pathlib.Path.home())))
WORK = HOME / 'work'
LOGS = WORK / 'run-logs' / ('pf-t1-' + STAMP)
SELF = pathlib.Path(__file__).resolve()
SINCE_FILE = WORK / 'run-logs' / 'pf-t1.since'
R = {'script': SELF.name, 'stamp': STAMP, 'phases': [], 'apps': {}, 'flows': {}, 'result': 'RUNNING'}


def save():
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / 'RESULT.json').write_text(json.dumps(R, indent=1) + '\n', encoding='utf-8')


def say(phase, status, detail):
    print('%s %s: %s' % (status, phase, detail), flush=True)
    R['phases'].append(dict(phase=phase, status=status, detail=detail))
    save()


def stop(phase, why):
    say(phase, 'STOP', why)
    R['result'] = 'STOP'
    save()
    print('RESULT STOP at %s. Kept: this script, logs %s. Paste RESULT.json back; do not rerun before reading it.' % (phase, LOGS))
    sys.exit(1)


def run(cmd, timeout=300, out=None):
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, b'', b'timeout'
    except FileNotFoundError:
        return 127, b'', ('%s is not installed or not on PATH' % cmd[0]).encode()
    if out is not None:
        pathlib.Path(out).write_bytes(r.stdout)
    return r.returncode, r.stdout, r.stderr


def must(path, phase):
    code, out, err = run([GH, 'api', path], timeout=180)
    if code != 0:
        stop(phase, 'GET %s failed: %s' % (path, (err or out).decode('utf-8', 'replace').strip()[:200]))
    text = out.decode('utf-8', 'replace').strip()
    return json.loads(text) if text else {}


def raw(path, phase):
    code, out, err = run([GH, 'api', '-H', 'Accept: application/vnd.github.raw', path], timeout=180)
    if code != 0:
        stop(phase, 'GET %s failed: %s' % (path, (err or out).decode('utf-8', 'replace').strip()[:200]))
    return out.decode('utf-8', 'replace')


def gate():
    code, out, err = run([GH, 'auth', 'status'], timeout=60)
    if code != 0:
        stop('gate', 'gh is not logged in: ' + (err or out).decode('utf-8', 'replace').strip()[:200])
    if not re.fullmatch(r'[0-9a-f]{40}', MAIN):
        stop('gate', 'set PF_MAIN to the full sha of the main to test. Nothing dispatched.')
    main = must('repos/%s/branches/main' % REPO, 'gate')['commit']['sha']
    first = SINCE_FILE.read_text(encoding='utf-8').split() if SINCE_FILE.is_file() else []
    rerun = len(first) == 2 and first[1] == MAIN
    if main != MAIN and not rerun:
        stop('gate', 'MAIN_MOVED: live main %s is not PF_MAIN %s. Nothing dispatched.' % (main[:12], MAIN[:12]))
    targets = json.loads(raw('repos/%s/contents/src/targets.json?ref=%s' % (REPO, main), 'gate'))
    apps = [t['id'] for t in targets if t.get('enabled') is True]
    if not apps:
        stop('gate', 'no enabled app in src/targets.json')
    R.update(main=main, enabled=apps, since=since())
    note = '' if main == MAIN else ' (rerun: main moved since the first attempt, e.g. a watch snapshot)'
    say('gate', 'OK', 'main %s%s, %d enabled apps: %s' % (main[:12], note, len(apps), ', '.join(apps)))
    return main, apps


def since():
    """Start of the first attempt; a rerun reuses runs dispatched after it. (Community watch
    pushes to main, so runs are matched by time, not by head commit.)"""
    if SINCE_FILE.is_file():
        old = SINCE_FILE.read_text(encoding='utf-8').split()
        if len(old) == 2 and old[1] == MAIN:
            return old[0]
    SINCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    value = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=60)).strftime('%Y-%m-%dT%H:%M:%SZ')
    SINCE_FILE.write_text(value + ' ' + MAIN + '\n', encoding='utf-8')
    return value


def runs_of(file, main, phase, want=lambda r: True):
    rows = must('repos/%s/actions/workflows/%s/runs?event=workflow_dispatch&per_page=20' % (REPO, file), phase)
    return [r for r in rows.get('workflow_runs', []) if (r.get('created_at') or '') >= R['since'] and want(r)]


def dispatch_and_wait(phase, file, main, fields, limit, want=lambda r: True):
    have = runs_of(file, main, phase, want)
    if have:
        say(phase, 'SKIP', 'run %s was already dispatched by this test; not dispatching again' % have[0]['id'])
    else:
        cmd = [GH, 'workflow', 'run', file, '--repo', REPO, '--ref', 'main']
        for k, v in fields:
            cmd += ['-f', '%s=%s' % (k, v)]
        code, out, err = run(cmd, timeout=120)
        if code != 0:
            stop(phase, 'dispatch failed: ' + (err or out).decode('utf-8', 'replace')[:200])
        say(phase, 'OK', 'dispatched %s' % file)
    end = time.time() + limit
    while True:
        have = runs_of(file, main, phase, want)
        if have and have[0].get('status') == 'completed':
            return have[0]
        if time.time() > end:
            stop(phase, 'no finished %s run after %d s; nothing else dispatched' % (file, limit))
        time.sleep(POLL)


def clean(line):
    line = re.sub(r'\x1b\[[0-9;]*m', '', line)
    return re.sub(r'^\S+Z ', '', line).strip()[:300]


def read_apps(phase, r):
    """Per app: conclusion from the jobs API, details from the run log."""
    jobs = []
    page = 1
    while True:
        rows = must('repos/%s/actions/runs/%s/jobs?per_page=100&page=%d' % (REPO, r['id'], page), phase).get('jobs', [])
        jobs += rows
        if len(rows) < 100:
            break
        page += 1
    log = LOGS / ('%s-%s.log' % (phase, r['id']))
    run([GH, 'run', 'view', str(r['id']), '--repo', REPO, '--log'], timeout=600, out=log)
    lines = log.read_bytes().decode('utf-8', 'replace').splitlines() if log.exists() else []
    found = {}
    for j in jobs:
        m = JOB.search(j.get('name') or '')
        if not m:
            continue
        app = m[1]
        mine = [clean(l.split('\t', 2)[2]) for l in lines if l.split('\t', 1)[0] == j.get('name') and l.count('\t') >= 2]
        pick = lambda key: [l for l in mine if key in l and 'echo ' not in l]
        found[app] = dict(
            run=r['id'], result=j.get('conclusion'), url=j.get('html_url'),
            version=next((l[8:] for l in mine if l.startswith('VERSION=')), ''),
            coverage=(pick('COVERAGE ') or [''])[-1], lost=pick('COVERAGE_LOST')[:10],
            dropped=pick('PATCH_DROPPED')[:10], fallback=(pick('PROVIDER_FALLBACK') or [''])[0][:300],
            attempts=(pick('ATTEMPTS_OK') or pick('ATTEMPTS_FAILED') or [''])[-1][:200],
            unavailable=pick('COVERAGE_UNAVAILABLE')[:2], step_down=pick('VERSION_STEP_DOWN')[:3],
            applied=(pick('applied ') or [''])[-1][:120],
            error=(pick('##[error]') or pick('[-] ') or [''])[0])
    return found


def batch(main, apps):
    r = dispatch_and_wait('batch', 'batch-patch.yml', main, [('targets', ','.join(apps)), ('publish', 'false')], BUILD_WAIT,
                          want=lambda x: 'publish=false' in (x.get('display_title') or x.get('name') or ''))
    found = read_apps('batch', r)
    for app in apps:
        row = found.get(app) or dict(run=r['id'], result='missing', error='no job for this app in the batch run')
        R['apps'][app] = dict(batch=row)
    bad = [a for a in apps if R['apps'][a]['batch'].get('result') != 'success']
    say('batch', 'OK' if not bad else 'FINDING', 'run %s: %d of %d apps worked without publishing%s'
        % (r['id'], len(apps) - len(bad), len(apps), ('; failed: ' + ', '.join(bad)) if bad else ''))
    for a in apps:
        b = R['apps'][a]['batch']
        note = b.get('coverage') if b.get('result') == 'success' else (b.get('error') or b.get('coverage'))
        print('   %-16s %-8s %-18s %s' % (a, b.get('result'), b.get('version') or '-', note or ''), flush=True)
    save()


def check(main):
    r = dispatch_and_wait('check', 'ci.yml', main, [], BUILD_WAIT)
    found = read_apps('check', r)
    R['flows']['check'] = dict(run=r['id'], conclusion=r.get('conclusion'), url=r.get('html_url'),
                               built=sorted(found), failed=sorted(a for a, v in found.items() if v['result'] not in ('success', 'skipped')))
    for a, v in found.items():
        R['apps'].setdefault(a, {})['check'] = v
    say('check', 'OK' if r.get('conclusion') == 'success' and not R['flows']['check']['failed'] else 'FINDING', '2. Check new patch run %s ended %s; app jobs: %s'
        % (r['id'], r.get('conclusion'), ', '.join('%s=%s' % (a, v['result']) for a, v in sorted(found.items())) or 'none (nothing new)'))


def flows(main):
    last = None
    for key, file, name in FLOWS:
        r = dispatch_and_wait(key, file, main, [], WAIT)
        R['flows'][key] = dict(name=name, run=r['id'], conclusion=r.get('conclusion'), url=r.get('html_url'))
        say(key, 'OK' if r.get('conclusion') == 'success' else 'FINDING', '%s run %s ended %s' % (name, r['id'], r.get('conclusion')))
        last = r
    return (last or {}).get('updated_at') or ''




def status(after):
    end = time.time() + WAIT
    while True:
        rows = must('repos/%s/actions/workflows/status.yml/runs?per_page=20' % REPO, 'status').get('workflow_runs', [])
        good = [x for x in rows if (x.get('created_at') or '') >= after and x.get('status') == 'completed' and x.get('conclusion') == 'success']
        if good:
            break
        if time.time() > end:
            say('status', 'FINDING', 'no new successful "Status page data" run within %d s' % WAIT)
            return
        time.sleep(POLL)
    doc = json.loads(raw('repos/%s/contents/status.json?ref=status' % REPO, 'status'))
    (LOGS / 'status.json').write_text(json.dumps(doc, indent=1) + '\n', encoding='utf-8')
    h = doc.get('headline') or {}
    R['status'] = dict(generated_at=doc.get('generated_at'), apps=h.get('apps'), workflows=h.get('workflows'),
                       issues=[i.get('title') for i in doc.get('issues') or []])
    say('status', 'OK', 'page data %s: red apps %s; red automations %s; open Failing issues %d'
        % (doc.get('generated_at'), h.get('apps') or 'none', h.get('workflows') or 'none', len(R['status']['issues'])))


def main():
    save()
    m, apps = gate()
    batch(m, apps)
    check(m)
    after = flows(m)
    status(after)
    R['result'] = 'OK'
    save()
    digest = hashlib.sha256(SELF.read_bytes()).hexdigest()
    removed = SELF.name.startswith('pf-t1-') and digest.startswith(SELF.stem.split('-')[-1])
    if removed:
        SELF.unlink()
    SINCE_FILE.unlink()
    findings = [p for p in R['phases'] if p['status'] == 'FINDING']
    with open(WORK / 'run-ledger.txt', 'a', encoding='utf-8') as f:
        f.write('%s pf-t1.py %s OK main=%s findings=%d\n' % (STAMP, digest[:12], m[:12], len(findings)))
    print('RESULT OK: every run finished and was read; %d finding(s). Logs: %s. Zip and upload that folder. Script %s.'
          % (len(findings), LOGS, 'removed' if removed else 'kept'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
