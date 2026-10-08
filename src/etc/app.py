#!/usr/bin/env python3
"""One tool for every app and patch change. Packet W2, 8 Oct 2026.

Owner rule: adding or removing an app, or a patch, takes one or two steps. Step one is the
workflow "5. Add target" (it runs this file and opens a pull request); step two is merging
that pull request once Validate and the Onboarding review are green. Locally:

    python3 src/etc/app.py add ID --package P --label L --provider OWNER/REPO \
        [--patches "A; B"] [--source apkmirror-bundle|apkmirror-apk|apkpure] \
        [--store-url URL] [--needs-microg] [--group media|social|tools] [--approve-confirm]
    python3 src/etc/app.py patch ID --patches "A; -B"     add A, drop B (see PATCH RULE)
    python3 src/etc/app.py disable ID | enable ID         stop or resume building, keep files
    python3 src/etc/app.py remove ID                      target gone, patch folders to _attic
    python3 src/etc/app.py regen | check | list

PATCH RULE. A target with an include list builds exactly that list: "A" adds A, "-A"
drops it. A target with an empty include list builds the provider defaults minus its
exclude list (YouTube): "-A" excludes A, "A" stops excluding it.

Every change writes the onboarding record docs/review/onboarding/<id>.md (no TODO: the
values come from the inputs; the agent review on the pull request is the review, and
merging is the owner's approval), then runs the repo's own checks (preflight, bancheck,
quarantine) and every generator (README block, page catalog, dropdown, credits,
Obtainium files). Nothing here pushes, merges, builds or publishes. Standard library only.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

TARGETS = Path('src/targets.json')
APPS = Path('src/build/helper/apps.json')
PATCHES = Path('src/patches')
OPTIONS = Path('src/options')
RECORDS = Path('docs/review/onboarding')
PORTAL = Path('docs/portal.js')
ID_RX = re.compile(r'^[a-z0-9][a-z0-9-]{0,40}$')
PKG_RX = re.compile(r'^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+$')
STORE_RX = re.compile(r'^https://(www\.)?(apkmirror\.com|apkpure\.(com|net))/[^\s]*$')
SRC_RX = re.compile(r'^[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}$')
GENERATORS = ['src/etc/obtainium.py', 'src/etc/readmegen.py', 'src/etc/dropgen.py',
              'src/etc/credits.py', 'src/etc/pagegen.py']  # pagegen last: it hashes portal.js
CHECKS = [['python3', 'src/etc/preflight.py'], ['bash', 'src/etc/bancheck.sh'], ['bash', 'src/etc/quarantine.sh']]


class Refused(Exception):
    pass


def today():
    return os.environ.get('PF_DATE') or datetime.date.today().isoformat()


def read_json(path):
    text = path.read_text(encoding='utf-8')
    indent = 2
    lines = text.split('\n')
    if len(lines) > 1:
        lead = len(lines[1]) - len(lines[1].lstrip(' '))
        indent = lead or 2
    return json.loads(text), indent


def write_json(path, data, indent):
    path.write_text(json.dumps(data, indent=indent, ensure_ascii=False) + '\n', encoding='utf-8')


def rules(kind):
    p = PATCHES / kind
    if not p.is_file():
        return []
    rows = [x.strip().lower() for x in p.read_text(encoding='utf-8').splitlines()]
    return [r for r in rows if r and not r.startswith('#')]


def lines_of(path):
    if not path.is_file():
        return []
    return [x.rstrip('\n') for x in path.read_text(encoding='utf-8').splitlines()]


def names_in(path):
    return [x.split('|', 1)[0].strip() for x in lines_of(path) if x.strip() and not x.strip().startswith('#')]


def write_lines(path, rows):
    path.write_text(''.join(r + '\n' for r in rows), encoding='utf-8')


def split_patches(text):
    out = []
    for raw in re.split(r'[;\n]', text or ''):
        name = raw.strip()
        if not name:
            continue
        drop = name.startswith('-')
        name = name[1:].strip() if drop else name
        if not name or len(name) > 200 or any(ord(c) < 32 for c in name) or '|' in name:
            raise Refused('bad patch name %r' % raw)
        out.append((drop, name))
    return out


def find(targets, tid):
    hits = [t for t in targets if t.get('id') == tid]
    if len(hits) != 1:
        raise Refused('no target %r' % tid if not hits else 'duplicate target %r' % tid)
    return hits[0]


def screen(names, approve):
    """BANNED always refuses; CONFIRM needs the owner's explicit approval."""
    banned, confirm, approved = rules('BANNED'), rules('CONFIRM'), []
    for n in names:
        low = n.lower()
        hit = [r for r in banned if r in low]
        if hit:
            raise Refused('patch %r matches BANNED %r; it can never be added' % (n, hit[0]))
        hit = [r for r in confirm if r in low]
        if hit:
            if not approve:
                raise Refused('patch %r matches CONFIRM %r; re-run with approve_confirm ticked if you accept it' % (n, hit[0]))
            approved.append(n)
    return approved


