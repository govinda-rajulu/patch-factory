#!/usr/bin/env python3
"""Packet controller for govinda-rajulu/patch-factory (generic template since 10 Oct 2026).

Copy this file, fill the CONFIG block (the build step fills the TREE and BUNDLE placeholders),
name the result pf-<packet>-<first 8 of its sha256>.py and hand it over with an if/then
launcher that checks bytes and sha256. How-to: docs/review/controllers/README.md.

Runs on the owner box. Every phase reads state first, so a rerun skips finished work and
never pushes, merges or dispatches twice. One side effect per phase, each with its own
result line. Phases:
  gate      gh logged in; live main is BASE (or the packet is already merged)
  clone     fresh stamped clone; the packet tree from the embedded bundle, checked by tree id,
            committed on BASE with a fixed author and date (same commit id on a rerun)
  push      new branch BRANCH (only if absent; a different head there stops)
  pr        open the pull request (only if none)
  validate  wait for CHECKS on the packet head (and OPTIONAL checks when they appear);
            any that fails stops before merge
  smoke     one nonpublishing Manual Patch per app in SMOKE on BRANCH; each must work and
            print a COVERAGE line (not COVERAGE_UNAVAILABLE), or nothing merges
  merge     merge commit guarded by the head sha; the merge tree must be the packet tree
  close     for each issue in CLOSE: one marked comment, then close
  pages     wait until GitHub Pages has deployed the merge, so the cleanup preview below
            does not go stale a minute later (W12 lesson L049)
  preview   cleanup.py preview only; writes the apply line; deletes nothing
RESULT OK: removes its clone and this script, appends a ledger line, keeps logs.
Any STOP: keeps everything and says where.
"""
import base64
import datetime
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

# ---- CONFIG -------------------------------------------------------------------------------
PACKET = 'h12'
REPO = 'govinda-rajulu/patch-factory'
BASE = os.environ.get('PF_BASE', '9a50d03870140e4a4e51484551b93c65265446c8')  # live main, full sha
BASE_TREE = '53dc55fb41fedeb7b49a1ecc82ab3b266f9644d4'  # the tree the packet was built on
PREREQ = 'a7f1f0afadee21c75db96231f18e484d542692b1'  # bundle prerequisite, an ancestor of BASE
HEAD = ''
TREE = '@@TREE@@'
BRANCH = 'packet/' + PACKET
WHO = 'Govindarajulu K <285203866+govinda-rajulu@users.noreply.github.com>'
WHEN = '2026-10-09T21:30:00+0000'
MESSAGE = 'packet H12: handover'
TITLE = 'packet H12: handover'
BODY = 'Packet H12. Tree %(tree)s tested in the assistant sandbox: full local suite OK. Opened by %(script)s.'
CHECKS = ('Validate targets and scripts',)
OPTIONAL = ('Onboarding record', 'Agent review (required for onboarding)')
SMOKE = ()          # app ids to build without publishing on BRANCH before the merge
CLOSE = ()          # (issue number, closing comment) pairs, done after the merge
PAGES_WAIT = int(os.environ.get('PF_PAGES_WAIT', '900'))
BUNDLE = '@@BUNDLE@@'
# -------------------------------------------------------------------------------------------
REMOTE = os.environ.get('PF_REMOTE', 'https://github.com/%s.git' % REPO)
GH = os.environ.get('PF_GH', 'gh')
WAIT = int(os.environ.get('PF_WAIT', '2700'))
BUILD_WAIT = int(os.environ.get('PF_BUILD_WAIT', '5400'))
POLL = int(os.environ.get('PF_POLL', '30'))

STAMP = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
HOME = pathlib.Path(os.environ.get('PF_HOME', str(pathlib.Path.home())))
WORK = HOME / 'work'
CLONE = WORK / ('patch-factory-%s-%s' % (PACKET, STAMP))
LOGS = WORK / 'run-logs' / ('pf-%s-%s' % (PACKET, STAMP))
SELF = pathlib.Path(__file__).resolve()
R = {'script': SELF.name, 'stamp': STAMP, 'base': BASE, 'tree': TREE, 'phases': [], 'result': 'RUNNING'}


def save():
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / 'RESULT.json').write_text(json.dumps(R, indent=1) + '\n', encoding='utf-8')


def say(phase, status, detail, **extra):
    print('%s %s: %s' % (status, phase, detail), flush=True)
    R['phases'].append(dict(phase=phase, status=status, detail=detail, **extra))
    save()


