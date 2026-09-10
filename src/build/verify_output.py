#!/usr/bin/env python3
"""Structural final-output gate; signature/device checks remain separate."""
import pathlib
import sys
import zipfile


def verify(root=pathlib.Path('.')):
    files = list((root / 'release').glob('*.apk'))
    if len(files) != 1 or not files[0].name.endswith('-arm64-v8a.apk'):
        raise ValueError('need exactly one arm64 output APK')
    p = files[0]
    if p.stat().st_size <= 1000000:
        raise ValueError('output APK too small')
    with zipfile.ZipFile(p) as z:
        names = z.namelist()
        if len(names) != len(set(names)):
            raise ValueError('duplicate output ZIP members')
        if 'AndroidManifest.xml' not in names or 'classes.dex' not in names:
            raise ValueError('output missing manifest or primary dex')
        if z.testzip() is not None:
            raise ValueError('output APK CRC failed')
    print('OUTPUT STRUCTURE OK: ' + p.name)


if __name__ == '__main__':
    try:
        verify()
    except (ValueError, OSError, zipfile.BadZipFile) as e:
        print('::error::output verification: ' + str(e), file=sys.stderr)
        sys.exit(1)
