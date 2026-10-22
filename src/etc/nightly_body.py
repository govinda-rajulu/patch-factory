#!/usr/bin/env python3
"""Readable Nightly watch issue body (owner, 22 Oct 2026, packet W15e; docs/review/REPORT-STYLE.md).

Replaces the indented text dump on issue #27. Every report line still reaches the body: known
lines are counted into tables, the rest go to "Other lines". A report over 45000 bytes is not
cut: the body says so and points at the run artifact, as before.

    nightly_body.py render REPORT FINGERPRINT RUN_URL   -> issue body on stdout
    nightly_body.py changes OLD_BODY_FILE NEW_BODY_FILE  -> short "what changed" comment
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import readable

LIMIT = 45000
FOLDER = re.compile(r'^(ok|--|\?\?|~~) ([a-z0-9-]+/[a-z0-9-]+)')


def esc(text):
    return re.sub(r'[\x00-\x1f\x7f]', ' ', text).replace('<', '&lt;').replace('>', '&gt;').replace('@', '&#64;').replace('`', "'")


def parse(text):
    sections, name = {}, 'start'
    for line in text.splitlines():
        if line.startswith('### '):
            name = line[4:].strip()
            sections.setdefault(name, [])
            continue
        sections.setdefault(name, []).append(line.rstrip())
    return sections


def render(text, fingerprint, run_url):
    head = ['<!-- fingerprint: %s -->' % fingerprint]
    tail = ['', 'Run: ' + run_url, '',
            "Full redacted report and structured coverage: this run's nightly-report artifact (30 days).",
            'Execution success does not establish complete provider coverage.']
    if len(text.encode('utf-8')) > LIMIT:
        return '\n'.join(head + ['# Nightly watch', '', 'Report exceeds the issue preview limit. Full report is in the artifact; '
                                 'no tail-only result substituted.'] + tail) + '\n'
    s = parse(text)
    other = []
    ban = [l.strip() for l in s.get('bancheck', []) if l.strip()]
    ban_sum = next((l for l in ban if l.startswith('scanned')), '; '.join(ban) or 'not reported')
    other += [l for l in ban if l != ban_sum]
    tgt = [l.strip() for l in s.get('targets integrity', []) if l.strip()]
    tgt_ok = 'ok' in tgt
    rel = [l.strip() for l in s.get('release coverage', []) if l.strip()]
    released = next((l for l in rel if l.startswith('released:')), 'released: not reported')
    never = next((l for l in rel if l.startswith('never built:')), 'never built: not reported')
    folders, stale, missing, unread = {}, {}, [], []
    for l in s.get('namecheck', []):
        m = FOLDER.match(l.strip())
        if not m:
            if l.strip():
                other.append(l.strip())
            continue
        kind, label = m.groups()
        if kind == 'ok':
            n = re.search(r'\((\d+) include names\)', l)
            folders[label] = int(n.group(1)) if n else None
        elif kind == '~~':
            stale.setdefault(label, []).append(l.split('exclude not offered by provider:', 1)[-1].strip())
        elif kind == '--':
            missing.append(l.strip())
        else:
            unread.append(l.strip())
    room, current = {}, None
    for l in s.get('headroom', []):
        m = re.match(r'^=== (\S+)\s+using (\d+) of (\d+)', l)
        if m:
            current = m.group(1)
            room[current] = dict(used=int(m.group(2)), total=int(m.group(3)), unused=[])
        elif l.strip() and current and re.match(r'^\s+', l):
            room[current]['unused'].append(l.strip())
        elif l.strip():
            other.append(l.strip())
    banned_hits = [l for l in ban if re.search(r'\b[1-9][0-9]* banned', l)]
    needs = len(missing) + len(unread) + len(banned_hits) + (0 if tgt_ok or not tgt else 1)
    L = head + readable.headline('Nightly watch', 'NEEDS YOU' if needs else 'OK', needs)
    L += readable.table(['Check', 'Result'], [
        ['Banned / confirm scan', esc(ban_sum)],
        ['Targets integrity', 'ok' if tgt_ok else esc('; '.join(tgt) or 'not reported')],
        ['Release coverage', esc(released.split('[')[0].strip()) + '; ' + esc(never)],
        ['Patch names', '%d folder(s) ok, %d missing name(s), %d unreadable; %d stale exclude(s) in %d folder(s) (harmless)'
         % (len(folders), len(missing), len(unread), sum(len(v) for v in stale.values()), len(stale))],
        ['Headroom', '%d folder(s): %d of %d offered names chosen' % (len(room), sum(r['used'] for r in room.values()),
                                                                    sum(r['total'] for r in room.values()))]])
    if needs:
        L += ['', '## Needs you'] + ['- ' + esc(x) for x in missing + unread + banned_hits]
        if tgt and not tgt_ok:
            L.append('- targets integrity: ' + esc('; '.join(tgt)))
    labels = sorted(set(folders) | set(room) | set(stale))
    if labels:
        L += ['', '## Per folder']
        L += readable.table(['App / folder', 'Chosen', 'Offered', 'Not chosen', 'Banned or confirm among those', 'Stale excludes'], [
            [esc(k), room.get(k, {}).get('used', folders.get(k, '-')), room.get(k, {}).get('total', '-'),
             len(room.get(k, {}).get('unused', [])),
             sum(1 for u in room.get(k, {}).get('unused', []) if u.startswith(('BAN', 'CFM'))), len(stale.get(k, []))]
            for k in labels])
    if stale:
        L += [''] + readable.details('Stale excludes: the provider no longer offers these; the exclude line is harmless',
                                     ['- %s: %s' % (esc(k), ', '.join('`%s`' % esc(n) for n in v)) for k, v in sorted(stale.items())])
    if room:
        rows = []
        for k, r in sorted(room.items()):
            rows += ['- **%s** (using %d of %d): %s' % (esc(k), r['used'], r['total'],
                                                       ', '.join(re.sub(r'\s+', ' ', esc(u)) for u in r['unused']) or 'every offered name is chosen')]
        L += [''] + readable.details('Names offered but not chosen, per folder (BAN = banned, CFM = owner confirms)', rows)
    if rel:
        L += [''] + readable.details('Released app prefixes', ['- ' + esc(l) for l in rel])
    known = {'start', 'bancheck', 'targets integrity', 'release coverage', 'namecheck', 'headroom'}
    for name, lines in s.items():
        if name not in known:
            other += ['[%s] %s' % (name, l.strip()) for l in lines if l.strip()]
        elif name == 'start':
            other += [l.strip() for l in lines if l.strip()]
    if other:
        L += ['', '## Other lines'] + ['- ' + esc(x) for x in other]
    return '\n'.join(L + tail) + '\n'


def main(argv):
    if len(argv) == 4 and argv[0] == 'render':
        sys.stdout.write(render(Path(argv[1]).read_text(encoding='utf-8'), argv[2], argv[3]))
        return 0
    if len(argv) == 3 and argv[0] == 'changes':
        old = Path(argv[1]).read_text(encoding='utf-8') if Path(argv[1]).is_file() else ''
        print('\n'.join(['**Changed since the last report**', ''] + readable.changed_lines(old, Path(argv[2]).read_text(encoding='utf-8'))))
        return 0
    print('usage: nightly_body.py render REPORT FINGERPRINT RUN_URL | changes OLD NEW', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
