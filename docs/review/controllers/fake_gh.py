#!/usr/bin/env python3
"""Fake `gh` for rehearsing a packet controller (see README.md). State lives in $FAKE_STATE.

Covers what packet.tmpl.py and src/etc/cleanup.py call: auth, branches, commits, pulls, merge,
check runs, Manual Patch dispatch/runs/jobs/logs, issues, deployments and their statuses,
releases. Knobs in the state file: checks{name: conclusion}, extra_checks[], smoke{app:
conclusion}, smoke_log{app: line}, issues{n: state}, pages_state, main, license{repo: spdx},
flows{workflow file: conclusion}, pulls[] (a seeded open pull request follows its branch). W13: provider dispatch input and run names (display_title),
cleanup apply calls, and the pf-t1 flows (any workflow file, status.json, targets.json).
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
M = 'repos/govinda-rajulu/openskip/'  # W13 mirror phase: its own pulls, origin and checks
if a[:1] == ['api'] and any(x.startswith(M) for x in a):
    mo = st['mirror_origin']; ms = st.setdefault('mirror', {'pulls': []})
    mg = lambda *x: sp.run(['git', '-C', mo] + list(x), capture_output=True, text=True).stdout.strip()
    mm, mp = (a[2], a[3]) if a[1] == '-X' else ('GET', a[1])
    mf = dict(x.split('=', 1) for i, x in enumerate(a) if i and a[i - 1] in ('-f', '-F'))
    if mp.startswith(M + 'pulls?state=all'): out(ms['pulls'])
    if mp == M + 'pulls' and mm == 'POST':
        pr = {'number': 901, 'head': {'sha': mg('rev-parse', 'refs/heads/' + mf['head']), 'ref': mf['head']}, 'merged_at': None, 'html_url': 'm'}
        ms['pulls'].append(pr); out(pr)
    if '/check-runs' in mp:
        out({'check_runs': [{'name': n, 'status': 'completed', 'conclusion': c, 'html_url': 'm'} for n, c in st.get('mirror_checks', {'Validate': 'success'}).items()]})
    if mp.startswith(M + 'pulls/901/merge') and mm == 'PUT':
        pr = ms['pulls'][0]
        if mf.get('sha') != pr['head']['sha']: fail('HTTP 409 head changed')
        mg('update-ref', 'refs/heads/main', pr['head']['sha']); pr['merged_at'] = 'now'; pr['merge_commit_sha'] = pr['head']['sha']
        out({'merged': True, 'sha': pr['head']['sha']})
    if mp.startswith(M + 'pulls/901'): out(ms['pulls'][0])
    if mp.startswith(M + 'branches/main'): out({'commit': {'sha': mg('rev-parse', 'refs/heads/main')}})
    fail('fake gh mirror: unhandled %s %s' % (mm, mp))
if a[:2] == ['auth', 'status']: save(); sys.exit(0)
if a[:2] == ['workflow', 'run']:
    ref = a[a.index('--ref') + 1]; wf = a[2]
    tgt = ([x.split('=', 1)[1] for x in a if x.startswith('target=')] + [''])[0]
    prov = ([x.split('=', 1)[1] for x in a if x.startswith('provider=')] + [''])[0]
    targets = ([x.split('=', 1)[1] for x in a if x.startswith('targets=')] + [''])[0]
    title = ('Manual %s%s / publish=false' % (tgt, ' / ' + prov if prov else '')) if wf == 'manual-patch.yml' else \
        ('Batch %s / publish=false' % targets) if wf == 'batch-patch.yml' else wf
    st['runs'].append({'id': 800000 + len(st['runs']), 'wf': wf, 'target': tgt or targets, 'provider': prov, 'display_title': title,
                       'head_branch': ref, 'head_sha': git('rev-parse', 'refs/heads/' + ref), 'created_at': '2099-01-01T00:00:00Z',
                       'updated_at': '2099-01-01T00:00:01Z', 'status': 'queued', 'conclusion': None, 'polls': 0, 'html_url': 'u'})
    save(); sys.exit(0)
if a[:2] == ['run', 'view']:
    r = [x for x in st['runs'] if str(x['id']) == a[2]][0]
    key = r['target'] + ('/' + r['provider'] if r.get('provider') else '')
    line = st.get('smoke_log', {}).get(key, 'COVERAGE p: app 2.0 covers 3 of 3 chosen patches; newest 2.0 covers 3')
    won = st.get('smoke_winner', {}).get(key, r.get('provider') or 'p')
    for t in r['target'].split(','):
        job = 'Patch ' + t if r.get('wf') == 'manual-patch.yml' else 'build (%s) / Patch %s' % (t, t)
        print('%s\tPatch apk\t2026-10-10T00:00:00.1Z %s' % (job, line))
        print('%s\tPatch apk\t2026-10-10T00:00:00.2Z ATTEMPTS_OK %s: attempt 1 of 1, winner %s' % (job, t, won))
    save(); sys.exit(0)
assert a[0] == 'api', a
while len(a) > 2 and a[1] == '-H': a = [a[0]] + a[3:]
m, p = (a[2], a[3]) if a[1] == '-X' else ('GET', a[1])
f = {}
for i, x in enumerate(a):
    if x in ('-f', '-F'): k, v = a[i + 1].split('=', 1); f[k] = v
for pr in st['pulls']:  # like GitHub: an open pull request follows its branch (state seeds may name a prior head)
    if not pr.get('merged_at') and pr.get('head', {}).get('ref'):
        pr['head']['sha'] = git('rev-parse', 'refs/heads/' + pr['head']['ref']) or pr['head']['sha']
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
    git('update-ref', 'refs/heads/main', c); st['main'] = c; pr['merged_at'] = 'now'; pr['merge_commit_sha'] = c; pr['state'] = 'closed'
    out({'merged': True, 'sha': c})
if p.startswith(R + 'pulls/%d' % NUM): out(st['pulls'][0])
if '/check-runs' in p:
    names = ['Validate targets and scripts', 'Advisory council (comments only)'] + st.get('extra_checks', [])
    out({'check_runs': [{'name': n, 'status': 'completed', 'conclusion': st.get('checks', {}).get(n, 'success'), 'html_url': 'u/' + n} for n in names]})
if p.startswith('repos/SysAdminDoc/') and p.endswith('/license'):
    out({'license': {'spdx_id': st.get('license', {}).get(p.split('/')[2], 'GPL-3.0')}})
if m in ('DELETE',) or (m == 'POST' and '/statuses' in p): out({})
if '/contents/src/targets.json' in p:
    print(json.dumps([{'id': 'adguard', 'enabled': True}, {'id': 'instagram', 'enabled': True}])); save(); sys.exit(0)
if '/contents/status.json' in p:
    print(json.dumps({'generated_at': 'now', 'headline': {}, 'issues': []})); save(); sys.exit(0)
if 'status.yml/runs' in p:
    out({'workflow_runs': [{'created_at': '2099-01-01T00:00:02Z', 'status': 'completed', 'conclusion': 'success'}]})
if '/actions/workflows/' in p and '/runs' in p and 'manual-patch.yml' not in p:
    wf = p.split('/actions/workflows/')[1].split('/')[0]
    rs = [r for r in st['runs'] if r.get('wf') == wf]
    for r in rs:
        r['polls'] += 1
        if r['polls'] > 1: r['status'] = 'completed'; r['conclusion'] = st.get('flows', {}).get(wf, 'success')
    out({'workflow_runs': list(reversed(rs))})
if 'manual-patch.yml/runs' in p:
    rs = [r for r in st['runs'] if 'head_sha=' + r['head_sha'] in p and r.get('wf') == 'manual-patch.yml']
    for r in rs:
        r['polls'] += 1
        key = r['target'] + ('/' + r['provider'] if r.get('provider') else '')
        if r['polls'] > 2: r['status'] = 'completed'; r['conclusion'] = st.get('smoke', {}).get(key, 'success')
    out({'workflow_runs': list(reversed(rs))})
if '/actions/runs/' in p and '/jobs' in p:
    rid = int(p.split('/runs/')[1].split('/')[0]); r = [x for x in st['runs'] if x['id'] == rid][0]
    out({'jobs': [{'name': 'build (%s) / Patch %s' % (t, t), 'conclusion': st.get('smoke', {}).get(t, 'success'), 'html_url': 'u', 'steps': []}
                  for t in r['target'].split(',') if t] if r.get('wf') != 'manual-patch.yml' else [{'name': 'Patch ' + r['target'], 'steps': []}]})
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
if p.startswith(R + 'pulls?state=open'): out([x for x in st['pulls'] if not x.get('merged_at') and ('head=' not in p or p.split('head=')[1].split('&')[0].endswith(':' + x['head']['ref']))])
if p.startswith(R + 'compare/'): print('behind'); save(); sys.exit(0)
fail('fake gh: unhandled %s %s' % (m, p))
