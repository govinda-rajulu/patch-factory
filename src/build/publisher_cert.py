#!/usr/bin/env python3
"""S2 publisher pins, observe first (packet W13, 10 Oct 2026).

Reads the store download's ORIGINAL signing certificate, before any merge re-packs it:
the base APK inside download/<apk_name>.apkm or .xapk, or download/<apk_name>.apk itself.
  * src/build/PUBLISHERS.json pins the package (sha256 list): a certificate outside the
    list fails the build (PUBLISHER_MISMATCH). A store or mirror that re-signed the app is
    exactly what this catches.
  * Not pinned yet: prints PUBLISHER_CERT for the log and passes. The next packet seeds
    the pins from these lines (pf-t1 collects them), so no fingerprint comes from a web page.
An unreadable original prints PUBLISHER_CERT_UNREADABLE and passes, pinned or not: the
existing package, variant and patcher gates still decide, and a fallback receipt
(source_fallback.py) already checks its own signer.
Usage: publisher_cert.py TARGET_ID
"""
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import artifact_identity as identity  # noqa: E402


def original(root, t, work):
    d = root / 'download'
    for ext in ('.apkm', '.xapk'):
        box = d / (t['apk_name'] + ext)
        if box.is_file():
            with zipfile.ZipFile(box) as z:
                names = [n for n in z.namelist() if n in ('base.apk', t['package'] + '.apk')]
                if not names:
                    raise ValueError('no base APK inside ' + box.name)
                out = Path(work) / 'base.apk'
                out.write_bytes(z.read(names[0]))
                return out, box.name + ':' + names[0]
    apk = d / (t['apk_name'] + '.apk')
    if apk.is_file():
        return apk, apk.name
    raise ValueError('no downloaded APK')


def check(root, ident, env, signer=identity.original_signer):
    t = identity.target(root, ident)
    pins = {}
    p = root / 'src/build/PUBLISHERS.json'
    if p.is_file():
        pins = json.loads(p.read_text(encoding='utf-8'))
    want = pins.get(t['package'])
    try:
        with tempfile.TemporaryDirectory() as work:
            apk, where = original(root, t, work)
            cert = signer(root, apk, env)['certificate_sha256']
    except Exception as e:  # never hide a mismatch below; only an unreadable original passes
        print('::notice::PUBLISHER_CERT_UNREADABLE %s: %s' % (t['package'], str(e)[:200] if isinstance(e, ValueError) else type(e).__name__))
        return 0
    if want is None:
        print('::notice::PUBLISHER_CERT %s %s (%s; not pinned yet)' % (t['package'], cert, where))
        return 0
    if cert in want:
        print('PUBLISHER_CERT %s %s pinned OK' % (t['package'], cert))
        return 0
    print('::error::PUBLISHER_MISMATCH %s: original certificate %s is not a pinned publisher certificate' % (t['package'], cert))
    return 1


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: publisher_cert.py TARGET_ID', file=sys.stderr)
        sys.exit(2)
    sys.exit(check(Path('.').resolve(), sys.argv[1], os.environ))