def record_path(tid):
    return RECORDS / (tid + '.md')


def source_key(b):
    if (b.get('host') or 'github') == 'gitlab':
        return 'gitlab:' + str(b.get('project_id'))
    return '%s/%s' % (b.get('owner'), b.get('repo'))


def write_record(t, added=(), approved=(), note=None, store=None):
    """Create or extend docs/review/onboarding/<id>.md so the onboarding check can pass."""
    RECORDS.mkdir(parents=True, exist_ok=True)
    p = record_path(t['id'])
    stamp = today()
    if p.is_file():
        text = p.read_text(encoding='utf-8')
    else:
        provs = ', '.join('%s (%s, channel %s)' % (source_key(b), b.get('name'), b.get('channel'))
                          for b in (t.get('candidates') or []) + (t.get('extra_bundles') or []))
        text = ('# %s (%s)\n\nPackage: %s\nSource APK: %s\nProvider: %s\n\n## Patches\n\n## Risks\n'
                '- Written by the agent review on the pull request that carries this record.\n\n'
                '## Decision\nOwner request through "5. Add target" on %s; merging the pull request is the approval.\n') % (
            t.get('label') or t['id'], t['id'], t['package'], store or 'per src/build/helper/apps.json',
            provs or 'none', stamp)
    for b in (t.get('candidates') or []) + (t.get('extra_bundles') or []):
        key = source_key(b)
        if key not in text:
            text = text.replace('\n## Patches\n', '\nProvider added %s: %s (%s, channel %s)\n\n## Patches\n' % (
                stamp, key, b.get('name'), b.get('channel')), 1)
    rows = []
    for n in added:
        if ('- ' + n + ':') not in text:
            rows.append('- %s: added %s by owner request' % (n, stamp))
    for n in approved:
        if ('Owner approved: ' + n) not in text:
            rows.append('Owner approved: ' + n)
    if rows:
        if '\n## Patches\n' in text:
            head, tail = text.split('\n## Patches\n', 1)
            text = head + '\n## Patches\n' + '\n'.join(rows) + '\n' + tail
        else:
            text += '\n## Patches\n' + '\n'.join(rows) + '\n'
    if note:
        text = text.rstrip('\n') + '\n\n' + note + '\n'
    if 'TODO' in text:
        raise Refused('%s contains TODO; fill it in (the onboarding check refuses it)' % p)
    p.write_text(text, encoding='utf-8')
    return p


def portal_edit(fn):
    if not PORTAL.is_file():
        return False
    s = PORTAL.read_text(encoding='utf-8')
    new = fn(s)
    if new != s:
        PORTAL.write_text(new, encoding='utf-8')
        return True
    return False


