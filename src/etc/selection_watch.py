#!/usr/bin/env python3
"""Selection watch (packet W13, owner design 10 Oct 2026): keep every app's patch choice
current without a hand edit, and put each decision in front of the owner once.

Daily, after the Nightly watch. Phases:
  collect  read every wired provider's patch names (the provider watch reader, "-x"),
           then plan:
             * a chosen (include) name the provider no longer offers is removed from the
               selection file (exclude lists are never edited: they are safety rails); more than max(3, a quarter) of one folder's chosen
               names gone at once is NOT removed (a broken provider release): it is reported
               and the build's own lost-patch cap sends that app to its fallback provider;
             * the provider's name baseline (docs/review/providers) is re-seeded, so the
               Provider watch shows only what is new since yesterday;
             * names offered but neither chosen nor excluded since the first run are listed
               as waiting for the owner, BANNED/CONFIRM tagged, with the "5. Add target"
               input that decides each one (owner decides; nothing is ever added here);
             * a digest of every provider's releases since the last one seen, Morphe's own
               patches included (state lives on the watch-state branch, not on main);
             * "better provider?": per app, its provider against the best alternative in the
               community index by patches offered and by our chosen names offered.
  apply    applies the planned removals and baselines in this checkout, runs preflight and
           bancheck, and commits them to main (main-writer queue; refuses if main moved;
           waits while any packet/* branch exists, so a packet controller's base holds).
  issue    one standing issue "Selection watch": body = latest report; a comment only when
           something changed or waits for the owner.
Removals only ever take names away; BANNED and CONFIRM are never touched.
"""
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src/etc'))
import provider_watch  # noqa: E402

OUT = ROOT / 'selection-watch-evidence'
TITLE = 'Selection watch'
MORPHE = 'MorpheApp/morphe-patches'
KEYWORDS = re.compile(r'(?i)\b(add|added|new|remov|drop|renam|deprecat|fix|support|break|always)')


def lines(path):
    return [l for l in path.read_text(encoding='utf-8').splitlines() if l.strip() and not l.startswith('#')] if path.is_file() else []


