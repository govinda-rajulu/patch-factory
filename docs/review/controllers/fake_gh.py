#!/usr/bin/env python3
"""Fake `gh` for rehearsing a packet controller (see README.md). State lives in $FAKE_STATE.

Covers what packet.tmpl.py and src/etc/cleanup.py call: auth, branches, commits, pulls, merge,
check runs, Manual Patch dispatch/runs/jobs/logs, issues, deployments and their statuses,
releases. Knobs in the state file: checks{name: conclusion}, extra_checks[], smoke{app:
conclusion}, smoke_log{app: line}, issues{n: state}, pages_state, main.
"""
import json, os, sys, pathlib, subprocess as sp
S = pathlib.Path(os.environ['FAKE_STATE'])
st = json.loads(S.read_text())
a = sys.argv[1:]
st.setdefault('calls', []).append(a)
NUM = 900


def save(): S.write_text(json.dumps(st))
def out(x): print(json.dumps(x)); save(); sys.exit(0)
def fail(m): save(); print(m, file=sys.stderr); sys.exit(1)
def git(*x): return sp.run(['git', '-C', st['origin']] + list(x), capture_output=True, text=True).stdout.strip()


R = 'repos/govinda-rajulu/patch-factory/'
if a[:2] == ['auth', 'status']: save(); sys.exit(0)
if a[:2] == ['workflow', 'run']:
    ref = a[a.index('--ref') + 1]; tgt = [x.split('=', 1)[1] for x in a if x.startswith('target=')][0]
    st['runs'].append({'id': 800000 + len(st['runs']), 'target': tgt, 'head_branch': ref, 'head_sha': git('rev-parse', 'refs/heads/' + ref),
                       'status': 'queued', 'conclusion': None, 'polls': 0, 'html_url': 'u'})
    save(); sys.exit(0)
if a[:2] == ['run', 'view']:
    r = [x for x in st['runs'] if str(x['id']) == a[2]][0]
    line = st.get('smoke_log', {}).get(r['target'], 'COVERAGE p: app 2.0 covers 3 of 3 chosen patches; newest 2.0 covers 3')
    print('Patch %s\tPatch apk\t2026-10-10T00:00:00.1Z %s' % (r['target'], line)); save(); sys.exit(0)
assert a[0] == 'api', a
m, p = (a[2], a[3]) if a[1] == '-X' else ('GET', a[1])
f = {}
for i, x in enumerate(a):
    if x in ('-f', '-F'): k, v = a[i + 1].split('=', 1); f[k] = v
if p.startswith(R + 'branches/main'): out({'commit': {'sha': st['main']}})
if p.startswith(R + 'git/commits/'): out({'tree': {'sha': git('rev-parse', p.split('/')[-1] + '^{tree}')}})
if p.startswith(R + 'pulls?state=all'): out(st['pulls'])
if p == R + 'pulls' and m == 'POST':
    pr = {'number': NUM, 'head': {'sha': git('rev-parse', 'refs/heads/' + f['head']), 'ref': f['head']}, 'merged_at': None, 'html_url': 'u', 'state': 'open'}
    st['pulls'].append(pr); out(pr)
if p.startswith(R + 'pulls/%d/merge' % NUM) and m == 'PUT':
    pr = st['pulls'][0]
    if f.get('sha') != pr['head']['sha']: fail('HTTP 409 head changed')
    env = dict(os.environ, GIT_AUTHOR_NAME='g', GIT_AUTHOR_EMAIL='g@x', GIT_COMMITTER_NAME='g', GIT_COMMITTER_EMAIL='g@x')
    tree = st.get('merge_tree') or pr['head']['sha'] + '^{tree}'
    c = sp.run(['git', '-C', st['origin'], 'commit-tree', tree, '-p', st['main'], '-p', pr['head']['sha'], '-m', 'Merge'],
               env=env, capture_output=True, text=True).stdout.strip()
    git('update-ref', 'refs/heads/main', c); st['main'] = c; pr['merged_at'] = 'now'; pr['merge_commit_sha'] = c
    out({'merged': True, 'sha': c})
if p.startswith(R + 'pulls/%d' % NUM): out(st['pulls'][0])
if '/check-runs' in p:
    names = ['Validate targets and scripts', 'Advisory council (comments only)'] + st.get('extra_checks', [])
    out({'check_runs': [{'name': n, 'status': 'completed', 'conclusion': st.get('checks', {}).get(n, 'success'), 'html_url': 'u/' + n} for n in names]})
if 'manual-patch.yml/runs' in p:
    rs = [r for r in st['runs'] if 'head_sha=' + r['head_sha'] in p]
    for r in rs:
        r['polls'] += 1
        if r['polls'] > 2: r['status'] = 'completed'; r['conclusion'] = st.get('smoke', {}).get(r['target'], 'success')
    out({'workflow_runs': list(reversed(rs))})
if '/actions/runs/' in p and '/jobs' in p:
    rid = int(p.split('/runs/')[1].split('/')[0]); r = [x for x in st['runs'] if x['id'] == rid][0]
    out({'jobs': [{'name': 'Patch ' + r['target'], 'steps': []}]})
if p.startswith(R + 'issues/'):
    n = p[len(R + 'issues/'):].split('/')[0].split('?')[0]
    iss = st.setdefault('issues', {})
    if '/comments' in p and m == 'GET': out(st.setdefault('comments', {}).get(n, []))
    if '/comments' in p and m == 'POST': st.setdefault('comments', {}).setdefault(n, []).append({'body': f['body']}); out({})
    if m == 'GET': out({'state': iss.get(n, 'open')})
    if m == 'PATCH': iss[n] = f['state']; out({'state': f['state']})
if p.startswith(R + 'deployments') and 'sha=' in p:
    sha = p.split('sha=')[1].split('&')[0]
    st['pages_polls'] = st.get('pages_polls', 0) + 1
    out([{'id': 7000}] if sha == st['main'] and st['pages_polls'] > 1 and st.get('pages_state') != 'never' else [])
if p.startswith(R + 'deployments/7000/statuses'): out([{'state': st.get('pages_state', 'success')}])
if p.startswith(R + 'releases'): out([{'id': 1, 'tag_name': 'adguard-v1.0-b20260901', 'published_at': '2026-09-01T00:00:00Z', 'assets': []}] if 'page=1' in p else [])
if p.startswith(R + 'deployments'): out([{'id': 9000 + i, 'environment': 'github-pages', 'created_at': '2026-10-0%dT00:00:00Z' % i, 'sha': 'a' * 40} for i in range(1, 8)] if 'page=1' in p else [])
if p.startswith(R + 'branches'):
    rows = git('for-each-ref', '--format=%(refname:short) %(objectname)', 'refs/heads').split('\n')
    out([{'name': x.split()[0], 'commit': {'sha': x.split()[1]}} for x in rows if x] if 'page=1' in p else [])
if p.startswith(R + 'pulls?state=open'): out([])
if p.startswith(R + 'compare/'): print('behind'); save(); sys.exit(0)
fail('fake gh: unhandled %s %s' % (m, p))