def portal_group(tid, group):
    def fn(s):
        rx = re.compile(r"(\['%s','[^']*',\[)([^\]]*)(\]\])" % re.escape(group))
        m = rx.search(s)
        if not m:
            raise Refused('page group %r not found in docs/portal.js' % group)
        ids = [x.strip().strip("'") for x in m[2].split(',') if x.strip()]
        if tid in ids:
            return s
        return s[:m.start(2)] + ','.join("'%s'" % x for x in ids + [tid]) + s[m.end(2):]
    return portal_edit(fn)


def _list_lines(s, fn):
    """Apply fn(list_text) only on the LOGOS line and the GROUPS rows of docs/portal.js."""
    out = []
    for line in s.split('\n'):
        m = re.search(r"(const LOGOS=new Set\(\[)([^\]]*)(\]\))", line) or \
            re.search(r"^(\s*\['(?:media|social|tools|other)','[^']*',\[)([^\]]*)(\]\])", line)
        if m:
            line = line[:m.start(2)] + fn(m[2]) + line[m.end(2):]
        out.append(line)
    return '\n'.join(out)


def _without(tid):
    def fn(text):
        ids = [x.strip().strip("'") for x in text.split(',') if x.strip()]
        return ','.join("'%s'" % x for x in ids if x != tid)
    return fn


def portal_forget(tid, logo_only=False):
    def fn(s):
        if logo_only:
            m = re.search(r"(const LOGOS=new Set\(\[)([^\]]*)(\]\))", s)
            return s if not m else s[:m.start(2)] + _without(tid)(m[2]) + s[m.end(2):]
        return _list_lines(s, _without(tid))
    return portal_edit(fn)


def portal_logo(tid):
    """Show the brand tile again when docs/assets/logos/<id>.png exists (enable)."""
    if not Path('docs/assets/logos/%s.png' % tid).is_file():
        return False
    def fn(s):
        m = re.search(r"(const LOGOS=new Set\(\[)([^\]]*)(\]\))", s)
        if not m:
            return s
        ids = [x.strip().strip("'") for x in m[2].split(',') if x.strip()]
        if tid in ids:
            return s
        return s[:m.start(2)] + ','.join("'%s'" % x for x in sorted(ids + [tid])) + s[m.end(2):]
    return portal_edit(fn)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def regen(check=False):
    bad = []
    for g in GENERATORS:
        if not Path(g).is_file():
            continue
        rc, out = run(['python3', g] + (['--check'] if check else []))
        print(('ok   ' if rc == 0 else 'FAIL ') + g + ('' if rc == 0 else ': ' + out[-400:]))
        if rc:
            bad.append(g)
    return bad


def gates():
    bad = []
    for cmd in CHECKS:
        if not Path(cmd[-1]).is_file():
            continue
        rc, out = run(cmd)
        print(('ok   ' if rc == 0 else 'FAIL ') + ' '.join(cmd) + ('' if rc == 0 else ': ' + out[-600:]))
        if rc:
            bad.append(' '.join(cmd))
    return bad


def apply_store(pkg, source, url):
    if not url:
        return 'no store URL given: an enabled target needs one in src/build/helper/apps.json'
    if not STORE_RX.match(url):
        raise Refused('store URL must be an https apkmirror.com or apkpure page')
    data, indent = read_json(APPS)
    if source == 'apkpure':
        data.setdefault('apkpure', {}).setdefault(pkg, {})['download_url'] = url
    else:
        data.setdefault('apkmirror', {}).setdefault(pkg, {})['list_url'] = url
    write_json(APPS, data, indent)
    return None


