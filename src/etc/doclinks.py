#!/usr/bin/env python3
"""W17a: every relative Markdown link in the repository must resolve (Sustain check).

Checks inline links `[text](target)` in tracked *.md files, outside fenced code and inline
code. External links (scheme:), pure anchors and empty targets are skipped; the anchor part
of a target is not checked. Usage: doclinks.py [--check]. Exit 1 when a link is broken.
"""
import os
import posixpath
import re
import subprocess
import sys

LINK = re.compile(r'\]\(([^)\s]+)\)')
FENCE = re.compile(r'```.*?```', re.S)
CODE = re.compile(r'`[^`\n]*`')


def tracked(root):
    out = subprocess.run(['git', 'ls-files', '-z', '*.md'], cwd=root, capture_output=True, check=True).stdout
    return sorted(p for p in out.decode('utf-8').split('\0') if p)


def broken(root):
    bad = []
    real = os.path.realpath(root)
    for f in tracked(root):
        with open(os.path.join(root, f), encoding='utf-8') as fh:
            text = CODE.sub('', FENCE.sub('', fh.read()))
        for m in LINK.finditer(text):
            t = m.group(1)
            if re.match(r'^[a-z][a-z0-9+.-]*:', t, re.I) or t.startswith(('#', '<')):
                continue
            path = t.split('#', 1)[0]
            if not path:
                continue
            target = posixpath.normpath(posixpath.join(posixpath.dirname(f), path))
            full = os.path.realpath(os.path.join(real, target))
            # W17a review: absolute targets and links that leave the checkout (.., symlinks) are broken.
            if (path.startswith('/') or target.startswith('..') or not (full == real or full.startswith(real + os.sep))
                    or not os.path.exists(full)):
                bad.append((f, t))
    return bad


def main(argv, root='.'):
    bad = broken(root)
    for f, t in bad[:50]:
        print('::error file=%s::broken relative link: %s' % (f, t[:160]))
    if bad:
        print('DOC_LINKS_BROKEN %d' % len(bad))
        return 1
    print('DOC_LINKS_OK %d Markdown files' % len(tracked(root)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
