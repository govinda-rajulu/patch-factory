#!/usr/bin/env python3
"""11. Rule merge (owner, 21 Oct 2026, packet W15d): a pull request the Selection watch rule
opened merges itself only when everything around it is green. Anything else waits.

Merges only when ALL hold, read from the GitHub API on the default branch's own code:
  * opened by github-actions[bot] from an `adopt/` branch of this repository;
  * every changed file is one the adopt step writes (ALLOWED), no include-patches line is
    removed, and no exclude-patches, policy, workflow, build or target file is touched;
  * no listed name carries a paid word on an app outside paid_ok_targets (ADOPT.json);
  * GitHub reports the pull request mergeable (a conflict cannot heal: the pull request is
    closed with a note and its branch deleted, so the next Selection watch rebuilds it on main);
  * check runs on the head: "Validate targets and scripts" succeeded and nothing failed;
  * the newest "Onboarding review #N" run, started after the head commit, succeeded (W15e: or,
    when no run carries that name, the bot's "Onboarding review: PASS" comment is newer than the head);
  * every app/provider pair the body lists has its own finished, successful nonpublishing
    Manual Patch on the head (the run title names the provider unless it is the primary).
W15e: a run waits up to PF_RULE_MERGE_PATIENCE seconds while builds or checks are still running,
because runs the bot starts wake no workflow (L069); the Onboarding review also wakes it.
Waits while an unmerged packet/* branch exists (a controller gates on the exact main sha).
Merges with the head sha pinned, so a later push cannot slip in, then starts Validate and the
status page on main (a push by the workflow token starts no workflow by itself).
"""
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOT = 'github-actions[bot]'
ALLOWED = [re.compile(p) for p in (
    r'src/patches/[a-z0-9-]+/include-patches', r'docs/review/onboarding/[a-z0-9-]+\.md',
    r'docs/review/providers/[A-Za-z0-9._-]+', r'README\.md', r'CREDITS\.md', r'docs/index\.html',
    r'docs/portal\.js', r'docs/obtainium(-[a-z]+)?\.json')]
LINE = re.compile(r'^- ([a-z0-9-]+) / ([A-Za-z0-9_.-]+): `([^`]+)`', re.M)


def added_names(patch):
    """Names from added include-file lines, using the build's option syntax."""
    if not isinstance(patch, str) or not patch:
        return None
    names = []
    for line in patch.splitlines():
        if not line.startswith('+') or line.startswith('+++'):
            continue
        line = line[1:].strip()
        if not line or line.startswith('#'):
            continue
        names.append(line.split('|', 1)[0].strip())
    return names


def path_identity(path, targets):
    """Map an include file's patch directory to the body's app/provider pair."""
    match = re.fullmatch(r'src/patches/([a-z0-9-]+)/include-patches', path)
    if not match:
        return None
    patch_dir = match.group(1)
    found = []
    for target, data in targets.items():
        for bundle in (data.get('candidates') or []) + (data.get('extra_bundles') or []):
            if bundle.get('patch_dir') == patch_dir:
                found.append((target, bundle.get('name')))
    return found[0] if len(found) == 1 and found[0][1] else None


VALIDATE = 'Validate targets and scripts'