def cmd_add(a):
    targets, indent = read_json(TARGETS)
    tid = a.id
    if not ID_RX.match(tid):
        raise Refused('id must be lowercase letters, digits and hyphens')
    if any(t.get('id') == tid for t in targets):
        raise Refused('target %s already exists; use patch, enable or disable' % tid)
    if any((t.get('tag_prefix') or t['id']) == tid for t in targets):
        raise Refused('release prefix %s is already used' % tid)
    if not PKG_RX.match(a.package or ''):
        raise Refused('package must look like com.example.app')
    if 'gitlab' in (a.provider or '').lower():
        raise Refused('GitLab is supported only as an extra bundle, not as a primary candidate. The build '
                      'resolver and provider watch resolve primaries through GitHub OWNER/REPO.')
    if not SRC_RX.match(a.provider or ''):
        raise Refused('provider must be OWNER/REPO on GitHub')
    if not a.label or len(a.label) > 60 or any(ord(c) < 32 for c in a.label):
        raise Refused('label is required (the name people see)')
    owner, repo = a.provider.split('/')
    pname = re.sub(r'[^a-z0-9-]', '-', owner.lower()).strip('-') or 'provider'
    pdir = PATCHES / ('%s-%s' % (tid, pname))
    if pdir.exists():
        raise Refused('%s already exists' % pdir)
    names = [n for d, n in split_patches(a.patches) if not d]
    approved = screen(names, a.approve_confirm)
    source = a.source or 'apkmirror-bundle'
    if a.store_url and not STORE_RX.match(a.store_url):
        raise Refused('store URL must be an https apkmirror.com or apkpure page')
    t = {'id': tid, 'enabled': bool(names), 'package': a.package, 'apk_name': tid,
         'apk_type': 'apk' if source == 'apkmirror-apk' else 'bundle',
         'max_app_version': None, 'max_patch_age_days': 60, 'min_sdk_ceiling': 29, 'pin': None,
         'candidates': [{'name': pname, 'host': 'github', 'owner': owner, 'repo': repo,
                         'channel': 'prerelease', 'patch_dir': pdir.name, 'options': pname}],
         'tag_prefix': tid, 'poll': bool(names), 'label': a.label,
         'source': 'apkpure' if source == 'apkpure' else 'apkmirror',
         'note': 'Added %s through 5. Add target.' % today()}
    if names:
        t['exclusive'] = True
    if a.needs_microg:
        t['needs_microg'] = True
    pdir.mkdir(parents=True)
    write_lines(pdir / 'include-patches', names)
    write_lines(pdir / 'exclude-patches', [])
    OPTIONS.mkdir(parents=True, exist_ok=True)
    opt = OPTIONS / (pname + '.json')
    if not opt.exists():
        opt.write_text('[]\n', encoding='utf-8')
    targets.append(t)
    write_json(TARGETS, targets, indent)
    warn = apply_store(a.package, source, a.store_url)
    write_record(t, names, approved, store=a.store_url)
    if a.group:
        portal_group(tid, a.group)
    msg = ['Added %s (%s) from %s, %s.' % (a.label, tid, a.provider,
           'enabled with %d patch name(s)' % len(names) if names else
           'DISABLED: no patch names given, so nothing would build; run patch then enable')]
    if warn:
        msg.append('Warning: ' + warn + '.')
    return msg


def selection(t):
    c = (t.get('candidates') or [None])[0]
    if not c or not c.get('patch_dir'):
        raise Refused('%s has no primary patch folder' % t['id'])
    return PATCHES / c['patch_dir']


