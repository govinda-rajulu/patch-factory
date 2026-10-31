#!/usr/bin/env python3
"""W17a: page-weight budget for the shelf's first load (Sustain check).

Counts what a visit downloads before any data: docs/index.html, docs/portal.js, every
@font-face file whose unicode-range covers Basic Latin (the full fallback font loads only for
other characters), every PNG/SVG under docs/assets that the page references, and the logos.
Status and release JSON are data, not page weight. Usage: page_weight.py [--check].
Raise BUDGET only on purpose, in the same change as the growth (knowledge/style/UI.md).
"""
import os
import re
import sys

BUDGET = 350_000  # bytes; W17a: 433,819 on main b1c34e50, 320,021 after the logo and font work
FACE = re.compile(r'@font-face\{([^}]*)\}')


def first_load(root='.'):
    docs = os.path.join(root, 'docs')
    with open(os.path.join(docs, 'index.html'), encoding='utf-8') as f:
        html = f.read()
    with open(os.path.join(docs, 'portal.js'), encoding='utf-8') as f:
        script = f.read()
    real = os.path.realpath(docs)
    parts = {'docs/index.html': os.path.getsize(os.path.join(docs, 'index.html')),
             'docs/portal.js': os.path.getsize(os.path.join(docs, 'portal.js'))}
    for body in FACE.findall(html):
        src = re.search(r'url\("([^"]+)"\)', body)
        rng = re.search(r'unicode-range:([^;}]+)', body)
        if not src:
            continue
        local = os.path.realpath(os.path.join(docs, src.group(1)))
        # W17a review: only a relative file under docs/ counts; anything else is a page error.
        if src.group(1).startswith('/') or ':' in src.group(1) or not local.startswith(real + os.sep):
            raise ValueError('font URL is not a local docs/ file: ' + src.group(1)[:80])
        latin = rng is None or any(r.strip().upper().startswith('U+0000') for r in rng.group(1).split(','))
        if latin:
            parts['docs/' + src.group(1)] = os.path.getsize(os.path.join(docs, src.group(1)))
    assets = os.path.join(docs, 'assets')
    for dirpath, _, files in os.walk(assets):
        for name in files:
            rel = os.path.relpath(os.path.join(dirpath, name), docs).replace(os.sep, '/')
            if name.endswith('.png') and rel.startswith('assets/logos/'):
                parts['docs/' + rel] = os.path.getsize(os.path.join(dirpath, name))
            elif name.endswith(('.png', '.svg')) and (rel in html or rel in script):
                parts['docs/' + rel] = os.path.getsize(os.path.join(dirpath, name))
    return parts


def main(argv, root='.'):
    parts = first_load(root)
    total = sum(parts.values())
    big = sorted(parts.items(), key=lambda kv: -kv[1])[:5]
    print('PAGE_WEIGHT %d bytes of %d budget (%d files; largest: %s)' % (
        total, BUDGET, len(parts), ', '.join('%s %d' % kv for kv in big)))
    if '--check' in argv and total > BUDGET:
        print('::error::page weight %d bytes is over the %d budget; shrink it or raise BUDGET on purpose '
              '(knowledge/style/UI.md)' % (total, BUDGET))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