def gh_api(path, method='GET', fields=None):
    cmd = ['gh', 'api', '-X', method, path]
    for k, v in (fields or {}).items():
        cmd += ['-f', '%s=%s' % (k, v)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise ValueError('%s %s failed: %s' % (method, path, (r.stderr or '').strip()[-200:]))
    return json.loads(r.stdout or 'null')


def when(text):
    return datetime.datetime.fromisoformat(text.replace('Z', '+00:00'))


def build_title(targets, target, provider):
    """The run title selection_watch's test build gets (manual-patch.yml run-name)."""
    t = targets.get(target) or {}
    primary = ((t.get('candidates') or [{}])[0]).get('name')
    if provider == primary or provider in [b.get('name') for b in t.get('extra_bundles') or []]:
        return 'Manual %s / publish=false' % target
    return 'Manual %s / %s / publish=false' % (target, provider)


def decide(repo, pr, api, policy, targets=None):
    """('merge'|'wait'|'refuse'|'stale', why). refuse = never by this bot; wait = not yet;
    stale = conflicts with main, closed so the next Selection watch rebuilds it."""
    if targets is None:
        targets = {t['id']: t for t in json.loads((ROOT / 'src/targets.json').read_text(encoding='utf-8'))}
    n, head = pr['number'], pr['head']['sha']
    if (pr.get('user') or {}).get('login') != BOT or not pr['head']['ref'].startswith('adopt/') \
            or (pr['head'].get('repo') or {}).get('full_name') != repo:
        return 'refuse', 'not a Selection watch rule pull request'
    if (pr.get('base') or {}).get('ref') != 'main':
        return 'refuse', 'pull request base is not main'
    files = api('repos/%s/pulls/%d/files?per_page=100' % (repo, n))
    if not files or len(files) >= 100:
        return 'refuse', 'file list empty or too long to read whole'
    actual = set()
    for f in files:
        name = f['filename']
        if not any(p.fullmatch(name) for p in ALLOWED):
            return 'refuse', 'touches %s, which the adopt step never writes' % name
        if name.endswith('/include-patches'):
            if f.get('deletions') or f.get('status') != 'modified':
                return 'refuse', '%s loses or replaces a line; adopting only adds' % name
            identity = path_identity(name, targets)
            if identity is None:
                return 'refuse', 'cannot map %s to one target/provider' % name
            parsed = added_names(f.get('patch'))
            if parsed is None:
                return 'refuse', '%s has no complete patch from the files API' % name
            actual.update((identity[0], identity[1], patch) for patch in parsed if patch)
    rows = LINE.findall(pr.get('body') or '')
    if not rows:
        return 'refuse', 'the body lists no adopted names'
    listed = set(rows)
    if actual != listed:
        missing = sorted(listed - actual)
        extra = sorted(actual - listed)
        reason = []
        if missing:
            reason.append('body-only ' + repr(missing[0]))
        if extra:
            reason.append('diff-only ' + repr(extra[0]))
        return 'refuse', 'include additions do not match PR body rows: ' + '; '.join(reason)
    for target, provider, name in sorted(actual):
        low = name.lower()
        if any(w in low for w in policy['paid_words']) and target not in policy['paid_ok_targets']:
            return 'refuse', 'paid word in %s on %s (an account app): owner decides' % (name, target)
    full = api('repos/%s/pulls/%d' % (repo, n))
    if full.get('mergeable') is None:
        return 'wait', 'GitHub has not computed mergeability yet'
    if full.get('mergeable') is not True:
        return 'stale', 'GitHub reports a conflict with main'
    checks = api('repos/%s/commits/%s/check-runs?per_page=100' % (repo, head)).get('check_runs', [])
    bad = [c['name'] for c in checks if c.get('status') == 'completed'
           and c.get('conclusion') not in ('success', 'neutral', 'skipped')]
    if bad:
        return 'refuse', 'check failed: ' + ', '.join(sorted(set(bad)))
    if any(c.get('status') != 'completed' for c in checks):
        return 'wait', 'checks still running'
    if not any(c['name'] == VALIDATE and c.get('conclusion') == 'success' for c in checks):
        return 'wait', 'no successful "%s" on the head yet' % VALIDATE
    born = when(api('repos/%s/commits/%s' % (repo, head))['commit']['committer']['date'])
    reviews = [r for r in api('repos/%s/actions/workflows/onboard-review.yml/runs?per_page=50' % repo).get('workflow_runs', [])
               if r.get('display_title') == 'Onboarding review #%d' % n and when(r['created_at']) >= born]
    if reviews:
        # W16n: the newest review decides; an older run on another head cannot veto it.
        last = max(reviews, key=lambda r: r['created_at'])
        if last.get('head_sha') and last.get('head_sha') != head:
            return 'refuse', 'Onboarding review is for a different PR head'
        if last.get('status') != 'completed':
            return 'wait', 'Onboarding review still running'
        if last.get('conclusion') != 'success':
            return 'refuse', 'Onboarding review ended %s: %s' % (last.get('conclusion'), last.get('html_url'))
    else:
        # W15e (L069): runs named before the quoting fix read "Onboarding review" only.
        said = [c for c in (api('repos/%s/issues/%d/comments?per_page=100' % (repo, n)) or [])
                if (c.get('user') or {}).get('login') == BOT and '## Onboarding review:' in (c.get('body') or '')
                and when(c.get('updated_at') or c['created_at']) >= born]
        if not said:
            return 'wait', 'no Onboarding review run for #%d after the head commit' % n
        verdict = max(said, key=lambda c: c.get('updated_at') or c['created_at'])['body']
        if '## Onboarding review: PASS' not in verdict:
            return 'refuse', 'the newest Onboarding review comment is not PASS'
    runs = api('repos/%s/actions/workflows/manual-patch.yml/runs?event=workflow_dispatch&head_sha=%s&per_page=50'
               % (repo, head)).get('workflow_runs', [])
    for target, provider in sorted({(t, p) for t, p, _ in rows}):
        title = build_title(targets, target, provider)
        mine = [r for r in runs if r.get('display_title') == title]
        if not mine:
            return 'wait', 'no test build "%s" on the head yet' % title
        if any(r.get('status') != 'completed' for r in mine):
            return 'wait', 'test build "%s" still running' % title
        failed = [r for r in mine if r.get('conclusion') != 'success']
        if failed:
            return 'refuse', 'test build "%s" ended %s: %s' % (title, failed[0].get('conclusion'), failed[0].get('html_url'))
    return 'merge', '%d name(s) on %d app(s), every check and test build green' % (len(rows), len({t for t, _, _ in rows}))


MARK = '<!-- rule-merge: refused -->'


def note(repo, number, why, api):
    """One comment per refused pull request, so the owner is told once, not on every run."""
    comments = api('repos/%s/issues/%d/comments?per_page=100' % (repo, number)) or []
    if any(MARK in (c.get('body') or '') for c in comments):
        return False
    api('repos/%s/issues/%d/comments' % (repo, number), 'POST',
        {'body': '%s\n11. Rule merge will not merge this: %s.\n\nOwner: merge it yourself if the reason is fine, '
                 'or close it; the next Selection watch then opens the same names again on main.' % (MARK, why)})
    return True


RUNNING = ('still running', 'no test build', 'no successful', 'has not computed', 'no Onboarding review')


def run(repo, api=gh_api, dispatch=None, policy=None, targets=None, patience=None, sleep=None):
    patience = int(os.environ.get('PF_RULE_MERGE_PATIENCE', '0')) if patience is None else patience
    sleep = sleep or __import__('time').sleep
    waited = 0
    while True:
        merged, waiting = one_pass(repo, api, dispatch, policy, targets)
        if merged or not waiting or waited >= patience:
            return 0
        print('RULE_MERGE waiting 60 s for: %s' % '; '.join(waiting))
        sleep(60)
        waited += 60


def one_pass(repo, api=gh_api, dispatch=None, policy=None, targets=None):
    policy = policy or json.loads((ROOT / 'src/patches/ADOPT.json').read_text(encoding='utf-8'))
    dispatch = dispatch or (lambda wf: subprocess.run(['gh', 'workflow', 'run', wf, '--repo', repo, '--ref', 'main'],
                                                      capture_output=True, timeout=120).returncode)
    merged = 0
    # A packet controller gates on the exact main sha; never move main under it.
    # Merged packet branches wait for cleanup (owner F3 holds it); only an unmerged one holds main.
    held = []
    for ref in api('repos/%s/git/matching-refs/heads/packet/' % repo) or []:
        try:
            status = api('repos/%s/compare/%s...main?per_page=1' % (repo, ref['object']['sha'])).get('status')
        except ValueError:
            status = None
        if status not in ('ahead', 'identical'):
            held.append(ref['ref'].split('refs/heads/', 1)[-1])
    if held:
        print('RULE_MERGE wait: packet branch %s is not merged yet; main stays put until it is' % held[0])
        return 0, []
    waiting = []
    for pr in api('repos/%s/pulls?state=open&per_page=50' % repo):
        if not pr['head']['ref'].startswith('adopt/'):
            continue
        call, why = decide(repo, pr, api, policy, targets)
        print('%sRULE_MERGE #%d %s: %s' % ('::warning::' if call in ('refuse', 'stale') else '', pr['number'], call, why))
        if call == 'stale':
            api('repos/%s/issues/%d/comments' % (repo, pr['number']), 'POST',
                {'body': '11. Rule merge: this conflicts with main and cannot heal. Closed; the next Selection watch '
                         'rebuilds the same names on main under the rule.'})
            api('repos/%s/pulls/%d' % (repo, pr['number']), 'PATCH', {'state': 'closed'})
            api('repos/%s/git/refs/heads/%s' % (repo, pr['head']['ref']), 'DELETE')
            print('RULE_MERGE #%d closed and %s deleted; it regenerates on the next Selection watch' % (pr['number'], pr['head']['ref']))
            continue
        if call == 'refuse':
            note(repo, pr['number'], why, api)
        if call == 'wait' and any(w in why for w in RUNNING):
            waiting.append('#%d %s' % (pr['number'], why))
        if call != 'merge':
            continue
        api('repos/%s/pulls/%d/merge' % (repo, pr['number']), 'PUT',
            {'merge_method': 'merge', 'sha': pr['head']['sha'],
             'commit_title': 'Rule merge #%d: %s' % (pr['number'], pr['title'][:120])})
        merged += 1
        print('RULE_MERGE #%d merged at %s' % (pr['number'], pr['head']['sha'][:12]))
        try:
            api('repos/%s/git/refs/heads/%s' % (repo, pr['head']['ref']), 'DELETE')
        except ValueError as e:
            print('::warning::RULE_MERGE #%d merged but %s was not deleted: %s' % (pr['number'], pr['head']['ref'], e))
    if merged:
        for wf in ('validate.yml', 'status.yml'):
            if dispatch(wf) != 0:
                print('::warning::RULE_MERGE could not start %s on main; run it from the Actions tab' % wf)
    return merged, waiting


if __name__ == '__main__':
    try:
        sys.exit(run(os.environ.get('GITHUB_REPOSITORY', 'govinda-rajulu/patch-factory')))
    except ValueError as e:
        print('::error::RULE_MERGE refused: %s' % e)
        sys.exit(1)
