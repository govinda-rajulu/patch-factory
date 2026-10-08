#!/usr/bin/env python3
"""Keep the "1. Manual Patch" target input in .github/workflows/manual-patch.yml honest.

8 Oct 2026 (packet W2): the input is free text, not a dropdown. Workflows cannot edit
workflow files with their own token, so a per-app dropdown made every add or remove of an
app need a hand edit of a workflow; free text keeps "5. Add target" to one run and one
merge. The first step of the build ("Refuse an unknown app id") stops a typo or a disabled
id in seconds, before any secret or download. The ids are listed in docs/APPS.md and by
`python3 src/etc/app.py list`.

  python3 src/etc/dropgen.py           convert an old dropdown to free text (idempotent)
  python3 src/etc/dropgen.py --check   exit 1 if it is a dropdown again or the default is not enabled
"""
import io
import json
import re
import sys

W = '.github/workflows/manual-patch.yml'
DESC = "'App id from src/targets.json, e.g. youtube (list: docs/APPS.md)'"
BLOCK = re.compile(r"(^[ \t]*target:[ \t]*\n[ \t]*description:[ \t]*)('[^'\n]*')([ \t]*\n[ \t]*required:[ \t]*true[ \t]*\n"
                   r"[ \t]*default:[ \t]*')([a-z0-9-]+)('[ \t]*\n([ \t]*)type:[ \t]*)(choice|string)([ \t]*\n)"
                   r"((?:[ \t]*options:[ \t]*\n(?:[ \t]*-[ \t]*'[a-z0-9-]+'[ \t]*\n)+)?)", re.M)


def enabled():
    T = json.load(io.open('src/targets.json', encoding='utf-8'))
    return [t['id'] for t in T if t.get('enabled')]


def main():
    check = '--check' in sys.argv
    s = io.open(W, encoding='utf-8').read()
    ids = enabled()
    if not ids:
        print('::error::no enabled targets in src/targets.json')
        return 4
    hits = list(BLOCK.finditer(s))
    if len(hits) != 1:
        print('::error::cannot find exactly one dispatch target input in %s (found %d)' % (W, len(hits)))
        return 4
    m = hits[0]
    dflt = m[4] if m[4] in ids else ids[0]
    current = m[7] == 'string' and not m[9] and m[2] == DESC and m[4] == dflt
    if current:
        print('target input is free text; default %r is enabled (%d enabled targets)' % (dflt, len(ids)))
        return 0
    if check:
        if m[7] != 'string' or m[9]:
            print('::error::%s target input is a dropdown again; run: python3 src/etc/dropgen.py' % W)
        if m[4] not in ids:
            print("::error::%s default '%s' is not an enabled target; run: python3 src/etc/dropgen.py" % (W, m[4]))
        if m[2] != DESC:
            print('::error::%s target description drifted; run: python3 src/etc/dropgen.py' % W)
        return 1
    s = s[:m.start()] + m[1] + DESC + m[3] + dflt + m[5] + 'string' + m[8] + s[m.end():]
    io.open(W, 'w', encoding='utf-8', newline='\n').write(s)
    print("target input: free text, default '%s'" % dflt)
    return 0


if __name__ == '__main__':
    sys.exit(main())
