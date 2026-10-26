#!/usr/bin/env python3
"""Remove the two repeated blocks from already published release notes (W14, owner ask 11 Oct 2026).

Older structured releases contain repeated safety and help text. New notes keep only
changes, provider notes and one install line; this tool removes those old repeated blocks
without changing the machine-readable release record.

  python3 src/etc/release_tidy.py preview --out PLAN.json
  python3 src/etc/release_tidy.py apply --token TOKEN --backup BACKUP.json [--receipt RECEIPT.json]

Rules: only bodies that carry the [pf-release-v1] marker and hold both blocks in their exact
generated wording change; everything else (legacy notes, edited notes, other shapes) is
counted and left alone. The marker line and every other byte stay identical. apply writes
the old bodies to BACKUP before the first edit, re-reads the full release list, and checks
each edit came back byte-identical. Asset files, tags and dates are not touched.
"""
import argparse, hashlib, json, os, pathlib, re, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'build'))
import release_notes  # noqa: E402

REPO = 'govinda-rajulu/patch-factory'
WEB = 'https://github.com/' + REPO
CHECKS = ('## Checks and limitations\n'
          '- CI checked APK identity, declared minimum Android API, native payloads, applied patch names and its configured signing certificate.\n'
          '- Not phone-tested by this pipeline; not proof of original-publisher authenticity or installed-app compatibility.\n'
          '- Same-version patch-only update delivery in Obtainium remains limited. New build does not necessarily mean a new app version.\n'
          '\n')
HELP = re.compile(r'## Help and stable information\n'
                  r'\[Install, updates, source types and status meanings\]\(' + re.escape(WEB) + r'/blob/[0-9a-f]{40}/docs/guide\.md\)\n'
                  r'No automatic uninstall, import migration or device-protection bypass is required or recommended\.\n')
MARKER = re.compile(release_notes.MARKER)
# Old releases point at the guide on main: their pinned source commit predates the section.



def tidy(body):
    """New body, or (None, why) when this release keeps its notes."""
    if not isinstance(body, str) or not MARKER.search(body):
        return None, 'legacy'
    if body.count(CHECKS) != 1 or len(HELP.findall(body)) != 1:
        return None, 'tidy' if CHECKS not in body and not HELP.search(body) else 'other'
    new = HELP.sub('', body.replace(CHECKS, ''), count=1)
    if MARKER.findall(new) != MARKER.findall(body) or not new.endswith(body[body.rindex('[pf-release-v1]'):]):
        return None, 'other'
    return new, 'change'


def gh(args, stdin=None):
    r = subprocess.run([os.environ.get('PF_GH', 'gh')] + args, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise SystemExit('STOP: gh %s failed: %s' % (' '.join(args[:4]), (r.stderr or '').strip()[:300]))
    return r.stdout


def releases():
    rows, seen = [], set()
    for page in range(1, 101):
        data = json.loads(gh(['api', 'repos/%s/releases?per_page=100&page=%d' % (REPO, page)]))
        if not isinstance(data, list):
            raise SystemExit('STOP: the release list is not a list; nothing changed')
        for r in data:
            if not isinstance(r, dict) or type(r.get('id')) is not int or r['id'] in seen:
                raise SystemExit('STOP: invalid or duplicate release row; nothing changed')
            seen.add(r['id'])
            rows.append(r)
        if len(data) < 100:
            return rows
    raise SystemExit('STOP: more than 10000 releases; nothing changed')


def plan(rows):
    out = {'change': [], 'counts': {'change': 0, 'tidy': 0, 'legacy': 0, 'other': 0}}
    for r in sorted(rows, key=lambda x: x['id']):
        new, why = tidy(r.get('body'))
        out['counts'][why] += 1
        if why == 'change':
            out['change'].append({'id': r['id'], 'tag': r.get('tag_name'), 'old': r['body'], 'new': new,
                                  'saved': len(r['body'].encode()) - len(new.encode())})
        elif why == 'other':
            out.setdefault('other_tags', []).append(r.get('tag_name'))
    canonical = json.dumps(out['change'], sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    out['token'] = hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]
    return out


def summary(p):
    c = p['counts']
    return ('TIDY %d release note(s) lose the repeated blocks (%d bytes); %d already tidy, %d legacy, %d other shape (kept)'
            % (c['change'], sum(x['saved'] for x in p['change']), c['tidy'], c['legacy'], c['other'])
            + ' TOKEN ' + p['token'])


def write(path, data):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=1, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=('preview', 'apply'))
    ap.add_argument('--token')
    ap.add_argument('--out')
    ap.add_argument('--backup')
    ap.add_argument('--receipt')
    a = ap.parse_args(argv)
    p = plan(releases())
    if a.mode == 'preview':
        if a.out:
            write(a.out, p)
        print(summary(p))
        return 0
    if not a.token:
        raise SystemExit('STOP: apply needs --token from preview; nothing changed')
    if a.token != p['token']:
        print(summary(p))
        raise SystemExit('STOP: token %s does not match the live plan (%s); GitHub changed since the preview. Nothing changed.' % (a.token, p['token']))
    if not a.backup:
        raise SystemExit('STOP: apply needs --backup; nothing changed')
    write(a.backup, [{'id': x['id'], 'tag': x['tag'], 'body': x['old']} for x in p['change']])
    done = []
    for x in p['change']:
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump({'body': x['new']}, f)
        try:
            back = json.loads(gh(['api', '-X', 'PATCH', 'repos/%s/releases/%d' % (REPO, x['id']), '--input', f.name]))
        finally:
            os.unlink(f.name)
        if back.get('body') != x['new']:
            raise SystemExit('STOP: release %s came back different after %d edit(s); backup %s' % (x['tag'], len(done), a.backup))
        done.append(x['tag'])
    after = plan(releases())
    if after['counts']['change']:
        raise SystemExit('STOP: %d release(s) still carry the blocks after apply; backup %s' % (after['counts']['change'], a.backup))
    if a.receipt:
        write(a.receipt, {'edited': done, 'after': after['counts']})
    print('APPLIED %d edit(s); re-read: %d to change, %d tidy, %d legacy, %d other' % (
        len(done), after['counts']['change'], after['counts']['tidy'], after['counts']['legacy'], after['counts']['other']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
