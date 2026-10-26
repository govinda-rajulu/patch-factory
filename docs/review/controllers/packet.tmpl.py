#!/usr/bin/env python3
"""Packet controller for govinda-rajulu/patch-factory (generic template since 10 Oct 2026).

Copy this file, fill the CONFIG block (the build step fills the TREE and BUNDLE placeholders),
name the result pf-<packet>-<first 8 of its sha256>.py and hand it over with an if/then
launcher that checks bytes and sha256. How-to: docs/review/controllers/README.md.

Runs on the owner box. Every phase reads state first, so a rerun skips finished work and
never pushes, merges or dispatches twice. One side effect per phase, each with its own
result line. Phases:
  gate      gh logged in; live main is BASE (or the packet is already merged). W15e: main may
            be past BASE by bot commits only; the clone proves it (see drift_tree)
  clone     fresh stamped clone; the packet tree from the embedded bundle, checked by tree id,
            committed on BASE with a fixed author and date (same commit id on a rerun)
  push      new branch BRANCH (only if absent; a different head there stops). With PARENT set
            (a fix on top of a pushed packet), BRANCH at PARENT is fast-forwarded instead
  pr        open the pull request (only if none); after a fast-forward, wait until the open
            pull request from BRANCH shows the new head
  validate  wait for CHECKS on the packet head (and OPTIONAL checks when they appear);
            any that fails stops before merge
  smoke     one nonpublishing Manual Patch per entry in SMOKE on BRANCH ("app", or
            "app/provider" to build one provider with its own pins), all dispatched at once,
            longest app first, then watched together (W15c); each must work and print
            a COVERAGE line (not COVERAGE_UNAVAILABLE; an any-version provider prints its "any
            app version" line and PATCHES_ALL_OFFERED instead), or nothing merges. Entries also in
            SMOKE_ADVISORY (fallback providers) are recorded as NOTE when they fail, never
            blocking: a broken fallback breaks nothing that works today
  merge     merge commit guarded by the head sha; the merge tree must be the packet tree
  close     for each issue or pull request in CLOSE: one marked comment, then close
  pages     wait until GitHub Pages has deployed the merge, so the cleanup preview below
            does not go stale a minute later (W12 lesson L049)
  preview   cleanup.py preview; writes the apply line
  cleanup   (W13) when CLEANUP_APPLY: applies that exact preview at once (the owner's launcher
            is the owner's command; PF_CLEANUP=keep skips it), receipt in the logs
  t1        (W13) when RUN_T1: docs/review/controllers/pf-t1.py, the all-flows test, on the
            merge; its own RESULT line and logs, reported here. W15f: PUBLISH_ALL makes its
            batch publish every enabled app and moves it before preview and cleanup
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
SMOKE_KEEP_GOING = ()  # (W16j) SMOKE entries built with keep_going: every failing patch is listed (PATCH_FAILED); always advisory
CLOSE = ()          # (issue number, closing comment) pairs, done after the merge
PRECHECKS = ()      # (api path, field, expected value, why) read in gate; a mismatch stops
CLEANUP_APPLY = False  # apply the cleanup preview at once (PF_CLEANUP=keep skips)
RUN_T1 = False      # run docs/review/controllers/pf-t1.py on the merge at the end
PUBLISH_ALL = False  # (W15f) T1's batch publishes every enabled app, and T1 runs before the cleanup
PUBLISH_APPS = ()   # (W16c) T1 publishes only these apps after its no-publish batch, and runs before the cleanup
PUBLISH_DISPATCH = ()  # (W16k) after the cleanup, dispatch ONE publishing Batch Patch on main for these apps and
                       # exit without waiting: W16j's controller died waiting (Cloud Shell idle timeout)
WATCH_DISPATCH = ()  # (W16n) workflow files dispatched once on main after the cleanup, not waited for
                     # (a green run closes its failing issue through Notify)
DELETE_BRANCHES = ()  # (W16k) merged branches deleted after the merge ('packet/w16j', BRANCH); a miss is a NOTE
SMOKES_PER_APP = 2  # (W16k) Manual Patch keeps one running and one pending run per app; a third is cancelled
TIDY = False        # (W14) src/etc/release_tidy.py on the merge: preview, then apply with a backup in the logs
MIRROR = None       # (W13) dict(repo, files, manifest, anchor, branch, title[, replaces]): copy files from the
                    # merged tree into another repository of the owner by ITS OWN pull request
PAGES_WAIT = int(os.environ.get('PF_PAGES_WAIT', '900'))
BUNDLE = '@@BUNDLE@@'
# -------------------------------------------------------------------------------------------
# W16n owner request: RESULT.json says who wrote the controller (owner, 26 Oct: no banner line on every run).
BUILT_BY = 'ClickUp Brain on Claude (engineering) for Govindarajulu K (owner)'
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
R = {'script': SELF.name, 'built_by': BUILT_BY, 'stamp': STAMP, 'base': BASE, 'tree': TREE, 'phases': [], 'result': 'RUNNING'}


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
    per = {}
    for t in SMOKE:
        per[t.split('/', 1)[0]] = per.get(t.split('/', 1)[0], 0) + 1
    over = sorted(a for a, n in per.items() if n > SMOKES_PER_APP)
    if over:
        stop('gate', 'more than %d smokes for %s: the Manual Patch queue cancels the third (W16j Instagram oxbow). '
             'Nothing pushed.' % (SMOKES_PER_APP, ', '.join(over)))
    code, out, err = run([GH, 'auth', 'status'], timeout=60)
    if code != 0:
        stop('gate', 'gh is not logged in: ' + (err or out).decode('utf-8', 'replace').strip()[:200])
    main = main_sha('gate')
    pr = find_pr('gate')
    merged = bool(pr and pr.get('merged_at'))
    R.update(main_at_start=main, pr=pr and pr['number'], merged_at_start=merged)
    if main != BASE and not merged:
        # W15e (L071): bot commits (Selection, Community, Provider watch) land on main every few
        # hours; a controller that stops on each one keeps the owner rebuilding. The clone below
        # proves the drift is bot-only and touches no packet file, or stops with MAIN_MOVED.
        say('gate', 'NOTE', 'main %s is past the base %s; the clone checks it moved by bot commits only' % (main[:12], BASE[:12]))
    if not merged:
        bt = (must('repos/%s/git/commits/%s' % (REPO, BASE), 'gate').get('tree') or {}).get('sha')
        if bt != BASE_TREE:
            stop('gate', 'base %s has tree %s, not the tree %s this packet was built on. Nothing changed.' % (BASE[:12], (bt or '')[:12], BASE_TREE[:12]))
    # W15b: prechecks describe the world before the merge (an open #188 the packet closes); a rerun
    # after the merge skips them, or it would stop on the very change the packet made.
    for path, field, want, why in (PRECHECKS if not merged else ()):
        got = must(path, 'gate')
        for k in field.split('.'):
            got = (got or {}).get(k) if isinstance(got, dict) else None
        if got != want:
            stop('gate', 'PRECHECK %s: %s is %r, the packet says %r (%s). Nothing changed.' % (path, field, got, want, why))
        say('gate', 'OK', 'precheck %s %s = %r' % (path, field, got))
    say('gate', 'OK', 'main %s, %s %s' % (main[:12], PACKET, 'already merged' if merged else 'not merged yet'))
    return pr, merged


BOT_MAIL = '41898282+github-actions[bot]@users.noreply.github.com'
MERGER_MAIL = 'noreply@github.com'  # W15f: GitHub commits the merges 11. Rule merge makes (author: the bot)


def git_out(args, phase, env=None):
    r = subprocess.run(['git'] + args, cwd=CLONE, capture_output=True, env=env, timeout=600)
    if r.returncode != 0:
        stop(phase, 'git %s failed: %s' % (' '.join(args[:2]), r.stderr.decode('utf-8', 'replace')[:200]))
    return r.stdout.decode('utf-8', 'replace')


def drift_tree(main, phase):
    """W15e (L071): the tree a merge into `main` must have. TREE when main is BASE. When main is
    past BASE, every commit after BASE must be authored by the Actions bot and committed by it, or
    (W15f, L072) be a merge GitHub committed for the bot (11. Rule merge), and none may touch a
    path the packet changes; the answer is then TREE
    with those bot paths taken from main. Anything else stops with MAIN_MOVED (nothing merged)."""
    if main == BASE:
        return TREE
    git_out(['fetch', '-q', 'origin', '+refs/heads/main:refs/pf/main'], phase)
    if subprocess.run(['git', 'cat-file', '-e', main + '^{commit}'], cwd=CLONE, capture_output=True).returncode != 0:
        stop(phase, 'MAIN_MOVED: main %s is not in the fetched history (force-pushed?). Nothing merged.' % main[:12])
    if subprocess.run(['git', 'merge-base', '--is-ancestor', BASE, main], cwd=CLONE, capture_output=True).returncode != 0:
        stop(phase, 'MAIN_MOVED: main %s does not contain the base %s. Nothing merged.' % (main[:12], BASE[:12]))
    rows = [l.split(' ') for l in git_out(['log', '--format=%H %ae %ce %P', BASE + '..' + main], phase).splitlines() if l.strip()]
    human = [r[0][:12] for r in rows if r[1] != BOT_MAIL or not (r[2] == BOT_MAIL and len(r) == 4 or r[2] == MERGER_MAIL)]
    if human:
        stop(phase, 'MAIN_MOVED: main %s has %d commit(s) after the base that are not bot commits (%s). Nothing merged.'
             % (main[:12], len(human), ', '.join(human[:5])))
    moved = [x for x in git_out(['diff', '--name-only', '--no-renames', '-z', BASE, main], phase).split('\0') if x]
    mine = set(x for x in git_out(['diff', '--name-only', '--no-renames', '-z', BASE_TREE, TREE], phase).split('\0') if x)
    both = sorted(set(moved) & mine)
    if both:
        stop(phase, 'MAIN_MOVED: bot commits after the base change %d file(s) this packet changes too (%s). Nothing merged.'
             % (len(both), ', '.join(both[:5])))
    idx = WORK / ('pf-%s-%s.index' % (PACKET, STAMP))
    env = dict(os.environ, GIT_INDEX_FILE=str(idx))
    git_out(['read-tree', TREE], phase, env)
    for path in moved:
        row = git_out(['ls-tree', '-z', main, '--', path], phase).strip('\0')
        if row:
            meta = row.split('\t', 1)[0].split()
            git_out(['update-index', '--add', '--cacheinfo', '%s,%s,%s' % (meta[0], meta[2], path)], phase, env)
        else:
            git_out(['update-index', '--force-remove', '--', path], phase, env)
    tree = git_out(['write-tree'], phase, env).strip()
    idx.unlink()
    R.setdefault('drift', {})[main] = dict(commits=len(rows), files=len(moved), tree=tree)
    say(phase, 'OK', 'main %s is %d bot commit(s) past the base, %d file(s), none the packet changes; merge tree must be %s'
        % (main[:12], len(rows), len(moved), tree[:12]))
    return tree


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
    if R.get('main_at_start') != BASE and not R.get('merged_at_start'):
        drift_tree(R['main_at_start'], 'clone')


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
    drift_tree(main_sha('merge'), 'merge')  # W15e: bot-only drift merges; anything else stops here
    out = must('repos/%s/pulls/%d/merge' % (REPO, pr['number']), 'merge', 'PUT', dict(merge_method='merge', sha=HEAD))
    sha = out.get('sha') or ''
    if not out.get('merged') or len(sha) != 40:
        stop('merge', 'merge answer was not a merge: %s' % json.dumps(out)[:200])
    say('merge', 'OK', 'merged #%d as %s' % (pr['number'], sha[:12]))
    return tree_check(sha)


def tree_check(sha):
    t = (must('repos/%s/git/commits/%s' % (REPO, sha), 'merge').get('tree') or {}).get('sha')
    if t == TREE:
        say('merge', 'OK', 'merge tree is the packet tree %s' % TREE[:12])
        return sha
    # W15e: a merge into a main that bot commits moved has the packet tree plus their files.
    git_out(['fetch', '-q', 'origin', '+refs/heads/main:refs/pf/main'], 'merge')
    parents = git_out(['rev-list', '--parents', '-n', '1', sha], 'merge').split()
    if len(parents) != 3 or parents[2] != HEAD:
        stop('merge', 'merge %s has tree %s, not the packet tree %s, and is not a merge of the packet head' % (sha[:12], (t or '')[:12], TREE[:12]))
    want = drift_tree(parents[1], 'merge')
    if t != want:
        stop('merge', 'merge %s has tree %s, not %s (the packet tree with the bot files of %s)' % (sha[:12], (t or '')[:12], want[:12], parents[1][:12]))
    say('merge', 'OK', 'merge tree %s is the packet tree plus the bot files of %s' % (t[:12], parents[1][:12]))
    return sha


def title(entry):
    app, _, provider = entry.partition('/')
    return 'Manual %s%s / publish=false%s' % (app, (' / ' + provider) if provider else '',
                                              ' / keep-going' if entry in SMOKE_KEEP_GOING else '')


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


def smoke_order():
    """W15c (owner, 21 Oct 2026): dispatch every smoke build at once, longest app first
    (src/etc/build-minutes.json in the packet clone; an app not listed counts as long)."""
    try:
        table = json.loads((CLONE / 'src/etc/build-minutes.json').read_text(encoding='utf-8')).get('minutes') or {}
    except (OSError, ValueError, AttributeError):
        table = {}
    rank = lambda t: -float(table.get(t.partition('/')[0], float('inf')) if isinstance(table, dict) else float('inf'))
    return sorted(SMOKE, key=lambda t: (rank(t), SMOKE.index(t)))


def smoke():
    """Nonpublishing builds on the packet branch prove the new resolver in CI before the merge.
    All are dispatched first and watched together; two builds of one app still queue behind
    each other (the patch-<app> concurrency group), so the wait covers that too."""
    R['smoke'] = {}
    have = smoke_runs()
    for t in smoke_order():
        if have.get(t):
            say('smoke', 'SKIP', '%s: run %s already exists on %s' % (t, have[t]['id'], HEAD[:12]))
            continue
        app, _, provider = t.partition('/')
        cmd = [GH, 'workflow', 'run', 'manual-patch.yml', '--repo', REPO, '--ref', BRANCH, '-f', 'target=' + app, '-f', 'publish=false']
        cmd += ['-f', 'keep_going=true'] if t in SMOKE_KEEP_GOING else []
        code, out, err = run(cmd + (['-f', 'provider=' + provider] if provider else []), timeout=120)
        if code != 0:
            stop('smoke', '%s: dispatch failed: %s. Nothing merged.' % (t, (err or out).decode('utf-8', 'replace')[:200]))
        say('smoke', 'OK', '%s: dispatched a nonpublishing Manual Patch on %s' % (t, BRANCH))
    end = time.time() + BUILD_WAIT
    while True:
        runs = smoke_runs()
        if all(runs.get(t) and runs[t].get('status') == 'completed' for t in SMOKE) or time.time() > end:
            break
        time.sleep(POLL)
    for t in SMOKE:
        r = runs.get(t)
        soft = t in SMOKE_ADVISORY or t in SMOKE_KEEP_GOING
        if not (r and r.get('status') == 'completed'):
            if soft:
                R['smoke'][t] = dict(run=(r or {}).get('id'), conclusion='unfinished', advisory=True)
                say('smoke', 'NOTE', '%s: advisory, no finished run after %d s (not blocking)' % (t, BUILD_WAIT))
                continue
            stop('smoke', '%s: no finished run after %d s. Nothing merged.' % (t, BUILD_WAIT))
        log = LOGS / ('smoke-%s-%s.log' % (t.replace('/', '-'), r['id']))
        run([GH, 'run', 'view', str(r['id']), '--repo', REPO, '--log'], timeout=300, out=log)
        text = log.read_bytes().decode('utf-8', 'replace') if log.exists() else ''
        cov = [l.split('Z ', 1)[-1].strip() for l in text.splitlines() if 'COVERAGE ' in l and ' covers ' in l and 'echo' not in l]
        # An any-version provider has no version list, so no COVERAGE line (Amazon Music, W13
        # smoke 2, L053): its resolver line stands in, with every chosen patch offered.
        anyv = [l.split('Z ', 1)[-1].strip() for l in text.splitlines() if ": any app version, the store's newest" in l and 'echo' not in l]
        offered = [l for l in text.splitlines() if 'PATCHES_ALL_OFFERED' in l and 'print(' not in l]
        if not cov and anyv and offered:
            cov = ['ANY_VERSION ' + anyv[-1].lstrip('- ')]
        lost = [l.split('Z ', 1)[-1].strip() for l in text.splitlines() if 'COVERAGE_LOST ' in l and 'echo' not in l]
        doubt = [l.split('Z ', 1)[-1].strip() for l in text.splitlines() if 'COVERAGE_UNAVAILABLE ' in l and 'echo' not in l and 'sed ' not in l]
        app, _, provider = t.partition('/')
        won = [l.split('Z ', 1)[-1].strip() for l in text.splitlines() if 'ATTEMPTS_OK ' in l and 'echo' not in l]
        dropped = [l.split('Z ', 1)[-1].strip() for l in text.splitlines() if 'PATCH_DROPPED ' in l and 'echo' not in l and 'print(' not in l]
        failed = [l.split('Z ', 1)[-1].strip()[:300] for l in text.splitlines() if 'ATTEMPT_FAILED ' in l and 'echo' not in l and 'print(' not in l]
        patch_failed = sorted({l.split('PATCH_FAILED ', 1)[1].strip()[:200] for l in text.splitlines()
                               if 'PATCH_FAILED ' in l and 'sed ' not in l and 'echo' not in l})
        R['smoke'][t] = dict(run=r['id'], conclusion=r.get('conclusion'), url=r.get('html_url'), coverage=cov[:4],
                             lost=lost[:20], unavailable=doubt[:4], attempts=won[-1:], dropped=dropped[:20], failed=failed[:4],
                             advisory=soft, patch_failed=patch_failed[:80], keep_going=t in SMOKE_KEEP_GOING)
        save()
        why = None
        if r.get('conclusion') != 'success':
            why = 'run %s ended %s: %s%s' % (r['id'], r.get('conclusion'), r.get('html_url'), ('; ' + failed[-1]) if failed else '')
        elif doubt or not cov:
            why = 'run %s worked but the resolver %s' % (r['id'], 'could not read the listing: ' + doubt[0] if doubt else 'printed no COVERAGE line')
        elif provider and not any((', winner %s' % provider) in w for w in won):
            why = 'run %s worked but not with provider %s (%s)' % (r['id'], provider, (won or ['no ATTEMPTS_OK line'])[-1])
        if why and patch_failed:
            why += '; failing patches (%d): %s' % (len(patch_failed), ', '.join(patch_failed[:12]))
        if why and soft:
            say('smoke', 'NOTE', '%s: advisory, %s (not blocking; the log is kept)' % (t, why))
            continue
        if why:
            stop('smoke', '%s: %s. Nothing merged; the log is kept.' % (t, why))
        say('smoke', 'OK', '%s: run %s worked; %s%s' % (t, r['id'], cov[-1], ('; dropped %d' % len(dropped)) if dropped else ''))


def delete_branches():
    """W16k (owner rule: delete merged branches): one DELETE per branch; a branch already gone is a NOTE."""
    for name in DELETE_BRANCHES:
        if name in ('main', 'status', 'gh-pages'):
            say('branches', 'NOTE', 'refusing to delete %s' % name)
            continue
        data, err = api('repos/%s/git/refs/heads/%s' % (REPO, name), 'DELETE', None, 'branches')
        if data is None:
            say('branches', 'NOTE', '%s not deleted: %s' % (name, str(err)[:160]))
        else:
            say('branches', 'OK', 'deleted branch %s' % name)
    return True


def close_issues():
    for number, text in CLOSE:
        phase = 'close'
        issue = must('repos/%s/issues/%d' % (REPO, number), phase)
        # W15c: "Closes #N" in a packet body closes N at the merge, before this phase (#188 on
        # 20 Oct closed with no comment). The comment still goes on; only the close is skipped.
        mark = '[pf-%s-close-%d]' % (PACKET, number)
        comments = must('repos/%s/issues/%d/comments?per_page=100' % (REPO, number), phase)
        if any(mark in (c.get('body') or '') for c in comments):
            say(phase, 'SKIP', 'closing comment already on #%d' % number)
        else:
            must('repos/%s/issues/%d/comments' % (REPO, number), phase, 'POST', dict(body=mark + '\n\n' + text))
            say(phase, 'OK', 'comment posted on #%d' % number)
        if issue.get('state') == 'closed':
            say(phase, 'SKIP', '#%d already closed' % number)
            continue
        if issue.get('pull_request'):
            # W15b: a pull request (Dependabot #188 applied in a packet) closes through the pulls
            # endpoint; state_reason belongs to issues only.
            must('repos/%s/pulls/%d' % (REPO, number), phase, 'PATCH', dict(state='closed'))
        else:
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
        say('cleanup', 'OK', 'not applied here; the apply line is in cleanup-apply-command.txt')
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


def tidy(merge_sha):
    """W14: strip the blocks every old release repeated (now one link to the guide). The old
    bodies go to release-tidy-backup.json in the logs before the first edit; the tool re-reads
    every release afterwards. A rerun finds nothing left to change."""
    if already('tidy', merge_sha):
        return True
    if not TIDY or os.environ.get('PF_TIDY') == 'keep':
        say('tidy', 'SKIP', 'release notes not tidied here')
        return True
    code, out, err = run([sys.executable, 'src/etc/release_tidy.py', 'preview', '--out', str(LOGS / 'release-tidy-preview.json')],
                         cwd=CLONE, timeout=900, out=LOGS / 'release-tidy-preview.txt')
    text = out.decode('utf-8', 'replace').strip()
    if code != 0 or not text.startswith('TIDY '):
        say('tidy', 'FAIL', 'preview: ' + (text or err.decode('utf-8', 'replace'))[-300:] + ' (nothing edited)')
        return False
    try:
        tidy_token = json.loads((LOGS / 'release-tidy-preview.json').read_text(encoding='utf-8'))['token']
    except (OSError, ValueError, KeyError, TypeError):
        say('tidy', 'FAIL', 'preview did not contain a release-tidy token (nothing edited)')
        return False
    code, out, err = run([sys.executable, 'src/etc/release_tidy.py', 'apply', '--token', tidy_token,
                          '--backup', str(LOGS / 'release-tidy-backup.json'),
                          '--receipt', str(LOGS / 'release-tidy-receipt.json')], cwd=CLONE, timeout=3600, out=LOGS / 'release-tidy-apply.txt')
    last = (out.decode('utf-8', 'replace').strip().splitlines() or [err.decode('utf-8', 'replace')[-300:]])[-1]
    R['tidy'] = dict(preview=text, applied=last)
    if code != 0:
        say('tidy', 'FAIL', 'apply: ' + last + ' (old bodies are in release-tidy-backup.json)')
        return False
    mark('tidy', merge_sha)
    say('tidy', 'OK', text + ' / ' + last)
    return True


def mirror(merge_sha):
    """Copy the exact merged bytes into MIRROR['repo'] by its own pull request; merge it when its
    checks pass. Refuses when a target file exists with other bytes or the manifest anchor moved.
    W14: MIRROR['replaces'] = {file: sha256 of the copy that repository holds now} allows an
    update of exactly that copy; its manifest line is then replaced in place."""
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
        repl = m.get('replaces') or {}
        for f in m['files']:
            new, old = (CLONE / f).read_bytes(), dest / f
            if old.exists() and old.read_bytes() != new and hashlib.sha256(old.read_bytes()).hexdigest() != repl.get(f):
                say('mirror', 'FAIL', '%s already has %s with other bytes; nothing pushed' % (repo, f))
                return False
            old.parent.mkdir(parents=True, exist_ok=True)
            old.write_bytes(new)
        mine = (CLONE / m['manifest']).read_bytes().decode('utf-8').splitlines()
        theirs_path = dest / m['manifest']
        theirs = theirs_path.read_bytes().decode('utf-8')
        add = [l for l in mine if any(l.startswith(f.rsplit('/', 1)[-1] + '\t') for f in m['files'])]
        need = [l for l in add if l not in theirs.splitlines()]
        rows = theirs.splitlines()
        for l in list(need):
            key = l.split('\t', 1)[0] + '\t'
            hit = [i for i, r in enumerate(rows) if r.startswith(key)]
            if hit and any(f.rsplit('/', 1)[-1] + '\t' == key for f in repl):
                rows[hit[0]] = l
                need.remove(l)
        if rows != theirs.splitlines():
            theirs = '\n'.join(rows) + '\n'
            theirs_path.write_bytes(theirs.encode('utf-8'))
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
                  body='Copied byte for byte from patch-factory %s by %s. Owner pre-approved series (10 Oct 2026).' % (merge_sha[:12], SELF.name)))
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
    env = dict(os.environ, PF_MAIN=merge_sha, PF_T1_PUBLISH='1' if PUBLISH_ALL else '',
               PF_T1_PUBLISH_APPS='' if PUBLISH_ALL else ','.join(PUBLISH_APPS))
    with open(LOGS / 'pf-t1.out', 'wb') as out:
        code = subprocess.run([sys.executable, str(script)], cwd=CLONE, env=env, stdout=out, stderr=subprocess.STDOUT).returncode
    lines = (LOGS / 'pf-t1.out').read_bytes().decode('utf-8', 'replace').splitlines()
    result = [l for l in lines if l.startswith('RESULT ')]
    R['t1'] = dict(code=code, result=(result or ['no RESULT line'])[-1], findings=[l for l in lines if l.startswith('FINDING ')][:30])
    if code == 0:
        mark('t1', merge_sha)
    say('t1', 'OK' if code == 0 else 'FAIL', R['t1']['result'])
    return code == 0


def publish_dispatch(merge_sha):
    """W16k: one publishing Batch Patch on main, dispatched and not waited for; its run link is kept."""
    if not PUBLISH_DISPATCH:
        return True
    # A rerun never publishes twice: a done file in WORK, and any publishing batch already on the merge.
    done = WORK / ('pf-%s-publish.done' % PACKET)
    if done.is_file() and done.read_text(encoding='utf-8').strip() == merge_sha:
        say('publish', 'SKIP', 'already dispatched for %s (%s)' % (merge_sha[:12], done.name))
        return True
    rows = must('repos/%s/actions/workflows/batch-patch.yml/runs?event=workflow_dispatch&branch=main&head_sha=%s&per_page=20'
                % (REPO, merge_sha), 'publish').get('workflow_runs', [])
    mine = [r for r in rows if r.get('head_sha') == merge_sha and str(r.get('display_title', '')).endswith('/ publish=true')]
    if mine:
        done.write_text(merge_sha + '\n', encoding='utf-8')
        say('publish', 'SKIP', 'a publishing batch already runs on %s: %s' % (merge_sha[:12], mine[0].get('html_url')))
        return True
    started = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    cmd = [GH, 'workflow', 'run', 'batch-patch.yml', '--repo', REPO, '--ref', 'main',
           '-f', 'targets=' + ','.join(PUBLISH_DISPATCH), '-f', 'publish=true']
    code, out, err = run(cmd, timeout=120)
    if code != 0:
        say('publish', 'FAIL', 'dispatch failed: %s' % (err or out).decode('utf-8', 'replace')[:200])
        return False
    found = None
    for _ in range(12):
        time.sleep(10)
        rows = must('repos/%s/actions/workflows/batch-patch.yml/runs?event=workflow_dispatch&branch=main&per_page=10' % REPO,
                    'publish').get('workflow_runs', [])
        rows = [r for r in rows if str(r.get('created_at', '')) >= started]
        if rows:
            found = rows[-1]
            break
    done.write_text(merge_sha + '\n', encoding='utf-8')
    R['publish_dispatch'] = dict(apps=list(PUBLISH_DISPATCH), run=found and found.get('id'), url=found and found.get('html_url'),
                                 merge=merge_sha)
    say('publish', 'OK', 'dispatched one publishing batch for %s on main (%s); not waiting, it runs in GitHub'
        % (', '.join(PUBLISH_DISPATCH), (found or {}).get('html_url') or 'run link not seen yet'))
    return True


def watch_dispatch(merge_sha):
    """W16n: dispatch each WATCH_DISPATCH workflow once on main; a rerun skips the ones already sent."""
    good = True
    for wf in WATCH_DISPATCH:
        done = WORK / ('pf-%s-watch-%s.done' % (PACKET, wf.replace('.yml', '')))
        if done.is_file() and done.read_text(encoding='utf-8').strip() == merge_sha:
            say('watch', 'SKIP', '%s already dispatched for %s' % (wf, merge_sha[:12]))
            continue
        code, out, err = run([GH, 'workflow', 'run', wf, '--repo', REPO, '--ref', 'main'], timeout=120)
        if code != 0:
            say('watch', 'FAIL', '%s dispatch failed: %s' % (wf, (err or out).decode('utf-8', 'replace')[:200]))
            good = False
            continue
        done.write_text(merge_sha + '\n', encoding='utf-8')
        R.setdefault('watch_dispatch', []).append(wf)
        say('watch', 'OK', '%s dispatched on main; not waiting, its green run closes its failing issue' % wf)
    return good


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
    delete_branches()
    deployed = pages(R['merge'])
    # W15f: with PUBLISH_ALL the fresh releases exist before the cleanup keeps the newest per app.
    early = PUBLISH_ALL or bool(PUBLISH_APPS)  # W16c: fresh releases before the cleanup, too
    tested = t1(R['merge']) if early else True
    previewed = preview()
    if deployed:
        cleaned = previewed and cleanup(R['merge'])
    else:
        # W16o round 3: no cleanup apply without the merge's own finished Pages deploy.
        say('cleanup', 'FAIL', 'not applied: the Pages deployment did not finish; the apply line is in cleanup-apply-command.txt')
        cleaned = False
    tidied = tidy(R['merge'])
    mirrored = mirror(R['merge'])
    if not early:
        tested = t1(R['merge'])
    watched = watch_dispatch(R['merge'])  # W16n
    dispatched = publish_dispatch(R['merge'])  # W16k: last, and not waited for
    return finish(deployed and previewed and cleaned and tidied and mirrored and tested and watched and dispatched)


if __name__ == '__main__':
    sys.exit(main())
