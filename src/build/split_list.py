#!/usr/bin/env python3
"""Print the split APKs inside a store bundle before the merge (W15b, 20 Oct 2026).

Facebook 583 code 475614366 merged to 217,689,153 bytes on 17 Oct and 301,471,185 bytes on
19 Oct; the log could not say why. One SPLIT line per inner APK (name, uncompressed bytes)
and one SPLITS total line make the next difference readable. Names and sizes only: no URL,
cookie or file content. Never fails the build: a bundle it cannot read prints SPLITS_UNREADABLE.
Usage: split_list.py FILE.apkm|FILE.xapk
"""
import re
import sys
import zipfile

SAFE = re.compile(r'[A-Za-z0-9._-]{1,120}')


def main(path):
    try:
        with zipfile.ZipFile(path) as z:
            rows = [(i.filename, i.file_size) for i in z.infolist() if i.filename.endswith('.apk')]
    except (OSError, zipfile.BadZipFile) as error:
        print('SPLITS_UNREADABLE %s' % type(error).__name__)
        return 0
    for name, size in sorted(rows):
        print('SPLIT %s %d' % (name if SAFE.fullmatch(name) else 'unsafe-name', size))
    print('SPLITS count=%d bytes=%d' % (len(rows), sum(s for _, s in rows)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]) if len(sys.argv) == 2 else 2)
