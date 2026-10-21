#!/usr/bin/env python3
"""The provider bundle version shown on the release page, read from the bundle file name.

W15d (owner, 21 Oct 2026): LinkedIn was built from heyymichii v1.2.0-dev.3 but its release
page said "1.2.0": the old pattern kept digits and dots only, so every prerelease suffix
(-dev.3, -beta.1) was dropped and a dev build read like the stable one.
Usage: bundle_version.py FILE.mpp   prints the version, or "unknown".
"""
import re
import sys
from pathlib import Path

PATTERN = re.compile(r'[0-9]+(?:[.][0-9]+)+(?:-[A-Za-z][A-Za-z0-9]*(?:[.][0-9A-Za-z]+)*)?')


def version_of(name):
    stem = Path(name).name
    if stem.endswith('.mpp'):
        stem = stem[:-4]
    found = PATTERN.findall(stem)
    return found[-1] if found else 'unknown'


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: bundle_version.py FILE.mpp', file=sys.stderr)
        sys.exit(2)
    print(version_of(sys.argv[1]))
