#!/usr/bin/env python3
"""Readable bot reports (owner ask, 22 Oct 2026, packet W15e). Style: docs/review/REPORT-STYLE.md.

Every issue body or comment a bot writes follows one shape, so anyone can read it in a glance:
  1. a title with one status word, then "Needs you:" (nothing, or the count);
  2. a summary table: one row per section, counts not lists;
  3. sections in order of urgency, each a table; long lists fold into <details>;
  4. a rerun edits the body in place; a comment says only what changed since the last run.
Standard library only. Callers escape their own text; cell() also keeps a '|' from breaking a row.
"""
import re


def cell(value, limit=300):
    text = re.sub(r'\s+', ' ', str(value)).strip()
    if len(text) > limit:
        text = text[:limit - 1] + '\u2026'
    return text.replace('|', '&#124;') or '-'


def table(headers, rows):
    """Markdown table lines; rows are sequences of cell values."""
    out = ['| ' + ' | '.join(cell(h) for h in headers) + ' |', '|' + '---|' * len(headers)]
    out += ['| ' + ' | '.join(cell(v) for v in row) + ' |' for row in rows]
    return out


def details(summary, lines):
    """A folded block. GitHub needs the blank lines around markdown inside <details>."""
    if not lines:
        return []
    return ['<details><summary>' + cell(summary) + '</summary>', ''] + list(lines) + ['', '</details>']


def group(items, key):
    """Ordered {key: [items]} keeping first-seen order."""
    out = {}
    for item in items:
        out.setdefault(key(item), []).append(item)
    return out


def names(values, limit=12):
    """`a`, `b`, ... and N more: a short inline list for a table cell."""
    values = list(values)
    shown = ', '.join('`' + v + '`' for v in values[:limit])
    return shown + (' and %d more' % (len(values) - limit) if len(values) > limit else '')


def headline(title, status, needs, happened=None, todo=None):
    """'# Title: STATUS' and three plain lines: what happened, whether the owner must act, what to do.

    W16j (owner, 25 Oct 2026: "I don't want to get dizzy reading"): every report opens the same
    way. The middle line keeps its '**Needs you:**' wording; readers and tests key on it."""
    happened = happened or '%s ran; result %s.' % (title, status)
    todo = todo or ('nothing.' if not needs else 'answer the items below (they are also on the Needs you issue).')
    return ['# %s: %s' % (title, status), '',
            '**What happened:** ' + happened,
            '**Needs you:** ' + ('nothing' if not needs else '%d item(s), listed first below' % needs),
            '**What to do:** ' + todo, '']


def changed_lines(old, new, limit=15):
    """What changed between two rendered bodies, as short +/- bullet lines (for the run comment)."""
    keep = lambda t: [l.strip() for l in (t or '').splitlines()
                      if l.strip() and not l.startswith(('<', '|---', 'http')) and 'fingerprint' not in l]
    before, after = keep(old), keep(new)
    gone = [l for l in before if l not in set(after)]
    came = [l for l in after if l not in set(before)]
    out = ['- now: ' + cell(l, 200) for l in came[:limit]]
    out += ['- before: ' + cell(l, 200) for l in gone[:limit]]
    more = max(0, len(came) - limit) + max(0, len(gone) - limit)
    if more:
        out.append('- and %d more changed line(s); the body has everything' % more)
    return out or ['- no visible change']
