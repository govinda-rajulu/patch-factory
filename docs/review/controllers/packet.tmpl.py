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
  push      new branch BRANCH (only if absent; a different head there stops). With PARENT set
            (a fix on top of a pushed packet), BRANCH at PARENT is fast-forwarded instead
  pr        open the pull request (only if none); after a fast-forward, wait until the open
            pull request from BRANCH shows the new head
  validate  wait for CHECKS on the packet head (and OPTIONAL checks when they appear);
            any that fails stops before merge
  smoke     one nonpublishing Manual Patch per entry in SMOKE on BRANCH ("app", or
            "app/provider" to build one provider with its own pins); each must work and print
            a COVERAGE line (not COVERAGE_UNAVAILABLE), or nothing merges. Entries also in
            SMOKE_ADVISORY (fallback providers) are recorded as NOTE when they fail, never
            blocking: a broken fallback breaks nothing that works today
  merge     merge commit guarded by the head sha; the merge tree must be the packet tree
  close     for each issue in CLOSE: one marked comment, then close
  pages     wait until GitHub Pages has deployed the merge, so the cleanup preview below
            does not go stale a minute later (W12 lesson L049)
  preview   cleanup.py preview; writes the apply line
  cleanup   (W13) when CLEANUP_APPLY: applies that exact preview at once (the owner's launcher
            is the owner's command; PF_CLEANUP=keep skips it), receipt in the logs
  t1        (W13) when RUN_T1: docs/review/controllers/pf-t1.py, the all-flows test, on the
            merge; its own RESULT line and logs, reported here
Checks: CHECKS must pass; OPTIONAL checks that appear must pass; ADVISORY checks are
waited for and recorded, never blocking (owner's call, written in the packet record).
PRECHECKS: live GitHub facts the packet's records rely on, read before anything is pushed.
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
PARENT = os.environ.get('PF_PARENT', BASE)  # parent of the packet commit: BASE, or a pushed packet head to fast-forward
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
ADVISORY = ()       # check names waited for and recorded, never blocking
SMOKE = ()          # "app" or "app/provider" entries to build without publishing on BRANCH
SMOKE_ADVISORY = ()  # SMOKE entries whose failure is recorded (NOTE), never blocking
CLOSE = ()          # (issue number, closing comment) pairs, done after the merge
PRECHECKS = ()      # (api path, field, expected value, why) read in gate; a mismatch stops
CLEANUP_APPLY = False  # apply the cleanup preview at once (PF_CLEANUP=keep skips)
RUN_T1 = False      # run docs/review/controllers/pf-t1.py on the merge at the end
MIRROR = None       # (W13) dict(repo, files, manifest, anchor, branch, title): copy files from the
                    # merged tree into another repository of the owner by ITS OWN pull request
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
    for path, field, want, why in PRECHECKS:
        got = must(path, 'gate')
        for k in field.split('.'):
            got = (got or {}).get(k) if isinstance(got, dict) else None
        if got != want:
            stop('gate', 'PRECHECK %s: %s is %r, the packet says %r (%s). Nothing changed.' % (path, field, got, want, why))
        say('gate', 'OK', 'precheck %s %s = %r' % (path, field, got))
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
    if PARENT != BASE:
        ok, _, _ = run(['git', 'merge-base', '--is-ancestor', BASE, PARENT], cwd=CLONE)
        if ok != 0:
            stop('clone', 'parent %s is not a descendant of the base %s; nothing changed' % (PARENT[:12], BASE[:12]))
    _, t, _ = run(['git', 'rev-parse', 'refs/pf/%s^{tree}' % PACKET], cwd=CLONE)
    if t.decode().strip() != TREE:
        stop('clone', 'packet tree is %s, expected %s' % (t.decode().strip()[:12], TREE[:12]))
    name, mail = WHO.split(' <')
    env = dict(os.environ, GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=mail.rstrip('>'), GIT_AUTHOR_DATE=WHEN,
               GIT_COMMITTER_NAME=name, GIT_COMMITTER_EMAIL=mail.rstrip('>'), GIT_COMMITTER_DATE=WHEN)
    r = subprocess.run(['git', 'commit-tree', TREE, '-p', PARENT, '-m', MESSAGE], cwd=CLONE, env=env, capture_output=True)
    HEAD = r.stdout.decode().strip()
    if r.returncode != 0 or len(HEAD) != 40:
        stop('clone', 'commit-tree failed: ' + r.stderr.decode('utf-8', 'replace')[:200])
    code, _, err = run(['git', 'checkout', '-q', '--detach', HEAD], cwd=CLONE)
    if code != 0:
        stop('clone', 'checkout of the packet head failed: ' + err.decode('utf-8', 'replace')[:200])
    R['head'] = HEAD
    say('clone', 'OK', 'packet head %s (tree %s) on base %s%s' % (HEAD[:12], TREE[:12], BASE[:12],
        (', after the pushed head %s' % PARENT[:12]) if PARENT != BASE else ''))


def push():
    code, out, err = run(['git', 'ls-remote', REMOTE, 'refs/heads/' + BRANCH], timeout=120)
    if code != 0:
        stop('push', 'ls-remote failed')
    have = out.decode().split('\t')[0].strip()
    if have == HEAD:
        say('push', 'SKIP', 'branch %s already at the packet head' % BRANCH)
        return
    ff = bool(have) and PARENT != BASE and have == PARENT
    if have and not ff:
        stop('push', 'branch %s exists at %s, not the packet head%s. Nothing pushed.'
             % (BRANCH, have[:12], (' or its parent %s' % PARENT[:12]) if PARENT != BASE else ''))
    code, out, err = run(['git', 'push', '-q', REMOTE, '%s:refs/heads/%s' % (HEAD, BRANCH)], cwd=CLONE, timeout=300)
    if code != 0:
        stop('push', 'git push failed: ' + err.decode('utf-8', 'replace')[:200])
    say('push', 'OK', 'pushed %s to %s (%s)' % (HEAD[:12], BRANCH, ('fast-forward from %s' % PARENT[:12]) if ff else 'new branch'))


def open_pr():
    pr = find_pr('pr')
    if pr:
        say('pr', 'SKIP', 'pull request #%d already exists' % pr['number'])
        return pr
    if PARENT != BASE:
        # After a fast-forward GitHub moves the open pull request a little later; wait for it.
        end = time.time() + 300
        while True:
            rows = must('repos/%s/pulls?state=open&head=govinda-rajulu:%s&per_page=20' % (REPO, BRANCH), 'pr')
            mine = [p for p in rows if (p.get('head') or {}).get('ref') == BRANCH]
            if not mine:
                break
            pr = find_pr('pr')
            if pr:
                say('pr', 'OK', 'pull request #%d now shows the packet head %s' % (pr['number'], HEAD[:12]))
                return pr
            if time.time() > end:
                stop('pr', 'open pull request #%d from %s did not move to %s in 300 s. Nothing merged.' % (mine[0]['number'], BRANCH, HEAD[:12]))
            time.sleep(max(POLL, 1) if POLL else 0)
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
        waiting = [c for c in runs if c.get('name') in OPTIONAL + ADVISORY and c.get('status') != 'completed']
        if all(n in state for n in CHECKS) and not waiting:
            for c in runs:
                if c.get('name') in ADVISORY:
                    R.setdefault('advisory', {})[c['name']] = dict(conclusion=c.get('conclusion'), url=c.get('html_url'))
                    say('validate', 'OK' if c.get('conclusion') == 'success' else 'NOTE', 'advisory %s ended %s (not blocking): %s'
                        % (c['name'], c.get('conclusion'), c.get('html_url')))
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


def title(entry):
    app, _, provider = entry.partition('/')
    return 'Manual %s%s / publish=false' % (app, (' / ' + provider) if provider else '')


def smoke_runs():
    """Runs on BRANCH at HEAD, by run name (Manual APP[ / PROVIDER] / publish=false)."""
    path = 'repos/%s/actions/workflows/manual-patch.yml/runs?event=workflow_dispatch&head_sha=%s&per_page=50' % (REPO, HEAD)
    found = {}
    for r in must(path, 'smoke').get('workflow_runs', []):
        if r.get('head_branch') != BRANCH:
            continue
        for t in SMOKE:
            if (r.get('display_title') or '') == title(t) and t not in found:
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
            app, _, provider = t.partition('/')
            cmd = [GH, 'workflow', 'run', 'manual-patch.yml', '--repo', REPO, '--ref', BRANCH, '-f', 'target=' + app, '-f', 'publish=false']
            code, out, err = run(cmd + (['-f', 'provider=' + provider] if provider else []), timeout=120)
            if code != 0:
                stop('smoke', '%s: dispatch failed: %s. Nothing merged.' % (t, (err or out).decode('utf-8', 'replace')[:200]))
            say('smoke', 'OK', '%s: dispatched a nonpublishing Manual Patch on %s' % (t, BRANCH))
        end = time.time() + BUILD_WAIT
        soft = t in SMOKE_ADVISORY
        while True:
            r = smoke_runs().get(t)
            if r and r.get('status') == 'completed':
                break
            if time.time() > end:
                if soft:
                    R['smoke'][t] = dict(run=(r or {}).get('id'), conclusion='unfinished', advisory=True)
                    say('smoke', 'NOTE', '%s: advisory, no finished run after %d s (not blocking)' % (t, BUILD_WAIT))
                    break
                stop('smoke', '%s: no finished run after %d s. Nothing merged.' % (t, BUILD_WAIT))
            time.sleep(POLL)
        if not (r and r.get('status') == 'completed'):
            continue
        log = LOGS / ('smoke-%s-%s.log' % (t.replace('/', '-'), r['id']))
        run([GH, 'run', 'view', str(r['id']), '--repo', REPO, '--log'], timeout=300, out=log)
        text = log.read_bytes().decode('utf-8', 'replace') if log.exists() else ''
        cov = [l.split('Z ', 1)[-1].strip() for l in text.splitlines() if 'COVERAGE ' in l and ' covers ' in l and 'echo' not in l]
        lost = [l.split('Z ', 1)[-1].strip() for l in text.splitlines() if 'COVERAGE_LOST ' in l and 'echo' not in l]
        doubt = [l.split('Z ', 1)[-1].strip() for l in text.splitlines() if 'COVERAGE_UNAVAILABLE ' in l and 'echo' not in l and 'sed ' not in l]
        app, _, provider = t.partition('/')
        won = [l.split('Z ', 1)[-1].strip() for l in text.splitlines() if 'ATTEMPTS_OK ' in l and 'echo' not in l]
        dropped = [l.split('Z ', 1)[-1].strip() for l in text.splitlines() if 'PATCH_DROPPED ' in l and 'echo' not in l and 'print(' not in l]
        failed = [l.split('Z ', 1)[-1].strip()[:300] for l in text.splitlines() if 'ATTEMPT_FAILED ' in l and 'echo' not in l and 'print(' not in l]
        R['smoke'][t] = dict(run=r['id'], conclusion=r.get('conclusion'), url=r.get('html_url'), coverage=cov[:4],
                             lost=lost[:20], unavailable=doubt[:4], attempts=won[-1:], dropped=dropped[:20], failed=failed[:4],
                             advisory=soft)
        save()
        why = None
        if r.get('conclusion') != 'success':
            why = 'run %s ended %s: %s%s' % (r['id'], r.get('conclusion'), r.get('html_url'), ('; ' + failed[-1]) if failed else '')
        elif doubt or not cov:
            why = 'run %s worked but the resolver %s' % (r['id'], 'could not read the listing: ' + doubt[0] if doubt else 'printed no COVERAGE line')
        elif provider and not any((', winner %s' % provider) in w for w in won):
            why = 'run %s worked but not with provider %s (%s)' % (r['id'], provider, (won or ['no ATTEMPTS_OK line'])[-1])
        if why and soft:
            say('smoke', 'NOTE', '%s: advisory, %s (not blocking; the log is kept)' % (t, why))
            continue
        if why:
            stop('smoke', '%s: %s. Nothing merged; the log is kept.' % (t, why))
        say('smoke', 'OK', '%s: run %s worked; %s%s' % (t, r['id'], cov[-1], ('; dropped %d' % len(dropped)) if dropped else ''))


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


def done_file(phase):
    return WORK / 'run-logs' / ('pf-%s-%s.done' % (PACKET, phase))


def already(phase, merge_sha):
    """A rerun after a finished phase changes nothing."""
    f = done_file(phase)
    if f.is_file() and f.read_text(encoding='utf-8').strip() == merge_sha:
        say(phase, 'SKIP', 'already done for %s (%s)' % (merge_sha[:12], f.name))
        return True
    return False


def mark(phase, merge_sha):
    done_file(phase).parent.mkdir(parents=True, exist_ok=True)
    done_file(phase).write_text(merge_sha + '\n', encoding='utf-8')


def cleanup(merge_sha):
    if already('cleanup', merge_sha):
        return True
    if not CLEANUP_APPLY or os.environ.get('PF_CLEANUP') == 'keep':
        say('cleanup', 'SKIP', 'not applied here; the apply line is in cleanup-apply-command.txt')
        return True
    receipt = LOGS / ('cleanup-receipt-%s.json' % STAMP)
    code, out, err = run([sys.executable, 'src/etc/cleanup.py', 'apply', '--token', R['cleanup']['token'], '--receipt', str(receipt)],
                         cwd=CLONE, timeout=1800, out=LOGS / 'cleanup-apply.txt')
    text = out.decode('utf-8', 'replace').strip().splitlines()
    last = text[-1] if text else (err.decode('utf-8', 'replace')[-300:])
    if code != 0:
        say('cleanup', 'FAIL', 'cleanup apply: ' + last + ' (nothing is deleted on a stale token; run the printed apply line later)')
        return False
    R['cleanup']['applied'] = last
    mark('cleanup', merge_sha)
    say('cleanup', 'OK', last)
    return True


def mirror(merge_sha):
    """Copy the exact merged bytes into MIRROR['repo'] by its own pull request; merge it when its
    checks pass. Refuses when a target file exists with other bytes or the manifest anchor moved."""
    if not MIRROR or already('mirror', merge_sha):
        return True
    m, repo = MIRROR, MIRROR['repo']
    rows = must('repos/%s/pulls?state=all&head=govinda-rajulu:%s&per_page=20' % (repo, m['branch']), 'mirror')
    pr = next((p for p in rows if (p.get('head') or {}).get('ref') == m['branch']), None)
    if pr is None:
        dest = WORK / ('mirror-%s-%s' % (repo.split('/')[1], STAMP))
        code, _, err = run(['git', 'clone', '-q', os.environ.get('PF_MIRROR_REMOTE', 'https://github.com/%s.git' % repo), str(dest)], timeout=600)
        if code != 0:
            say('mirror', 'FAIL', 'clone of %s failed: %s' % (repo, err.decode('utf-8', 'replace')[:200]))
            return False
        for f in m['files']:
            new, old = (CLONE / f).read_bytes(), dest / f
            if old.exists() and old.read_bytes() != new:
                say('mirror', 'FAIL', '%s already has %s with other bytes; nothing pushed' % (repo, f))
                return False
            old.parent.mkdir(parents=True, exist_ok=True)
            old.write_bytes(new)
        mine = (CLONE / m['manifest']).read_bytes().decode('utf-8').splitlines()
        theirs_path = dest / m['manifest']
        theirs = theirs_path.read_bytes().decode('utf-8')
        add = [l for l in mine if any(l.startswith(f.rsplit('/', 1)[-1] + '\t') for f in m['files'])]
        need = [l for l in add if l not in theirs.splitlines()]
        if need:
            if not theirs.endswith('\n') or not theirs.splitlines()[-1].startswith(m['anchor']):
                say('mirror', 'FAIL', '%s manifest does not end with the %r line; nothing pushed' % (repo, m['anchor']))
                return False
            theirs_path.write_bytes((theirs + '\n'.join(need) + '\n').encode('utf-8'))
        name, mail = WHO.split(' <')
        env = dict(os.environ, GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=mail.rstrip('>'), GIT_AUTHOR_DATE=WHEN,
                   GIT_COMMITTER_NAME=name, GIT_COMMITTER_EMAIL=mail.rstrip('>'), GIT_COMMITTER_DATE=WHEN)
        for c in (['git', 'add', '--'] + m['files'] + [m['manifest']], ['git', 'commit', '-q', '-m', m['title']],
                  ['git', 'push', '-q', 'origin', 'HEAD:refs/heads/' + m['branch']]):
            r = subprocess.run(c, cwd=dest, env=env, capture_output=True)
            if r.returncode != 0:
                say('mirror', 'FAIL', '%s failed: %s' % (' '.join(c[:2]), r.stderr.decode('utf-8', 'replace')[:200]))
                return False
        pr = must('repos/%s/pulls' % repo, 'mirror', 'POST', dict(title=m['title'], head=m['branch'], base='main',
                  body='Copied byte for byte from patch-factory %s by %s. Owner pre-approved, 10 Oct 2026.' % (merge_sha[:12], SELF.name)))
        say('mirror', 'OK', '%s: opened #%d' % (repo, pr['number']))
    if not pr.get('merged_at'):
        head = pr['head']['sha']
        start = time.time()
        end = start + WAIT
        while True:
            runs = must('repos/%s/commits/%s/check-runs?per_page=100' % (repo, head), 'mirror').get('check_runs', [])
            if not runs and time.time() > start + int(os.environ.get('PF_MIRROR_QUIET', '600')):
                break  # that repository runs no checks on this pull request
            if runs and all(c.get('status') == 'completed' for c in runs):
                bad = [c['name'] for c in runs if c.get('conclusion') not in ('success', 'skipped', 'neutral')]
                if bad:
                    say('mirror', 'FAIL', '%s #%d: %s did not pass; not merged' % (repo, pr['number'], ', '.join(bad)))
                    return False
                break
            if time.time() > end:
                say('mirror', 'FAIL', '%s #%d: checks not finished after %d s; not merged' % (repo, pr['number'], WAIT))
                return False
            time.sleep(POLL)
        out = must('repos/%s/pulls/%d/merge' % (repo, pr['number']), 'mirror', 'PUT', dict(merge_method='merge', sha=head))
        if not out.get('merged'):
            say('mirror', 'FAIL', '%s #%d: merge refused' % (repo, pr['number']))
            return False
        say('mirror', 'OK', '%s #%d merged' % (repo, pr['number']))
    mark('mirror', merge_sha)
    return True


def t1(merge_sha):
    if already('t1', merge_sha):
        return True
    if not RUN_T1 or os.environ.get('PF_T1') == 'skip':
        say('t1', 'SKIP', 'all-flows test not run here')
        return True
    script = CLONE / 'docs/review/controllers/pf-t1.py'
    env = dict(os.environ, PF_MAIN=merge_sha)
    with open(LOGS / 'pf-t1.out', 'wb') as out:
        code = subprocess.run([sys.executable, str(script)], cwd=CLONE, env=env, stdout=out, stderr=subprocess.STDOUT).returncode
    lines = (LOGS / 'pf-t1.out').read_bytes().decode('utf-8', 'replace').splitlines()
    result = [l for l in lines if l.startswith('RESULT ')]
    R['t1'] = dict(code=code, result=(result or ['no RESULT line'])[-1], findings=[l for l in lines if l.startswith('FINDING ')][:30])
    if code == 0:
        mark('t1', merge_sha)
    say('t1', 'OK' if code == 0 else 'FAIL', R['t1']['result'])
    return code == 0


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
    print('RESULT OK. Logs: %s (RESULT.json, cleanup files, smoke logs, pf-t1.out). Zip and upload that folder with the pf-t1 logs folder. Clone removed; script %s.'
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
    cleaned = previewed and cleanup(R['merge'])
    mirrored = mirror(R['merge'])
    tested = t1(R['merge'])
    return finish(deployed and previewed and cleaned and mirrored and tested)


if __name__ == '__main__':
    sys.exit(main())