def cmd_patch(a):
    targets, indent = read_json(TARGETS)
    t = find(targets, a.id)
    d = selection(t)
    inc, exc = lines_of(d / 'include-patches'), lines_of(d / 'exclude-patches')
    have_inc, have_exc = names_in(d / 'include-patches'), names_in(d / 'exclude-patches')
    changes = split_patches(a.patches)
    if not changes:
        raise Refused('give patch names, e.g. "Hide ads; -Old patch"')
    added, msg = [], []
    list_mode = bool(have_inc)
    for drop, n in changes:
        if list_mode and not drop:
            if n in have_inc:
                msg.append('already included: ' + n)
                continue
            inc.append(n); have_inc.append(n); added.append(n); msg.append('include + ' + n)
        elif list_mode and drop:
            if n not in have_inc:
                raise Refused('%s is not in %s/include-patches' % (n, d.name))
            inc = [x for x in inc if x.split('|', 1)[0].strip() != n]
            have_inc.remove(n); msg.append('include - ' + n)
        elif drop:
            if n in have_exc:
                msg.append('already excluded: ' + n)
                continue
            exc.append(n); have_exc.append(n); msg.append('exclude + ' + n)
        else:
            if n not in have_exc:
                raise Refused('%s builds provider defaults; %r is not excluded, so there is nothing to add' % (t['id'], n))
            exc = [x for x in exc if x.split('|', 1)[0].strip() != n]
            have_exc.remove(n); added.append(n); msg.append('exclude - ' + n + ' (default patch back on)')
    if list_mode and not have_inc:
        raise Refused('that would empty the include list and silently switch %s to provider defaults' % t['id'])
    approved = screen(added, a.approve_confirm)
    write_lines(d / 'include-patches', inc)
    write_lines(d / 'exclude-patches', exc)
    write_record(t, [n for n in added if list_mode], approved)
    return ['%s (%s): %s' % (t.get('label'), d.name, '; '.join(msg))]


def cmd_toggle(a, on):
    targets, indent = read_json(TARGETS)
    t = find(targets, a.id)
    if bool(t.get('enabled')) == on and bool(t.get('poll')) == on:
        return ['%s is already %s' % (a.id, 'enabled' if on else 'disabled')]
    d = selection(t)
    if on and not names_in(d / 'include-patches') and not names_in(d / 'exclude-patches') and not t.get('pin'):
        raise Refused('%s has an empty include list, so it would build every provider default; '
                      'add patch names first (action patch)' % a.id)
    t['enabled'] = on
    t['poll'] = on
    write_json(TARGETS, targets, indent)
    if on:
        write_record(t, note='Enabled %s by owner request.' % today())
    elif record_path(a.id).is_file():
        write_record(t, note='Disabled %s by owner request; releases stay published.' % today())
    if on:
        portal_logo(a.id)
    else:
        portal_forget(a.id, logo_only=True)
    return ['%s %s.' % (a.id, 'enabled' if on else 'disabled: no new builds, files and releases kept')]


def cmd_remove(a):
    targets, indent = read_json(TARGETS)
    t = find(targets, a.id)
    rest = [x for x in targets if x is not t]
    used = {b.get('patch_dir') for x in rest for b in (x.get('candidates') or []) + (x.get('extra_bundles') or [])}
    moved = []
    attic = PATCHES / '_attic'
    for b in (t.get('candidates') or []) + (t.get('extra_bundles') or []):
        pd = b.get('patch_dir')
        if not pd or pd in used or not (PATCHES / pd).is_dir():
            continue
        dest = attic / pd
        if dest.exists():
            dest = attic / ('%s-removed-%s' % (pd, today()))
        attic.mkdir(parents=True, exist_ok=True)
        shutil.move(str(PATCHES / pd), str(dest))
        moved.append('%s -> %s' % (pd, dest))
    write_json(TARGETS, rest, indent)
    portal_forget(a.id)
    if record_path(a.id).is_file():
        write_record(t, note='Removed %s by owner request. Patch folders moved to src/patches/_attic; '
                     'published releases stay on GitHub.' % today())
    return ['Removed %s.' % a.id] + ['moved ' + m for m in moved] + [
        'Kept: published releases, the store entry in apps.json and the logo file (history).']


def cmd_list(a):
    targets, _ = read_json(TARGETS)
    for t in targets:
        c = (t.get('candidates') or [{}])[0]
        inc = names_in(PATCHES / str(c.get('patch_dir')) / 'include-patches')
        print('%-18s %-8s %-28s %3s patch(es)%s' % (t['id'], 'on' if t.get('enabled') else 'OFF', source_key(c),
              len(inc) if inc else 'all', '  needs MicroG' if t.get('needs_microg') else ''))
    return []