def cap(total):
    return max(3, total // 4)


def rules(root, kind):
    return [l.strip().lower() for l in lines(root / 'src/patches' / kind)]


def tag(name, banned, confirm):
    low = name.lower()
    return 'BAN' if any(b in low for b in banned) else 'CFM' if any(c in low for c in confirm) else ''


def esc(value, limit=200):
    value = re.sub(r'[\x00-\x1f\x7f]', ' ', str(value))[:limit]
    return provider_watch.display(value)


def plan_names(root, rows, observed, pending):
    """Edits and findings from one observation per provider row."""
    banned, confirm = rules(root, 'BANNED'), rules(root, 'CONFIRM')
    today = datetime.date.today().isoformat()
    edits, baselines, findings, waiting, blocked = {}, {}, [], [], []
    for row in rows:
        key = row['target'] + '/' + row['name']
        names = observed.get(key)
        if names is None:
            findings.append('%s: names unreadable today; nothing changed for it' % key)
            continue
        offered = set(names)
        d = root / 'src/patches' / row['patch_dir']
        inc = lines(d / 'include-patches')
        exc = lines(d / 'exclude-patches')
        gone_inc = [l for l in inc if l.split('|', 1)[0] not in offered]
        gone_exc = [l for l in exc if l not in offered]
        if len(gone_inc) > cap(len(inc)):
            blocked.append('%s: %d of %d chosen names gone at once; not removed (builds fall back to the next provider). Gone: %s'
                           % (key, len(gone_inc), len(inc), ', '.join(gone_inc)))
        else:
            # Excludes are safety rails: one the provider stopped offering stays, so a name it
            # brings back later is still kept out (open-mode apps apply provider defaults).
            if gone_inc:
                edits[row['patch_dir']] = dict(include=gone_inc, exclude=[], provider=key)
            path = 'docs/review/providers/' + row['baseline']
            old = lines(root / path)
            if sorted(old) != sorted(names):
                baselines[path] = dict(added=sorted(offered - set(old)), removed=sorted(set(old) - offered),
                                       names=sorted(names), seeded=not old)
        decided = {l.split('|', 1)[0] for l in inc} | set(exc)
        before = set(lines(root / 'docs/review/providers' / row['baseline']))
        for k in [k for k in pending if k.startswith(key + '|') and (k.split('|', 1)[1] in decided or k.split('|', 1)[1] not in offered)]:
            pending.pop(k)
        for n in sorted(offered - decided):
            if key + '|' + n not in pending and before and n not in before:
                pending[key + '|' + n] = today
            if key + '|' + n in pending:
                waiting.append(dict(target=row['target'], provider=row['name'], patch_dir=row['patch_dir'], name=n,
                                    tag=tag(n, banned, confirm), since=pending[key + '|' + n]))
    return dict(edits=edits, baselines=baselines, findings=findings, waiting=waiting, blocked=blocked)


def gh_json(path):
    r = subprocess.run(['gh', 'api', path], capture_output=True, timeout=120)
    if r.returncode != 0:
        raise ValueError('GET failed')
    return json.loads(r.stdout or b'null')


def digest(repos, chosen, seen, reader=gh_json):
    """Releases newer than the last seen one, per repo; first sight shows only the newest."""
    out = []
    for repo in repos:
        try:
            rels = [r for r in reader('repos/%s/releases?per_page=10' % repo) if not r.get('draft') and r.get('published_at')]
        except Exception:
            out.append(dict(repo=repo, error='releases unreadable'))
            continue
        rels.sort(key=lambda r: r['published_at'], reverse=True)
        last = seen.get(repo)
        new = [r for r in rels if last and r['published_at'] > last] if last else rels[:1]
        if rels:
            seen[repo] = rels[0]['published_at']
        for r in new[:5]:
            body = (r.get('body') or '').splitlines()
            keep = [l.strip(' -*#\t') for l in body if KEYWORDS.search(l) or any(c in l for c in chosen)]
            out.append(dict(repo=repo, tag=r.get('tag_name', ''), date=r['published_at'][:10], url=r.get('html_url', ''),
                            prerelease=bool(r.get('prerelease')), lines=[l for l in keep if l][:12]))
    return out


def ranking(root, targets):
    """Per app: current providers vs the best alternative in the community index."""
    try:
        index = json.loads((root / 'src/community/bundles.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return ['community index unreadable']
    banned, confirm = rules(root, 'BANNED'), rules(root, 'CONFIRM')
    comp = index.get('compatibilities') or []

    def offers(bundle, package):
        names = []
        for p in bundle.get('patches') or []:
            k = p.get('compatiblePackagesKey', p.get('compatibilityKey'))
            pk = comp[k] if isinstance(k, int) and 0 <= k < len(comp) else None
            if pk is None or any(isinstance(x, dict) and x.get('packageName') == package for x in pk):
                names.append(p.get('name') or '')
        return [n for n in names if n]
    out = []
    for t in targets:
        if not t.get('enabled'):
            continue
        mine = {('%s/%s' % (c.get('owner'), c.get('repo'))).lower(): c for c in t['candidates'] + t.get('extra_bundles', [])}
        chosen = set()
        for c in t['candidates'] + t.get('extra_bundles', []):
            if not c.get('fallback'):
                chosen |= {l.split('|', 1)[0] for l in lines(root / 'src/patches' / c['patch_dir'] / 'include-patches')}
        rows = []
        for b in index.get('bundles') or []:
            if t['package'] not in (b.get('targetApps') or []):
                continue
            names = offers(b, t['package'])
            rows.append(dict(repo=b.get('repo', ''), total=len(names), overlap=len(chosen & set(names)),
                             risk=sum(1 for n in names if tag(n, banned, confirm)),
                             current=(b.get('repo') or '').lower() in mine))
        cur = [r for r in rows if r['current']]
        alt = sorted([r for r in rows if not r['current']], key=lambda r: (r['total'], r['overlap']), reverse=True)
        if not alt:
            out.append('%s: no alternative in the community index' % t['id'])
            continue
        c0 = max(cur, key=lambda r: r['total']) if cur else dict(repo='(not in index)', total=0, overlap=0, risk=0)
        a = alt[0]
        flag = ' **better provider?**' if a['total'] > c0['total'] else ''
        out.append('%s: now %s (%d offered, %d of our %d chosen, %d ban-risk); best other %s (%d offered, %d of our chosen, %d ban-risk)%s'
                   % (t['id'], c0['repo'], c0['total'], c0['overlap'], len(chosen), c0['risk'], a['repo'], a['total'],
                      a['overlap'], a['risk'], flag))
    return out


def report(p, dig, rank, run_url):
    L = ['# Selection watch', '', run_url, '',
         'Removed names are ones the provider no longer offers; builds already go without them. '
         'Nothing is ever added here: new patches wait for you.', '']
    L += ['## Removed today (%d folder(s))' % len(p['edits'])]
    for d, e in sorted(p['edits'].items()):
        L.append('- `%s` (%s): %s' % (esc(d), esc(e['provider']), ', '.join('`%s`' % esc(x) for x in e['include'])))
    L += ['', '## Needs you']
    L += ['- ' + esc(b, 2000) for b in p['blocked']] or ['- nothing blocked']
    L += ['', '## New patches waiting for your call (%d)' % len(p['waiting'])]
    for w in p['waiting'][:80]:
        L.append('- %s%s / %s: `%s` (since %s). Add: "5. Add target", action patch, id `%s`, patches `%s`; skip: patches `-%s`'
                 % ('**%s** ' % w['tag'] if w['tag'] else '', esc(w['target']), esc(w['provider']), esc(w['name']), w['since'],
                    esc(w['target']), esc(w['name']), esc(w['name'])))
    L += ['', '## Provider releases since the last run']
    for d in dig:
        if d.get('error'):
            L.append('- %s: %s' % (esc(d['repo']), d['error']))
            continue
        L.append('- **%s %s** (%s%s) %s' % (esc(d['repo']), esc(d['tag'], 80), d['date'], ', pre-release' if d['prerelease'] else '', d['url']))
        L += ['  - ' + esc(x) for x in d['lines']]
    if not dig:
        L.append('- none')
    L += ['', '## Better provider? (community index, you decide; switching goes through onboarding)']
    L += ['- ' + esc(r, 600) for r in rank]
    L += ['', '## Baselines re-seeded (%d)' % len(p['baselines'])]
    for path, b in sorted(p['baselines'].items()):
        L.append('- `%s`: %s' % (esc(path), 'seeded, %d names' % len(b['names']) if b['seeded'] else
                                 '+%d -%d' % (len(b['added']), len(b['removed']))))
    L += ['', '## Not read today'] + (['- ' + esc(f, 300) for f in p['findings']] or ['- every provider was read'])
    return '\n'.join(L) + '\n'


def collect(root, out, observe, reader=gh_json, state_text=None, identity=None):
    targets = json.loads((root / 'src/targets.json').read_text(encoding='utf-8'))
    rows = provider_watch.inventory(targets)
    state = json.loads(state_text) if state_text else {}
    state.setdefault('pending', {})
    state.setdefault('releases', {})
    observed = {}
    for row in rows:
        try:
            observed[row['target'] + '/' + row['name']] = list(observe(row)['names'])
        except Exception:
            pass
    p = plan_names(root, rows, observed, state['pending'])
    chosen = set()
    for row in rows:
        chosen |= {l.split('|', 1)[0] for l in lines(root / 'src/patches' / row['patch_dir'] / 'include-patches')}
    repos = sorted({'%s/%s' % (r['owner'], r['repo']) for r in rows if r['host'] == 'github'} | {MORPHE})
    dig = digest(repos, chosen, state['releases'], reader)
    rank = ranking(root, targets)
    run_url = (identity or {}).get('run_url', '')
    text = report(p, dig, rank, run_url)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'plan.json').write_text(json.dumps(p, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    (out / 'state.json').write_text(json.dumps(state, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    (out / 'report.md').write_text(text, encoding='utf-8')
    changed = bool(p['edits'] or p['blocked'] or p['waiting'] or any(not d.get('error') for d in dig))
    (out / 'changed').write_text('1\n' if changed else '0\n', encoding='utf-8')
    print('SELECTION_WATCH removed=%d blocked=%d waiting=%d releases=%d baselines=%d unread=%d'
          % (len(p['edits']), len(p['blocked']), len(p['waiting']), len([d for d in dig if not d.get('error')]),
             len(p['baselines']), len(p['findings'])))
    return p


def git(root, *args):
    r = subprocess.run(['git', *args], cwd=root, capture_output=True, timeout=120)
    if r.returncode != 0:
        raise ValueError('git %s failed: %s' % (args[0], r.stderr.decode('utf-8', 'replace')[:200]))
    return r.stdout.decode().strip()


def apply(root, out, runner=git, push=True):
    p = json.loads((out / 'plan.json').read_text(encoding='utf-8'))
    paths = []
    for d, e in p['edits'].items():
        for side in ('include', 'exclude'):
            gone = set(e[side])
            if not gone:
                continue
            f = root / 'src/patches' / d / (side + '-patches')
            raw = f.read_bytes().decode('utf-8').split('\n')
            f.write_bytes('\n'.join(l for l in raw if l not in gone).encode('utf-8'))
            paths.append(str(f.relative_to(root)))
    for path, b in p['baselines'].items():
        (root / path).write_text('\n'.join(b['names']) + '\n', encoding='utf-8')
        paths.append(path)
    if not paths:
        print('SELECTION_APPLY nothing to commit')
        return 'NOTHING'
    if push:
        # A packet controller gates on the exact main commit: never move main under one.
        packets = runner(root, 'ls-remote', 'origin', 'refs/heads/packet/*').split()
        if packets:
            print('SELECTION_APPLY paused: packet branch %s exists; tomorrow retries' % packets[1].rsplit('/', 1)[-1])
            return 'PAUSED'
    import preflight
    preflight.check(root)
    head = runner(root, 'rev-parse', 'HEAD')
    runner(root, 'add', '--', *paths)
    staged = sorted(runner(root, 'diff', '--cached', '--name-only').splitlines())
    if not set(staged) <= set(paths):
        raise ValueError('staged files differ from the plan')
    if not staged:
        print('SELECTION_APPLY nothing changed on disk')
        return 'NOTHING'
    msg = ['selection watch: %d folder(s) lose names the provider no longer offers, %d baseline(s) re-seeded'
           % (len(p['edits']), len(p['baselines'])), '']
    for d, e in sorted(p['edits'].items()):
        msg.append('%s: -%s' % (d, '; -'.join(e['include'] + e['exclude'])))
    runner(root, '-c', 'user.name=github-actions[bot]', '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com',
           'commit', '-q', '-m', '\n'.join(msg)[:6000])
    if push:
        remote = runner(root, 'ls-remote', 'origin', 'refs/heads/main').split()
        if remote[:1] != [head]:
            raise ValueError('REMOTE_MAIN_MOVED: nothing pushed; tomorrow retries')
        runner(root, 'push', 'origin', 'HEAD:refs/heads/main')
    print('SELECTION_APPLY committed %d file(s)' % len(staged))
    return 'COMMITTED'


def issue(out, repo):
    body = (out / 'report.md').read_text(encoding='utf-8')[:60000]
    found = subprocess.run(['gh', 'issue', 'list', '--repo', repo, '--state', 'open', '--search', 'in:title "%s"' % TITLE,
                            '--json', 'number,title'], capture_output=True, timeout=120)
    rows = [r for r in json.loads(found.stdout or b'[]') if r.get('title') == TITLE] if found.returncode == 0 else []
    with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write(body)
    if rows:
        n = str(rows[0]['number'])
        subprocess.run(['gh', 'issue', 'edit', n, '--repo', repo, '--body-file', f.name], check=True, timeout=120)
        if (out / 'changed').read_text().strip() == '1':
            first = [l for l in body.splitlines() if l.startswith('## ')]
            subprocess.run(['gh', 'issue', 'comment', n, '--repo', repo, '--body',
                            'Updated by run %s: %s' % (os.environ.get('GITHUB_RUN_ID', '?'), '; '.join(first[:4]))],
                           check=True, timeout=120)
    else:
        subprocess.run(['gh', 'issue', 'create', '--repo', repo, '--title', TITLE, '--body-file', f.name], check=True, timeout=120)
    print('SELECTION_ISSUE updated')


def main(argv):
    if len(argv) != 1 or argv[0] not in ('collect', 'apply', 'issue'):
        print('usage: selection_watch.py collect|apply|issue', file=sys.stderr)
        return 2
    if argv[0] == 'collect':
        ident = provider_watch.run_identity(os.environ)
        state = os.environ.get('PF_WATCH_STATE_FILE')
        text = Path(state).read_text(encoding='utf-8') if state and Path(state).is_file() else None
        with tempfile.TemporaryDirectory(prefix='pf-selection-watch-') as work:
            collect(ROOT, OUT, provider_watch.Observer(ROOT, Path(work)), state_text=text, identity=ident)
        if os.environ.get('GITHUB_STEP_SUMMARY'):
            with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as s:
                s.write((OUT / 'report.md').read_text(encoding='utf-8')[:60000])
        return 0
    if argv[0] == 'apply':
        apply(ROOT, OUT)
        return 0
    issue(OUT, os.environ.get('GITHUB_REPOSITORY', 'govinda-rajulu/patch-factory'))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as e:
        print('::error::selection watch stopped: %s' % (str(e)[:300] if isinstance(e, ValueError) else type(e).__name__))
        sys.exit(1)