def stop(phase, why):
    say(phase, 'STOP', why)
    R['result'] = 'STOP'
    save()
    where = ('clone %s' % CLONE) if CLONE.exists() else 'no clone was made'
    print('RESULT STOP at %s. Kept: %s, this script, logs %s. Paste RESULT.json back; do not rerun before reading it.' % (phase, where, LOGS))
    sys.exit(1)


def run(cmd, cwd=None, timeout=900, out=None):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, b'', b'timeout'
    except FileNotFoundError:
        return 127, b'', ('%s is not installed or not on PATH' % cmd[0]).encode()
    if out is not None:
        pathlib.Path(out).write_bytes(r.stdout)
    return r.returncode, r.stdout, r.stderr


def api(path, method='GET', fields=None, phase='api'):
    cmd = [GH, 'api', '-X', method, path]
    for k, v in (fields or {}).items():
        cmd += ['-f' if isinstance(v, str) else '-F', '%s=%s' % (k, v)]
    code, out, err = run(cmd, timeout=180)
    if code != 0:
        return None, (err or out).decode('utf-8', 'replace').strip()[:300]
    text = out.decode('utf-8', 'replace').strip()
    return (json.loads(text) if text else {}), ''


def must(path, phase, method='GET', fields=None):
    data, err = api(path, method, fields, phase)
    if data is None:
        stop(phase, '%s %s failed: %s' % (method, path, err))
    return data


def main_sha(phase):
    return must('repos/%s/branches/main' % REPO, phase)['commit']['sha']


def find_pr(phase):
    """The packet pull request: from BRANCH, and its head commit carries the packet tree."""
    rows = must('repos/%s/pulls?state=all&head=govinda-rajulu:%s&per_page=20' % (REPO, BRANCH), phase)
    for p in rows:
        sha = (p.get('head') or {}).get('sha') or ''
        if (p.get('head') or {}).get('ref') != BRANCH or not sha:
            continue
        c = must('repos/%s/git/commits/%s' % (REPO, sha), phase)
        if (c.get('tree') or {}).get('sha') == TREE:
            return p
    return None


def gate():
    code, out, err = run([GH, 'auth', 'status'], timeout=60)
    if code != 0:
        stop('gate', 'gh is not logged in: ' + (err or out).decode('utf-8', 'replace').strip()[:200])
    main = main_sha('gate')
    pr = find_pr('gate')
    merged = bool(pr and pr.get('merged_at'))
    R.update(main_at_start=main, pr=pr and pr['number'], merged_at_start=merged)
    if main != BASE and not merged:
        stop('gate', 'MAIN_MOVED: live main %s is not the base %s and %s is not merged. Nothing changed.' % (main[:12], BASE[:12], PACKET))
    if not merged:
        bt = (must('repos/%s/git/commits/%s' % (REPO, BASE), 'gate').get('tree') or {}).get('sha')
        if bt != BASE_TREE:
            stop('gate', 'base %s has tree %s, not the tree %s this packet was built on. Nothing changed.' % (BASE[:12], (bt or '')[:12], BASE_TREE[:12]))
    say('gate', 'OK', 'main %s, %s %s' % (main[:12], PACKET, 'already merged' if merged else 'not merged yet'))
    return pr, merged


def clone():
    WORK.mkdir(parents=True, exist_ok=True)
    code, out, err = run(['git', 'clone', '-q', REMOTE, str(CLONE)], timeout=900)
    if code != 0:
        stop('clone', 'git clone failed: ' + err.decode('utf-8', 'replace')[:200])
    global HEAD
    bundle = LOGS / ('pf-%s.bundle' % PACKET)
    bundle.write_bytes(base64.b64decode(BUNDLE))
    have, _, _ = run(['git', 'cat-file', '-e', PREREQ + '^{commit}'], cwd=CLONE)
    if have != 0:
        stop('clone', 'the clone lacks the bundle prerequisite %s; nothing changed' % PREREQ[:12])
    for c in (['git', 'bundle', 'verify', str(bundle)], ['git', 'fetch', '-q', str(bundle), 'refs/heads/%s:refs/pf/%s' % (BRANCH, PACKET)]):
        code, out, err = run(c, cwd=CLONE)
        if code != 0:
            stop('clone', ' '.join(c[:3]) + ' failed: ' + err.decode('utf-8', 'replace')[:200])
    _, t, _ = run(['git', 'rev-parse', 'refs/pf/%s^{tree}' % PACKET], cwd=CLONE)
    if t.decode().strip() != TREE:
        stop('clone', 'packet tree is %s, expected %s' % (t.decode().strip()[:12], TREE[:12]))
    name, mail = WHO.split(' <')
    env = dict(os.environ, GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=mail.rstrip('>'), GIT_AUTHOR_DATE=WHEN,
               GIT_COMMITTER_NAME=name, GIT_COMMITTER_EMAIL=mail.rstrip('>'), GIT_COMMITTER_DATE=WHEN)
    r = subprocess.run(['git', 'commit-tree', TREE, '-p', BASE, '-m', MESSAGE], cwd=CLONE, env=env, capture_output=True)
    HEAD = r.stdout.decode().strip()
    if r.returncode != 0 or len(HEAD) != 40:
        stop('clone', 'commit-tree failed: ' + r.stderr.decode('utf-8', 'replace')[:200])
    code, _, err = run(['git', 'checkout', '-q', '--detach', HEAD], cwd=CLONE)
    if code != 0:
        stop('clone', 'checkout of the packet head failed: ' + err.decode('utf-8', 'replace')[:200])
    R['head'] = HEAD
    say('clone', 'OK', 'packet head %s (tree %s) on base %s' % (HEAD[:12], TREE[:12], BASE[:12]))


