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
           waits while an unmerged packet/* branch exists, so a packet controller's base holds;
           W15d: merged ones waiting for cleanup no longer pause it).
  adopt    (W15b) new names the src/patches/ADOPT.json rule passes (name AND community-index
           description) go to ONE pull request with onboarding records; checks are started on
           it; 11. Rule merge merges it only when green (W15d). Held names wait for the owner with the rule that held them.
  issue    one standing issue "Selection watch": body = latest report; a comment only when
           something changed or waits for the owner.
Removals only ever take names away; BANNED, CONFIRM and exclude lists are never touched.
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
import provider_watch
import decisions
import readable  # noqa: E402

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


def adopt_policy(root):
    return json.loads((root / 'src/patches/ADOPT.json').read_text(encoding='utf-8'))


def index_descriptions(root):
    """(repo lower, patch name) -> list of (packages, description) from the community index."""
    path = root / 'src/community/bundles.json'
    if not path.is_file():
        return {}
    d = json.loads(path.read_text(encoding='utf-8'))
    comp, out = d.get('compatibilities') or [], {}
    for b in d.get('bundles') or []:
        for p in b.get('patches') or []:
            k = p.get('compatiblePackagesKey')
            cp = comp[k] if isinstance(k, int) and 0 <= k < len(comp) else None
            pkgs = (set(cp) if isinstance(cp, dict) else {e.get('packageName') for e in cp if isinstance(e, dict)}
                    if isinstance(cp, list) else set())
            apps = [a for a in (b.get('targetApps') or []) if isinstance(a, str)]
            if not pkgs and 0 < len(apps) <= 2:
                # A bundle built for one app (HushGram; HushTelegram's two Telegram packages)
                # tags no package per patch; its patches are for that app, not universal.
                pkgs = set(apps)
            out.setdefault((str(b.get('repo', '')).lower(), p.get('name')), []).append(
                (pkgs, str(p.get('description') or '')))
    return out


def classify(policy, descriptions, row, package, name, flag, others=()):
    """W15b auto-adopt rule. Returns ('adopt', why) or ('hold', why); unsure means hold.
    others: names other bundles of the same app offer (one name under two bundles aborts)."""
    if flag == 'BAN':
        return 'hold', 'matches BANNED'
    if flag == 'CFM':
        return 'hold', 'matches CONFIRM: owner decides'
    if name in others:
        who = ' (%s)' % others[name] if isinstance(others, dict) and others[name] else ''
        return 'hold', 'another bundle of this app%s offers the same name; one bundle per name (AGENTS rule 4)' % who
    # W15d: a name the owner gave to another provider (one provider per feature) waits.
    for r in policy.get('reserved', []):
        mine = {str(row.get('name', '')).lower(), str(row.get('owner', '')).lower()}
        if r.get('target') == row.get('target') and r.get('name') == name and str(r.get('for', '')).lower() not in mine:
            return 'hold', 'reserved for %s by the owner: %s' % (r.get('for'), r.get('why', ''))
    repo = ('%s/%s' % (row.get('owner', ''), row.get('repo', ''))).lower()
    entries = descriptions.get((repo, name), [])
    found = [desc for pkgs, desc in entries if package in pkgs]
    if not found and any(not pkgs for pkgs, _ in entries):
        return 'hold', 'universal patch: the index ties it to no app, so it was not written for this one'
    if not found or not found[0].strip():
        return 'hold', 'no description in the community index'
    text = (name + ' ' + found[0]).lower()
    for w in policy['hold_words']:
        if w in text:
            return 'hold', 'hold word "%s"' % w
    for w in policy['paid_words']:
        if w in text and row['target'] not in policy['paid_ok_targets']:
            return 'hold', 'paid word "%s" on an app outside paid_ok_targets' % w
    words = set(re.findall(r'[a-z]+', text))
    first = (re.findall(r'[a-z]+', name.lower()) or [''])[0]
    if (first in policy.get('content_verbs', []) and not any(w in text for w in policy.get('switch_words', []))
            and not words & set(policy.get('wanted_words', []))):
        return 'hold', 'changes what the app shows for good: no off switch and no ad, tracking or suggestion target in its description'
    return 'adopt', 'by the Selection watch adopt rule (src/patches/ADOPT.json): no BANNED, CONFIRM, hold or paid match in its name or index description'


def solo_candidates(root):
    targets = json.loads((root / 'src/targets.json').read_text(encoding='utf-8'))
    return {(t.get('id'), c.get('name')) for t in targets for c in t.get('candidates') or []
            if isinstance(c, dict) and (c.get('overrides') or {}).get('extra_bundles') == []}


def peer_names(root, rows, observed, w):
    """Names that make w a second copy, mapped to the bundle that holds them first.
    W16h (25 Oct 2026): two bundles offering one name used to hold each other, so
    neither copy ever reached the owner (live Needs you: piko and brosssh both held
    'Hide notes tray'). A name now waits only for a bundle that builds alongside this
    one and either ships it or comes earlier (primary first, then extras in order).
    Two candidates never build together, so they are not peers."""
    me = next((i for i, r in enumerate(rows) if r['target'] == w['target'] and r['name'] == w['provider']), len(rows))
    role = rows[me]['role'] if me < len(rows) else 'extra'
    alone = solo_candidates(root)
    out = {}
    for i, r in enumerate(rows):
        if r['target'] != w['target'] or i == me or (role == 'candidate' and r['role'] == 'candidate'):
            continue
        # A candidate whose overrides drop the extras (Truecaller heval99) builds alone.
        if (role == 'candidate' and (w['target'], w['provider']) in alone) or \
                (r['role'] == 'candidate' and (r['target'], r['name']) in alone):
            continue
        for n in lines(root / 'src/patches' / r['patch_dir'] / 'include-patches'):
            out.setdefault(n.split('|', 1)[0], r['name'])
        if i < me:
            for n in observed.get(r['target'] + '/' + r['name']) or []:
                out.setdefault(n, r['name'])
    return out


def plan_names(root, rows, observed, pending, open_targets=frozenset()):
    """Edits and findings from one observation per provider row. A new name in an open-mode
    app (no exclusive include list) already ships by the provider's default: it is reported
    once under its own heading and never waits (W14: YouTube's Force system font waited)."""
    banned, confirm = rules(root, 'BANNED'), rules(root, 'CONFIRM')
    today = datetime.date.today().isoformat()
    edits, baselines, findings, waiting, blocked, defaults, backlog = {}, {}, [], [], [], [], []
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
            if row['target'] in open_targets:
                pending.pop(key + '|' + n, None)
                if before and n not in before:
                    defaults.append(dict(target=row['target'], provider=row['name'], name=n, tag=tag(n, banned, confirm)))
                continue
            if key + '|' + n not in pending and before and n not in before:
                pending[key + '|' + n] = today
            if key + '|' + n in pending:
                waiting.append(dict(target=row['target'], provider=row['name'], patch_dir=row['patch_dir'], name=n,
                                    tag=tag(n, banned, confirm), since=pending[key + '|' + n],
                                    owner=row.get('owner', ''), repo=row.get('repo', '')))
            elif before:
                # W15b (owner, 20 Oct 2026): older names never chosen go through the same rule.
                backlog.append(dict(target=row['target'], provider=row['name'], patch_dir=row['patch_dir'], name=n,
                                    tag=tag(n, banned, confirm), since='before watch',
                                    owner=row.get('owner', ''), repo=row.get('repo', '')))
    return dict(edits=edits, baselines=baselines, findings=findings, waiting=waiting, blocked=blocked, defaults=defaults,
                backlog=backlog)


def gh_json(path):
    r = subprocess.run(['gh', 'api', path], capture_output=True, timeout=120)
    if r.returncode != 0:
        raise ValueError('GET failed')
    return json.loads(r.stdout or b'null')


def digest(repos, chosen, seen, reader=gh_json, tags=None):
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
            if tags is not None:
                tags[repo] = rels[0].get('tag_name', '')
        for r in new[:5]:
            body = (r.get('body') or '').splitlines()
            keep = [l.strip(' -*#\t') for l in body if KEYWORDS.search(l) or any(c in l for c in chosen)]
            out.append(dict(repo=repo, tag=r.get('tag_name', ''), date=r['published_at'][:10], url=r.get('html_url', ''),
                            prerelease=bool(r.get('prerelease')), lines=[l for l in keep if l][:12]))
    return out


def version_key(tag):
    return tuple(int(x) for x in re.findall(r'\d+', tag or '')[:4])


def reminders(root, tags):
    """Owner reminders that fire on a provider version (W14): each entry in
    src/etc/reminders.json says {"repo", "at_least", "say"}; it shows every day once the
    repo's newest release reaches at_least, until the entry is removed."""
    try:
        rows = json.loads((root / 'src/etc/reminders.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return ['reminders file unreadable']
    due = []
    for r in rows if isinstance(rows, list) else []:
        tag = tags.get(r.get('repo', ''))
        if tag and version_key(tag) >= version_key(r.get('at_least', '')):
            due.append('%s %s: %s' % (r['repo'], tag, r.get('say', '')))
    return due


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
            # Two shapes in the index: [{"packageName": ...}] and {"package": [versions]} (W13:
            # the second, HushFacebook's, read as offering nothing). None or empty: any app.
            if isinstance(pk, dict):
                pkgs = set(pk)
            elif isinstance(pk, list):
                pkgs = {x.get('packageName') for x in pk if isinstance(x, dict)} | {x for x in pk if isinstance(x, str)}
            else:
                pkgs = set()
            if not pkgs or package in pkgs:
                names.append(p.get('name') or '')
        return [n for n in names if n]
    out = []
    for t in targets:
        if not t.get('enabled'):
            continue
        # Current = what builds today (primary candidates and extra bundles). A fallback is
        # neither current nor an alternative (W13: De-Vanced showed as Facebook's "now").
        mine = {('%s/%s' % (c.get('owner'), c.get('repo'))).lower(): c for c in t['candidates'] + t.get('extra_bundles', [])
                if not c.get('fallback')}
        spare = {('%s/%s' % (c.get('owner'), c.get('repo'))).lower() for c in t['candidates'] if c.get('fallback')}
        chosen = set()
        for c in t['candidates'] + t.get('extra_bundles', []):
            if not c.get('fallback'):
                chosen |= {l.split('|', 1)[0] for l in lines(root / 'src/patches' / c['patch_dir'] / 'include-patches')}
        rows = []
        for b in index.get('bundles') or []:
            if t['package'] not in (b.get('targetApps') or []) or (b.get('repo') or '').lower() in spare:
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


def held_kind(why):
    """Short reason group for a held name, so 77 held names read as a handful of rows."""
    low = (why or '').lower()
    for word, kind in (('reserved', 'reserved by the owner'), ('banned', 'matches BANNED'), ('confirm', 'matches CONFIRM: owner decides'),
                       ('universal patch', 'universal patch (not written for this app)'), ('paid word', 'paid word on an account app'),
                       ('another bundle', 'same name in another bundle (one bundle per name)'),
                       ('for good', 'changes the app for good (no off switch)'), ('no description', 'no description in the index'),
                       ('hold word', 'hold word')):
        if word in low:
            return kind
    return 'other'


def report(p, dig, rank, run_url, due=()):
    """W15e (owner, 22 Oct 2026): tables first, long lists folded. Style: docs/review/REPORT-STYLE.md."""
    adopt = [w for w in p['waiting'] + p.get('backlog', []) if w.get('call') == 'adopt']
    held = [w for w in p['waiting'] if w.get('call') not in ('adopt', 'skip')]
    old_held = [w for w in p.get('backlog', []) if w.get('call') not in ('adopt', 'skip')]
    defaults = p.get('defaults') or []
    needs = len(p['blocked']) + len(held) + len(due)
    removed = sum(len(e['include']) for e in p['edits'].values())
    L = readable.headline('Selection watch', 'NEEDS YOU' if needs else 'OK', needs)
    L += [run_url, '']
    L += readable.table(['What', 'Count', 'Meaning'], [
        ['Needs you', needs, 'blocked names, new names waiting for your call, reminders'],
        ['Removed today', '%d name(s) in %d folder(s)' % (removed, len(p['edits'])), 'the provider no longer offers them; builds already go without'],
        ['Adopted by rule', '%d name(s) on %d app(s)' % (len(adopt), len({w['target'] for w in adopt})),
         'one pull request; 11. Rule merge merges it when every check, review and test build is green'],
        ['Held by the rule', len(old_held), 'older names the rule keeps out, grouped by reason below'],
        ['New in open-mode apps', len(defaults), "they already ship by the provider's default"],
        ['Provider releases', len([d for d in dig if not d.get('error')]), 'since the last run'],
        ['Baselines re-seeded', len(p['baselines']), 'name lists the next run compares against'],
        ['Not read today', len(p['findings']), 'providers this run could not read']])
    L += ['', '## Needs you']
    rows = [['blocked', esc(b, 2000)] for b in p['blocked']]
    rows += [['reminder', esc(d, 600)] for d in due]
    rows += [['new name', '%s%s / %s: `%s` (since %s%s). Add: "5. Add target", action patch, id `%s`, patches `%s`; skip: patches `-%s`'
              % ('**%s** ' % w['tag'] if w['tag'] else '', esc(w['target']), esc(w['provider']), esc(w['name']), w['since'],
                 '; held: ' + esc(w['why'], 120) if w.get('why') else '', esc(w['target']), esc(w['name']), esc(w['name']))]
             for w in held[:80]]
    L += readable.table(['Kind', 'What to do'], rows) if rows else ['- nothing blocked']
    if p['edits']:
        L += ['', '## Removed today (%d folder(s))' % len(p['edits'])]
        L += readable.table(['Folder', 'Provider', 'Names the provider dropped'],
                            [['`%s`' % esc(d), esc(e['provider']), readable.names(esc(x) for x in e['include'])]
                             for d, e in sorted(p['edits'].items())])
    if adopt:
        L += ['', '## Adopted by rule (%d): pull request opened; 11. Rule merge merges it when green' % len(adopt)]
        by = readable.group(adopt, lambda w: (w['target'], w['provider']))
        L += readable.table(['App / provider', 'Names', 'New names'],
                            [['%s / %s' % (esc(t), esc(v)), len(ws), readable.names(esc(w['name']) for w in ws)] for (t, v), ws in by.items()])
        L += [''] + readable.details('All %d adopted names' % len(adopt),
                                     ['- %s / %s: `%s`' % (esc(w['target']), esc(w['provider']), esc(w['name'])) for w in adopt[:200]])
    if old_held:
        L += ['', '## Older names never chosen, held by the rule (%d)' % len(old_held)]
        kinds = readable.group(old_held, lambda w: held_kind(w.get('why')))
        L += readable.table(['Why held', 'Names', 'Apps'],
                            [[k, len(ws), ', '.join(sorted({esc(w['target']) for w in ws}))] for k, ws in kinds.items()])
        L += [''] + readable.details('Every held name with its reason',
                                     ['- %s / %s: `%s` (held: %s)' % (esc(w['target']), esc(w['provider']), esc(w['name']), esc(w['why'], 120))
                                      for w in old_held[:200]])
    if defaults:
        L += ['', "## New in open-mode apps (%d): they already ship by the provider's default" % len(defaults)]
        L += readable.table(['App / provider', 'Name', 'To drop it'],
                            [['%s / %s' % (esc(w['target']), esc(w['provider'])), '%s`%s`' % ('**%s** ' % w['tag'] if w['tag'] else '', esc(w['name'])),
                              '"5. Add target", action patch, id `%s`, patches `-%s`' % (esc(w['target']), esc(w['name']))] for w in defaults[:80]])
    L += ['', '## Provider releases since the last run']
    good = [d for d in dig if not d.get('error')]
    if good:
        L += readable.table(['Provider', 'Release', 'Date', 'Link'],
                            [['**%s %s**' % (esc(d['repo']), esc(d['tag'], 80)), 'pre-release' if d['prerelease'] else 'release', d['date'], d['url']] for d in good])
        notes = []
        for d in good:
            notes += ['- **%s %s**' % (esc(d['repo']), esc(d['tag'], 80))] + ['  - ' + esc(x) for x in d['lines']]
        L += [''] + readable.details('Release notes (first lines)', notes)
    L += ['- %s: %s' % (esc(d['repo']), d['error']) for d in dig if d.get('error')]
    if not dig:
        L.append('- none')
    L += ['', '## Better provider? (community index, you decide; switching goes through onboarding)']
    split = [r.split(': ', 1) if ': ' in r else [r, ''] for r in rank]
    flagged = [x for x in split if '**better provider?**' in x[1]]
    L += readable.table(['App', 'Now and best other'], [[esc(a), esc(b.replace('**better provider?**', ''), 600) + ' **better provider?**'] for a, b in flagged]) \
        if flagged else ['- no app has a bigger provider in the index']
    L += [''] + readable.details('Every app (%d)' % len(rank), ['- ' + esc(r, 600) for r in rank])
    if p['baselines']:
        L += ['', '## Baselines re-seeded (%d)' % len(p['baselines'])]
        L += readable.details('Files', ['- `%s`: %s' % (esc(path), 'seeded, %d names' % len(b['names']) if b['seeded'] else
                                                     '+%d -%d' % (len(b['added']), len(b['removed']))) for path, b in sorted(p['baselines'].items())])
    L += ['', '## Not read today'] + (['- ' + esc(f, 300) for f in p['findings']] or ['- every provider was read'])
    return '\n'.join(L) + '\n'


KEEP_HOLD = ('another bundle', 'reserved for', 'paid word')


def remember(memory, rows):
    """W16j: the owner decides a name once per app (src/patches/DECISIONS.json). take adopts a held
    name from any provider; drop keeps it out quietly. BANNED, one bundle per name, reserved names
    and paid words outside paid_ok_targets still win."""
    for w in rows:
        verdict, row = decisions.call(memory, w['target'], w['name'])
        if not verdict or w.get('tag') == 'BAN':
            continue
        why = 'owner decided %s on %s (%s, src/patches/DECISIONS.json)' % (verdict, row.get('date', '?'), row.get('id', '?'))
        if verdict == 'drop':
            w['call'], w['why'] = 'skip', why
        elif w.get('call') == 'hold' and not str(w.get('why', '')).startswith(KEEP_HOLD):
            w['call'], w['why'] = 'adopt', why + '; the rule alone held it: ' + str(w.get('why', ''))
            if w.get('tag') == 'CFM':
                w['approved'] = True


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
    p = plan_names(root, rows, observed, state['pending'], frozenset(t['id'] for t in targets if not t.get('exclusive')))
    # W15b: every waiting name gets an adopt or hold call with its reason.
    policy, descriptions = adopt_policy(root), index_descriptions(root)
    packages = {t['id']: t.get('package') for t in targets}
    for w in p['waiting'] + p['backlog']:
        w['call'], w['why'] = classify(policy, descriptions, w, packages.get(w['target']), w['name'], w['tag'],
                                       peer_names(root, rows, observed, w))
    remember(decisions.load(root), p['waiting'] + p['backlog'])
    chosen = set()
    for row in rows:
        chosen |= {l.split('|', 1)[0] for l in lines(root / 'src/patches' / row['patch_dir'] / 'include-patches')}
    repos = sorted({'%s/%s' % (r['owner'], r['repo']) for r in rows if r['host'] == 'github'} | {MORPHE})
    state.setdefault('tags', {})
    dig = digest(repos, chosen, state['releases'], reader, state['tags'])
    due = reminders(root, state['tags'])
    p['reminders'] = due
    rank = ranking(root, targets)
    run_url = (identity or {}).get('run_url', '')
    text = report(p, dig, rank, run_url, due)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'plan.json').write_text(json.dumps(p, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    (out / 'state.json').write_text(json.dumps(state, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    (out / 'report.md').write_text(text, encoding='utf-8')
    changed = bool(p['edits'] or p['blocked'] or p['waiting'] or p['defaults'] or due or any(not d.get('error') for d in dig))
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


def gh_compare(sha):
    """GitHub's compare status of a commit against main ('ahead' or 'identical' = in main), or None."""
    repo = os.environ.get('GITHUB_REPOSITORY', 'govinda-rajulu/patch-factory')
    r = subprocess.run(['gh', 'api', 'repos/%s/compare/%s...main?per_page=1' % (repo, sha), '--jq', '.status'],
                       capture_output=True, text=True, timeout=120)
    return r.stdout.strip() if r.returncode == 0 else None


def unmerged_packets(listing, compare=gh_compare):
    """W15d: packet branches whose head is NOT in main yet (a controller's base must hold).
    A merged packet branch waits for cleanup (owner F3 holds cleanup) and must not freeze main:
    four merged ones paused every apply. Unknown status counts as unmerged."""
    words = listing.split()
    out = []
    for sha, ref in zip(words[0::2], words[1::2]):
        if compare(sha) not in ('ahead', 'identical'):
            out.append(ref.split('refs/heads/', 1)[-1])
    return out


def apply(root, out, runner=git, push=True, compare=gh_compare):
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
        packets = unmerged_packets(runner(root, 'ls-remote', 'origin', 'refs/heads/packet/*'), compare)
        if packets:
            print('SELECTION_APPLY paused: packet branch %s is not merged yet; tomorrow retries' % packets[0])
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


def adopt(root, out, repo, runner=None, stamp=None):
    """W15b: names the rule adopted go to one pull request; W15d: 11. Rule merge merges it when green.

    One open adopt pull request at a time; app.py writes the onboarding record (each name
    with its reason) and runs the repo's gates and generators; Validate and the Onboarding
    review are started on the branch, because a pull request opened with the workflow token
    starts no checks by itself (same as "5. Add target")."""
    run = runner or (lambda cmd, **k: subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=600, **k))
    plan = json.loads((out / 'plan.json').read_text(encoding='utf-8'))
    picks = [w for w in plan.get('waiting', []) + plan.get('backlog', []) if w.get('call') == 'adopt']
    if not picks:
        print('SELECTION_ADOPT nothing adopted today')
        return 0
    found = run(['gh', 'pr', 'list', '--repo', repo, '--state', 'open', '--json', 'number,headRefName'])
    if found.returncode != 0:
        print('::warning::SELECTION_ADOPT could not list pull requests; nothing opened today')
        return 1
    open_adopt = [r for r in json.loads(found.stdout or '[]') if str(r.get('headRefName', '')).startswith('adopt/')]
    if open_adopt:
        print('SELECTION_ADOPT waiting: pull request #%s is still open; one at a time' % open_adopt[0]['number'])
        return 0
    # W15c (20 Oct 2026): run 39485415276 pushed adopt/2026-10-20-39485415276 and GitHub refused
    # the pull request (the repository did not let Actions create pull requests). A branch with
    # no pull request at all is still pending: open its pull request now, or wait on it; never
    # push a second branch.
    stamp = stamp or datetime.date.today().isoformat()
    heads = run(['git', 'ls-remote', '--heads', 'origin', 'refs/heads/adopt/*'])
    for line in (heads.stdout or '').splitlines() if heads.returncode == 0 else []:
        name = line.split('refs/heads/', 1)[-1].strip()
        if not name.startswith('adopt/'):
            continue
        seen = run(['gh', 'pr', 'list', '--repo', repo, '--state', 'all', '--head', name, '--json', 'number'])
        if seen.returncode == 0 and json.loads(seen.stdout or '[]') == []:
            return open_and_check(root, out, repo, run, name, picks, stamp, pending=True)
        # W15d: no adopt pull request is open (checked above), so this branch's is closed or
        # merged; it is spent. Delete it so old branches do not pile up (5S).
        if seen.returncode == 0:
            gone = run(['git', 'push', 'origin', '--delete', name])
            print('SELECTION_ADOPT %s spent branch %s' % ('deleted' if gone.returncode == 0 else '::warning:: could not delete', name))
    branch = 'adopt/%s-%s' % (stamp, os.environ.get('GITHUB_RUN_ID', 'local'))
    groups = {}
    for w in picks:
        groups.setdefault((w['target'], w['provider']), []).append(w)
    for (target, provider), ws in sorted(groups.items()):
        cmd = ['python3', 'src/etc/app.py', 'patch', target, '--bundle', provider,
               '--patches', '; '.join(w['name'] for w in ws),
               '--why', json.dumps({w['name']: w['why'] for w in ws})]
        if any(w.get('approved') for w in ws):
            cmd.append('--approve-confirm')  # W16j: a CONFIRM name the owner already took (DECISIONS.json)
        r = run(cmd)
        if r.returncode != 0:
            print('::warning::SELECTION_ADOPT %s/%s refused by app.py: %s' % (target, provider, (r.stderr or r.stdout)[-300:]))
            return 1
    if run(['git', 'diff', '--quiet', '--', '.github']).returncode != 0:
        print('::error::SELECTION_ADOPT touched a workflow file; nothing pushed')
        return 1
    steps = [['git', 'switch', '-c', branch],
             ['git', 'add', '-A', '--', 'src', 'docs', 'README.md', 'CREDITS.md'],
             ['git', '-c', 'user.name=github-actions[bot]', '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com',
              'commit', '-m', 'adopt: %d new name(s) by the Selection watch rule' % len(picks)],
             ['git', 'push', 'origin', branch]]
    for cmd in steps:
        r = run(cmd)
        if r.returncode != 0:
            print('::warning::SELECTION_ADOPT %s failed: %s' % (cmd[1], (r.stderr or r.stdout)[-300:]))
            return 1
    return open_and_check(root, out, repo, run, branch, picks, stamp)


def open_and_check(root, out, repo, run, branch, picks, stamp, pending=False):
    groups = {}
    for w in picks:
        groups.setdefault((w['target'], w['provider']), []).append(w)
    body = ['Adopted by the Selection watch rule (src/patches/ADOPT.json). 11. Rule merge merges this only when every check, '
            'the Onboarding review and every test build are green; anything else waits for the owner.', '']
    if pending:
        body += ['The branch was pushed by an earlier run whose pull request GitHub refused; the list below is today\'s rule output.', '']
    body += ['- %s / %s: `%s`: %s' % (w['target'], w['provider'], w['name'], w['why']) for w in picks]
    r = run(['gh', 'pr', 'create', '--repo', repo, '--base', 'main', '--head', branch,
             '--title', 'adopt: %d new patch name(s), %s' % (len(picks), stamp), '--body', '\n'.join(body)])
    if r.returncode != 0:
        note = ('SELECTION_ADOPT branch %s has no pull request; GitHub refused it: %s. Owner: open it from '
                'https://github.com/%s/compare/main...%s or allow Actions to create pull requests '
                '(Settings, Actions, General, Workflow permissions). No second branch is pushed meanwhile.'
                % (branch, (r.stderr or '').strip()[-160:], repo, branch))
        print('::warning::' + note)
        report = out / 'report.md'
        if report.is_file():
            with report.open('a', encoding='utf-8') as f:
                f.write('\n## Adopt waiting\n\n' + note + '\n')
        # The first refusal is red once, so it is seen; later runs wait on the branch quietly.
        return 0 if pending else 1
    number = run(['gh', 'pr', 'view', branch, '--repo', repo, '--json', 'number', '--jq', '.number']).stdout.strip()
    for wf, ref, extra in (('validate.yml', branch, []), ('onboard-review.yml', 'main', ['-f', 'pr=' + number])):
        if run(['gh', 'workflow', 'run', wf, '--repo', repo, '--ref', ref] + extra).returncode != 0:
            print('::warning::SELECTION_ADOPT could not start %s for #%s; run it from the Actions tab' % (wf, number))
    # Validate builds nothing, so each touched app also gets one nonpublishing test build on the
    # branch (the provider itself when it is not the primary), the same evidence a packet smoke gives.
    targets = {t['id']: t for t in json.loads((root / 'src/targets.json').read_text(encoding='utf-8'))}
    for target, provider in sorted(groups):
        primary = ((targets.get(target) or {}).get('candidates') or [{}])[0].get('name')
        extra = [] if provider == primary or provider in [b.get('name') for b in targets.get(target, {}).get('extra_bundles', [])] \
            else ['-f', 'provider=' + provider]
        cmd = ['gh', 'workflow', 'run', 'manual-patch.yml', '--repo', repo, '--ref', branch,
               '-f', 'target=' + target, '-f', 'publish=false'] + extra
        if run(cmd).returncode != 0:
            print('::warning::SELECTION_ADOPT could not start the test build of %s/%s for #%s' % (target, provider, number))
    print('SELECTION_ADOPT opened #%s with %d name(s); test builds started for %d app/provider pair(s)' % (number, len(picks), len(groups)))
    return 0


def issue(out, repo):
    body = (out / 'report.md').read_text(encoding='utf-8')[:60000]
    found = subprocess.run(['gh', 'issue', 'list', '--repo', repo, '--state', 'open', '--search', 'in:title "%s"' % TITLE,
                            '--json', 'number,title'], capture_output=True, timeout=120)
    rows = [r for r in json.loads(found.stdout or b'[]') if r.get('title') == TITLE] if found.returncode == 0 else []
    with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write(body)
    if rows:
        n = str(rows[0]['number'])
        before = subprocess.run(['gh', 'issue', 'view', n, '--repo', repo, '--json', 'body', '-q', '.body'],
                                capture_output=True, text=True, timeout=120)
        subprocess.run(['gh', 'issue', 'edit', n, '--repo', repo, '--body-file', f.name], check=True, timeout=120)
        if (out / 'changed').read_text().strip() == '1':
            # W15e: the comment says only what changed; the body has everything (REPORT-STYLE.md).
            lines = readable.changed_lines(before.stdout if before.returncode == 0 else '', body)
            subprocess.run(['gh', 'issue', 'comment', n, '--repo', repo, '--body',
                            '\n'.join(['**Changed by run %s**' % os.environ.get('GITHUB_RUN_ID', '?'), ''] + lines)],
                           check=True, timeout=120)
    else:
        subprocess.run(['gh', 'issue', 'create', '--repo', repo, '--title', TITLE, '--body-file', f.name], check=True, timeout=120)
    print('SELECTION_ISSUE updated')


def main(argv):
    if len(argv) != 1 or argv[0] not in ('collect', 'apply', 'adopt', 'issue'):
        print('usage: selection_watch.py collect|apply|adopt|issue', file=sys.stderr)
        return 2
    if argv[0] == 'adopt':
        return adopt(ROOT, OUT, os.environ.get('GITHUB_REPOSITORY', 'govinda-rajulu/patch-factory'))
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