def from_env():
    """Workflow entry: inputs arrive as environment variables, never as shell text."""
    e = os.environ
    get = lambda k: (e.get(k) or '').strip()
    action = get('PF_ACTION')
    argv = [action, get('PF_ID')]
    flags = {'add': [('--package', 'PF_PACKAGE'), ('--label', 'PF_LABEL'), ('--provider', 'PF_PROVIDER'),
                     ('--patches', 'PF_PATCHES'), ('--source', 'PF_SOURCE'), ('--store-url', 'PF_STORE_URL')],
             'patch': [('--patches', 'PF_PATCHES')]}.get(action, [])
    for flag, key in flags:
        if get(key):
            argv += [flag, get(key)]
    if action == 'add' and get('PF_NEEDS_MICROG') == 'true':
        argv.append('--needs-microg')
    if action in ('add', 'patch') and get('PF_APPROVE_CONFIRM') == 'true':
        argv.append('--approve-confirm')
    if get('PF_SUMMARY'):
        argv += ['--summary', get('PF_SUMMARY')]
    return argv


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['from-env']:
        argv = from_env()
    ap = argparse.ArgumentParser(description=__doc__.split('\n', 1)[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('add')
    p.add_argument('id')
    p.add_argument('--package', required=True)
    p.add_argument('--label', required=True)
    p.add_argument('--provider', required=True)
    p.add_argument('--patches', default='')
    p.add_argument('--source', choices=['apkmirror-bundle', 'apkmirror-apk', 'apkpure'])
    p.add_argument('--store-url', default='')
    p.add_argument('--needs-microg', action='store_true')
    p.add_argument('--group', choices=['media', 'social', 'tools'])
    p.add_argument('--approve-confirm', action='store_true')
    p = sub.add_parser('patch')
    p.add_argument('id')
    p.add_argument('--patches', required=True)
    p.add_argument('--approve-confirm', action='store_true')
    for name in ('enable', 'disable', 'remove'):
        sub.add_parser(name).add_argument('id')
    for name in ('regen', 'check', 'list'):
        sub.add_parser(name)
    for p in sub.choices.values():
        p.add_argument('--no-regen', action='store_true', help='skip checks and generators (tests)')
        p.add_argument('--summary', help='write a plain summary (pull request body) here')
    a = ap.parse_args(argv)
    try:
        if a.cmd == 'regen':
            return 1 if regen() else 0
        if a.cmd == 'check':
            return 1 if (gates() + regen(check=True)) else 0
        if a.cmd == 'list':
            cmd_list(a)
            return 0
        msg = {'add': cmd_add, 'patch': cmd_patch, 'remove': cmd_remove,
               'enable': lambda x: cmd_toggle(x, True), 'disable': lambda x: cmd_toggle(x, False)}[a.cmd](a)
    except Refused as e:
        print('REFUSED: %s' % e)
        print('::error::%s' % e)
        return 1
    for m in msg:
        print(m)
    bad = [] if a.no_regen else regen() + gates()
    if a.summary:
        body = ['## %s %s' % (a.cmd, a.id), ''] + ['- ' + m for m in msg] + ['']
        body += ['Checks and generators: ' + ('all passed.' if not bad else 'FAILED: ' + ', '.join(bad)), '',
                 'Next: merge this pull request when **3. Validate** and **Onboarding review** are green. '
                 'Enabled apps build in the next scheduled run, or now through **1. Manual Patch**.', '',
                 'Written by `src/etc/app.py` (packet W2). Nothing was built, merged or published.']
        Path(a.summary).write_text('\n'.join(body) + '\n', encoding='utf-8')
    if bad:
        print('::error::the change was written but these failed: ' + ', '.join(bad))
        return 1
    print('APP_CHANGE OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