def push():
    code, out, err = run(['git', 'ls-remote', REMOTE, 'refs/heads/' + BRANCH], timeout=120)
    if code != 0:
        stop('push', 'ls-remote failed')
    have = out.decode().split('\t')[0].strip()
    if have == HEAD:
        say('push', 'SKIP', 'branch %s already at the packet head' % BRANCH)
        return
    if have:
        stop('push', 'branch %s exists at %s, not the packet head. Nothing pushed.' % (BRANCH, have[:12]))
    code, out, err = run(['git', 'push', '-q', REMOTE, '%s:refs/heads/%s' % (HEAD, BRANCH)], cwd=CLONE, timeout=300)
    if code != 0:
        stop('push', 'git push failed: ' + err.decode('utf-8', 'replace')[:200])
    say('push', 'OK', 'pushed %s to %s (new branch)' % (HEAD[:12], BRANCH))


def open_pr():
    pr = find_pr('pr')
    if pr:
        say('pr', 'SKIP', 'pull request #%d already exists' % pr['number'])
        return pr
    body = BODY % dict(tree=TREE[:12], script=SELF.name, smoke=', '.join(SMOKE) or 'none')
    pr = must('repos/%s/pulls' % REPO, 'pr', 'POST', dict(title=TITLE, head=BRANCH, base='main', body=body))
    say('pr', 'OK', 'opened #%d' % pr['number'], url=pr.get('html_url'))
    return pr


def validate():
    end = time.time() + WAIT
    while True:
        runs = must('repos/%s/commits/%s/check-runs?per_page=100' % (REPO, HEAD), 'validate').get('check_runs', [])
        state = {}
        for name in CHECKS + tuple(n for n in OPTIONAL if any(c.get('name') == n for c in runs)):
            mine = [c for c in runs if c.get('name') == name]
            done = [c for c in mine if c.get('status') == 'completed']
            if any(c.get('conclusion') == 'success' for c in done):
                state[name] = 'success'
            elif done and len(done) == len(mine):
                stop('validate', '%s ended %s: %s. Nothing merged. If it is the agent review, read its pull request comment; '
                     'merging over it is your call.' % (name, done[0].get('conclusion'), done[0].get('html_url')))
        if all(n in state for n in CHECKS) and not any(c.get('name') in OPTIONAL and c.get('status') != 'completed' for c in runs):
            say('validate', 'OK', 'passed on %s: %s' % (HEAD[:12], ', '.join(sorted(state))))
            return
        if time.time() > end:
            stop('validate', 'not all checks passed after %d s: %s' % (WAIT, ', '.join(n for n in CHECKS if n not in state)))
        time.sleep(POLL)


def merge(pr):
    pr = must('repos/%s/pulls/%d' % (REPO, pr['number']), 'merge')
    if pr.get('merged_at'):
        sha = pr.get('merge_commit_sha') or ''
        say('merge', 'SKIP', '#%d already merged as %s' % (pr['number'], sha[:12]))
        return tree_check(sha)
    if pr.get('head', {}).get('sha') != HEAD:
        stop('merge', 'pull request head %s is not the packet head %s' % (pr.get('head', {}).get('sha', '')[:12], HEAD[:12]))
    if main_sha('merge') != BASE:
        stop('merge', 'MAIN_MOVED before merge; nothing merged')
    out = must('repos/%s/pulls/%d/merge' % (REPO, pr['number']), 'merge', 'PUT', dict(merge_method='merge', sha=HEAD))
    sha = out.get('sha') or ''
    if not out.get('merged') or len(sha) != 40:
        stop('merge', 'merge answer was not a merge: %s' % json.dumps(out)[:200])
    say('merge', 'OK', 'merged #%d as %s' % (pr['number'], sha[:12]))
    return tree_check(sha)


def tree_check(sha):
    t = (must('repos/%s/git/commits/%s' % (REPO, sha), 'merge').get('tree') or {}).get('sha')
    if t != TREE:
        stop('merge', 'merge %s has tree %s, not the packet tree %s' % (sha[:12], (t or '')[:12], TREE[:12]))
    say('merge', 'OK', 'merge tree is the packet tree %s' % TREE[:12])
    return sha


def smoke_runs():
    path = 'repos/%s/actions/workflows/manual-patch.yml/runs?event=workflow_dispatch&head_sha=%s&per_page=30' % (REPO, HEAD)
    found = {}
    for r in must(path, 'smoke').get('workflow_runs', []):
        if r.get('head_branch') != BRANCH:
            continue
        for j in must('repos/%s/actions/runs/%s/jobs?per_page=50' % (REPO, r['id']), 'smoke').get('jobs', []):
            for t in SMOKE:
                if (j.get('name') or '').endswith('Patch ' + t) and t not in found:
                    found[t] = r
    return found


def smoke():
    """Nonpublishing builds on the packet branch prove the new resolver in CI before the merge."""
    R['smoke'] = {}
    for t in SMOKE:
        have = smoke_runs().get(t)
        if have:
            say('smoke', 'SKIP', '%s: run %s already exists on %s' % (t, have['id'], HEAD[:12]))
        else:
            code, out, err = run([GH, 'workflow', 'run', 'manual-patch.yml', '--repo', REPO, '--ref', BRANCH,
                                  '-f', 'target=' + t, '-f', 'publish=false'], timeout=120)
            if code != 0:
                stop('smoke', '%s: dispatch failed: %s. Nothing merged.' % (t, (err or out).decode('utf-8', 'replace')[:200]))
            say('smoke', 'OK', '%s: dispatched a nonpublishing Manual Patch on %s' % (t, BRANCH))
        end = time.time() + BUILD_WAIT
        while True:
            r = smoke_runs().get(t)
            if r and r.get('status') == 'completed':
                break
            if time.time() > end:
                stop('smoke', '%s: no finished run after %d s. Nothing merged.' % (t, BUILD_WAIT))
            time.sleep(POLL)
        log = LOGS / ('smoke-%s-%s.log' % (t, r['id']))
        run([GH, 'run', 'view', str(r['id']), '--repo', REPO, '--log'], timeout=300, out=log)
        text = log.read_bytes().decode('utf-8', 'replace') if log.exists() else ''
        cov = [l.split('Z ', 1)[-1].strip() for l in text.splitlines() if 'COVERAGE ' in l and ' covers ' in l and 'echo' not in l]
        lost = [l.split('Z ', 1)[-1].strip() for l in text.splitlines() if 'COVERAGE_LOST ' in l and 'echo' not in l]
        doubt = [l.split('Z ', 1)[-1].strip() for l in text.splitlines() if 'COVERAGE_UNAVAILABLE ' in l and 'echo' not in l and 'sed ' not in l]
        R['smoke'][t] = dict(run=r['id'], conclusion=r.get('conclusion'), url=r.get('html_url'), coverage=cov[:4],
                             lost=lost[:20], unavailable=doubt[:4])
        save()
        if r.get('conclusion') != 'success':
            stop('smoke', '%s: run %s ended %s: %s. Nothing merged; the log is kept.' % (t, r['id'], r.get('conclusion'), r.get('html_url')))
        if doubt or not cov:
            stop('smoke', '%s: run %s worked but the resolver %s. Nothing merged; the log is kept.'
                 % (t, r['id'], 'could not read the listing: ' + doubt[0] if doubt else 'printed no COVERAGE line'))
        say('smoke', 'OK', '%s: run %s worked; %s' % (t, r['id'], cov[0]))


def close_issues():
    for number, text in CLOSE:
        phase = 'close'
        issue = must('repos/%s/issues/%d' % (REPO, number), phase)
        if issue.get('state') == 'closed':
            say(phase, 'SKIP', '#%d already closed' % number)
            continue
        mark = '[pf-%s-close-%d]' % (PACKET, number)
        comments = must('repos/%s/issues/%d/comments?per_page=100' % (REPO, number), phase)
        if any(mark in (c.get('body') or '') for c in comments):
            say(phase, 'SKIP', 'closing comment already on #%d' % number)
        else:
            must('repos/%s/issues/%d/comments' % (REPO, number), phase, 'POST', dict(body=mark + '\n\n' + text))
            say(phase, 'OK', 'comment posted on #%d' % number)
        must('repos/%s/issues/%d' % (REPO, number), phase, 'PATCH', dict(state='closed', state_reason='completed'))
        say(phase, 'OK', '#%d closed' % number)


def pages(merge_sha):
    """Cleanup keeps the newest 5 Pages records; a deploy that lands after the preview makes
    its token stale (W12: STOP, token mismatch). Wait for the merge's own deployment first."""
    end = time.time() + PAGES_WAIT
    while True:
        rows = must('repos/%s/deployments?environment=github-pages&sha=%s&per_page=5' % (REPO, merge_sha), 'pages')
        if rows:
            st = must('repos/%s/deployments/%s/statuses?per_page=5' % (REPO, rows[0]['id']), 'pages')
            state = (st[0].get('state') if st else '') or 'pending'
            if state in ('success', 'failure', 'error', 'inactive'):
                say('pages', 'OK' if state == 'success' else 'FAIL', 'Pages deployment %s for %s: %s' % (rows[0]['id'], merge_sha[:12], state))
                return state == 'success'
        if time.time() > end:
            say('pages', 'FAIL', 'no finished Pages deployment for %s after %d s; the cleanup token may go stale' % (merge_sha[:12], PAGES_WAIT))
            return False
        time.sleep(POLL)


def preview():
    code, out, err = run([sys.executable, 'src/etc/cleanup.py', 'preview', '--out', str(LOGS / 'cleanup-preview.json')],
                         cwd=CLONE, timeout=900, out=LOGS / 'cleanup-preview.txt')
    text = out.decode('utf-8', 'replace')
    token = [l.split()[1] for l in text.splitlines() if l.startswith('TOKEN ')]
    if code != 0 or len(token) != 1:
        say('preview', 'FAIL', 'cleanup preview did not finish: ' + (err.decode('utf-8', 'replace') or text)[-300:])
        return False
    head = text.splitlines()[0] if text else ''
    apply = ('T=$(mktemp -d); if git clone -q --depth 1 https://github.com/%s.git "$T/pf"; then echo "OK clone"; else echo "STOP clone"; fi; '
             'if [ -f "$T/pf/src/etc/cleanup.py" ]; then python3 "$T/pf/src/etc/cleanup.py" apply --token %s '
             '--receipt "$HOME/work/run-logs/cleanup-receipt-$(date -u +%%Y%%m%%dT%%H%%M%%SZ).json"; fi' % (REPO, token[0]))
    (LOGS / 'cleanup-apply-command.txt').write_text(apply + '\n', encoding='utf-8')
    R['cleanup'] = dict(token=token[0], summary=head, apply_command=apply)
    say('preview', 'OK', head + ' TOKEN ' + token[0])
    return True


def finish(good):
    if not good:
        R['result'] = 'STOP'
        save()
        print('RESULT STOP: see the FAIL lines above. Kept: clone %s, this script, logs %s. Paste RESULT.json back.' % (CLONE, LOGS))
        return 1
    R['result'] = 'OK'
    save()
    shutil.rmtree(CLONE, ignore_errors=True)
    digest = hashlib.sha256(SELF.read_bytes()).hexdigest()
    removed = SELF.name.startswith('pf-%s-' % PACKET) and digest.startswith(SELF.stem.split('-')[-1])
    if removed:
        SELF.unlink()
    with open(WORK / 'run-ledger.txt', 'a', encoding='utf-8') as f:
        f.write('%s pf-%s.py %s OK pr=#%s merge=%s smoke=%s token=%s\n' % (STAMP, PACKET, digest[:12], R.get('pr'), (R.get('merge') or '')[:12],
                ','.join('%s:%s' % (k, v.get('run')) for k, v in R.get('smoke', {}).items()), R.get('cleanup', {}).get('token')))
    print('RESULT OK. Logs: %s (RESULT.json, cleanup-apply-command.txt, smoke logs). Zip and upload that folder. Clone removed; script %s.'
          % (LOGS, 'removed' if removed else 'kept (name does not carry its sha)'))
    return 0


def main():
    save()
    pr, merged = gate()
    clone()
    if not merged:
        push()
        pr = open_pr()
        R['pr'] = pr['number']
        validate()
        smoke()
    R['merge'] = merge(pr)
    close_issues()
    deployed = pages(R['merge'])
    previewed = preview()
    return finish(deployed and previewed)


if __name__ == '__main__':
    sys.exit(main())
