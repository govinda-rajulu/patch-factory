#!/usr/bin/env python3
"""W15g signing split: the Sign job's first-party code. No provider code runs here.

place TARGET    no secret: move the downloaded hand-off (handoff/) into this fresh checkout
handoff TARGET  no secret: the unsigned APK and its report are this run's patch-job output
sign TARGET     KEYSTORE_PASS/KEYSTORE_ALIAS only: keystore certificate equals the committed
                pin, then apksigner writes release/<apk> from signing/<apk>; the keystore file
                is deleted before this step ends
verify TARGET   no secret: one signer equal to the pin, the same signature schemes the
                patcher used to write, every non-signature entry byte-identical, alignment kept;
                writes the signed identity report the Publish job reads

Same-run evidence, not isolation from a malicious runner or an independent attestation.
"""
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import zipfile

import artifact_identity as ai

WORK = 'signing'
LIBRARY_PAGE = 16384
# Morphe Patcher 2.x ApkSigner (official source, read 31 Oct 2026): minSdk >= 24 signs with
# v2 only; below 24 apksig defaults (v1 + v2 + v3). Never v4. W15g keeps exactly that.
SCHEMES = ('v1', 'v2', 'v3', 'v3.1', 'v3.2', 'v4')
V2_ONLY = {'v1': False, 'v2': True, 'v3': False, 'v3.1': False, 'v3.2': False, 'v4': False}
LEGACY = {'v1': True, 'v2': True, 'v3': True, 'v3.1': False, 'v3.2': False, 'v4': False}
SCHEME_LINE = re.compile(r'^Verified using (v[0-9]+(?:[.][0-9]+)?) scheme[^:]*: (true|false)$')


def expected_schemes(min_sdk):
    ai.require(type(min_sdk) is int and min_sdk > 0, 'invalid minimum SDK in the unsigned report')
    return dict(V2_ONLY if min_sdk >= 24 else LEGACY)


def scheme_flags(schemes):
    return ['--v1-signing-enabled', str(schemes['v1']).lower(),
            '--v2-signing-enabled', str(schemes['v2']).lower(),
            '--v3-signing-enabled', str(schemes['v3']).lower(),
            '--v4-signing-enabled', 'false']


def parse_schemes(text):
    found = {}
    for line in text.splitlines():
        m = SCHEME_LINE.match(line.strip())
        if m:
            ai.require(m[1] in SCHEMES, 'unknown signature scheme in apksigner output: ' + m[1])
            ai.require(m[1] not in found, 'duplicate scheme line in apksigner output')
            found[m[1]] = m[2] == 'true'
    for key in ('v1', 'v2', 'v3'):
        ai.require(key in found, 'apksigner did not report scheme ' + key)
    return {k: found.get(k, False) for k in SCHEMES}


def report_path(root, ident):
    return root / 'build-evidence' / (ident + '.json')


def read_report(root, ident):
    ai.record(root, 'build-evidence/' + ident + '.json')
    return json.loads(report_path(root, ident).read_text())


def one_apk(root, folder):
    apks = sorted((root / folder).glob('*.apk'))
    ai.require(len(apks) == 1 and not apks[0].is_symlink(), folder + ' needs exactly one regular APK')
    return apks[0]


STAGED = re.compile(r'(?:release/[^/]+[.]apk|release/[.][a-z][a-z-]{0,30}|build-evidence/[^/]+[.]json|shadow-evidence/[^/]+[.]json|src/targets[.]json)')


def place(root, ident, stage):
    """Move a downloaded hand-off artifact into a fresh checkout, refusing anything unexpected.
    A build may run with src/targets.json pinned to the winning candidate (build_attempts.view);
    the carried copy is accepted only if it is the checkout's own bytes or exactly that view."""
    root = pathlib.Path(root).resolve()
    raw = root / stage
    ai.require(not raw.is_symlink() and raw.is_dir(), 'hand-off folder missing or a link')
    stage = raw.resolve()
    ai.require(stage.parent == root, 'hand-off folder outside the checkout')
    files = sorted(str(p.relative_to(stage)) for p in stage.rglob('*') if p.is_file() or p.is_symlink())
    bad = [f for f in files if not STAGED.fullmatch(f) or (stage / f).is_symlink()]
    ai.require(not bad, 'unexpected file in the hand-off: ' + ', '.join(bad[:5]))
    ai.require(any(f.startswith('release/') and f.endswith('.apk') for f in files), 'hand-off has no APK')
    ai.require('build-evidence/' + ident + '.json' in files, 'hand-off has no identity report')
    for folder in ('release', 'build-evidence', 'shadow-evidence', WORK):
        ai.require(not (root / folder).exists(), folder + ' already exists; use a fresh checkout')
    if 'src/targets.json' in files:
        carried = (stage / 'src/targets.json').read_text(encoding='utf-8')
        original = (root / 'src/targets.json').read_text(encoding='utf-8')
        if carried != original:
            report = json.loads((stage / 'build-evidence' / (ident + '.json')).read_text())
            import build_attempts
            ai.require(carried == build_attempts.view_text(original, ident, report['inputs']['winner']),
                       'carried src/targets.json is neither the checkout nor the winning candidate view')
            (root / 'src/targets.json').write_text(carried, encoding='utf-8')
            print('TARGET VIEW: src/targets.json pinned to %s, as in the patch job' % report['inputs']['winner'])
    for f in files:
        if f == 'src/targets.json':
            continue
        dest = root / f
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.replace(stage / f, dest)
    shutil.rmtree(stage)
    print('HANDOFF_PLACED %s files=%d' % (ident, len(files)))


def handoff(root, ident, env):
    """The downloaded patch output is this run's, this commit's and this target's, byte for byte."""
    root = pathlib.Path(root).resolve()
    ai.require(re.fullmatch(r'[a-z0-9-]+', ident) is not None, 'invalid target id')
    d = read_report(root, ident)
    ai.require(d.get('schema') == ai.SCHEMA and d.get('status') == 'unsigned' and d.get('signing_split') is True
               and d.get('target') == ident, 'patch output is not an unsigned split report for this target')
    head = ai.command(['git', 'rev-parse', 'HEAD'], root).decode().strip()
    ai.require(d['inputs']['source_commit'] == head and d['inputs']['target'] == ident,
               'patch output is from another source commit or target')
    ai.require(d['unsigned']['binding'] == ai.run_binding(env),
               'patch output is from another workflow run or attempt (after a failure use Re-run all jobs; '
               'a partial re-run cannot reuse another attempt\'s APK)')
    ai.require(d['inputs']['expected_certificate_sha256'] == ai.pinned_certificate(root), 'signer pin differs from the patch job')
    apk = one_apk(root, 'release')
    rel = 'release/' + apk.name
    ai.require(ai.record(root, rel) == d['output'], 'unsigned APK differs from the patch job report (path, bytes or SHA-256)')
    for name in ('.version', '.tagprefix', '.tagsuffix', '.provider', '.patchver', '.applied'):
        ai.record(root, 'release/' + name)
    print('HANDOFF_OK %s unsigned=%s bytes=%d' % (ident, d['output']['sha256'], d['output']['bytes']))
    return d, apk


def sign(root, ident, env):
    root = pathlib.Path(root).resolve()
    keystore = root / 'src/ks.keystore'
    try:
        d, apk = handoff(root, ident, env)
        ai.require(keystore.is_file() and not keystore.is_symlink(), 'decoded keystore missing')
        ai.check_keystore_pin(root, env)
        work = root / WORK
        ai.require(not work.exists(), 'signing work folder already exists; use a fresh checkout')
        work.mkdir()
        unsigned = work / apk.name
        os.replace(apk, unsigned)
        tools = ai.sdk_tools('apksigner', env)
        ai.require(tools, 'apksigner unavailable')
        schemes = expected_schemes(d['manifest']['min_sdk'])
        # Passwords only through env:NAME (never argv, logs or reports); --out keeps the unsigned
        # input; --alignment-preserved keeps the patcher's 4-byte and 16 KiB library alignment.
        args = [tools[0], 'sign', '--ks', str(keystore), '--ks-key-alias', env['KEYSTORE_ALIAS'],
                '--ks-pass', 'env:KEYSTORE_PASS', '--key-pass', 'env:KEYSTORE_PASS',
                '--alignment-preserved', 'true'] + scheme_flags(schemes) + ['--out', str(apk), str(unsigned)]
        result = subprocess.run(args, cwd=root, env=env, capture_output=True, timeout=600)
        # Never print argv (alias) or raw tool output that could echo it; exit code only.
        ai.require(result.returncode == 0, 'apksigner sign failed (exit %d)' % result.returncode)
        ai.require(apk.is_file() and unsigned.is_file(), 'signed or unsigned APK missing after signing')
        ai.require(not pathlib.Path(str(apk) + '.idsig').exists(), 'unexpected v4 signature file')
        print('SIGNED %s with %s (schemes %s)' % (ident, pathlib.Path(tools[0]).parent.name,
                                                 '+'.join(k for k, v in schemes.items() if v)))
    finally:
        keystore.unlink(missing_ok=True)


def entries(path):
    """Name -> (method, crc, sizes, sha256 of the raw stored bytes), from the central directory."""
    rows = {}
    with zipfile.ZipFile(path) as z, open(path, 'rb') as raw:
        for info in z.infolist():
            ai.require(info.filename not in rows, 'duplicate ZIP entry: ' + info.filename[:120])
            raw.seek(info.header_offset)
            head = raw.read(30)
            ai.require(len(head) == 30 and head[:4] == b'PK\x03\x04', 'bad local header: ' + info.filename[:120])
            name_len, extra_len = int.from_bytes(head[26:28], 'little'), int.from_bytes(head[28:30], 'little')
            local_name = raw.read(name_len)
            central_name = info.orig_filename.encode('utf-8' if info.flag_bits & 0x800 else 'cp437')
            # The local header must name the same entry with the same method as the central directory.
            ai.require(local_name == central_name and int.from_bytes(head[8:10], 'little') == info.compress_type,
                       'local header differs from the central directory: ' + info.filename[:120])
            if not info.flag_bits & 0x08:
                # No data descriptor: the local CRC and sizes are authoritative too.
                ai.require(int.from_bytes(head[14:18], 'little') == info.CRC and
                           int.from_bytes(head[18:22], 'little') in (info.compress_size, 0xFFFFFFFF) and
                           int.from_bytes(head[22:26], 'little') in (info.file_size, 0xFFFFFFFF),
                           'local header sizes differ from the central directory: ' + info.filename[:120])
            start = info.header_offset + 30 + name_len + extra_len
            # Version, flags, method, time, date, CRC and sizes as written in the local header
            # (the extra field may carry alignment padding and is not compared).
            local = hashlib.sha256(head[4:26] + local_name).hexdigest()
            raw.seek(start)
            digest, left = hashlib.sha256(), info.compress_size
            while left:
                chunk = raw.read(min(left, 1 << 20))
                ai.require(chunk, 'truncated ZIP entry: ' + info.filename[:120])
                digest.update(chunk); left -= len(chunk)
            rows[info.filename] = {'method': info.compress_type, 'crc': info.CRC, 'size': info.file_size,
                                   'stored': info.compress_size, 'sha256': digest.hexdigest(), 'local': local,
                                   'offset': start}
    return rows


def alignment(rows):
    four = sorted(n for n, r in rows.items() if r['method'] == zipfile.ZIP_STORED and r['offset'] % 4)
    page = sorted(n for n, r in rows.items() if r['method'] == zipfile.ZIP_STORED and n.lower().endswith('.so')
                  and r['offset'] % LIBRARY_PAGE)
    return {'four_byte': not four, 'library_16k': not page, 'unaligned': (four + page)[:20]}


def compare(unsigned, signed):
    a, b = entries(unsigned), entries(signed)
    plain_a = {n: {k: v for k, v in r.items() if k != 'offset'} for n, r in a.items() if not ai.SIGNATURE_FILE.fullmatch(n)}
    plain_b = {n: {k: v for k, v in r.items() if k != 'offset'} for n, r in b.items() if not ai.SIGNATURE_FILE.fullmatch(n)}
    ai.require(set(plain_a) == set(plain_b), 'signing added or removed a non-signature entry')
    changed = sorted(n for n in plain_a if plain_a[n] != plain_b[n])
    ai.require(not changed, 'signing changed entry bytes: ' + ', '.join(changed[:5]))
    ai.require([n for n in a if n in plain_a] == [n for n in b if n in plain_b], 'signing reordered entries')
    return {'entries_compared': len(plain_a),
            'signature_files': {'unsigned': sorted(n for n in a if n not in plain_a)[:50],
                                'signed': sorted(n for n in b if n not in plain_b)[:50]},
            'alignment': {'unsigned': alignment(a), 'signed': alignment(b)}}


def zipalign_check(unsigned, signed, env):
    """Official checker: 4-byte alignment must pass; 16 KiB library pages (-P 16, build-tools 35+)
    must not be lost by signing."""
    tools = ai.sdk_tools('zipalign', env)
    ai.require(tools, 'zipalign unavailable')
    four = subprocess.run([tools[0], '-c', '4', str(signed)], capture_output=True, timeout=300)
    ai.require(four.returncode == 0, 'signed APK fails zipalign -c 4 (exit %d)' % four.returncode)
    page = [subprocess.run([tools[0], '-c', '-P', '16', '4', str(apk)], capture_output=True, timeout=300).returncode
            for apk in (unsigned, signed)]
    ai.require(page[1] == 0 or page[0] != 0, 'signing lost 16 KiB library alignment (zipalign -c -P 16 4)')
    return {'tool': pathlib.Path(tools[0]).parent.name, 'page16_unsigned': page[0] == 0, 'page16_signed': page[1] == 0}


def verify(root, ident, env):
    root = pathlib.Path(root).resolve()
    ai.require(not (root / 'src/ks.keystore').exists(), 'keystore still present at verification')
    ai.require(not any(k.startswith('KEYSTORE') for k in env), 'signing secret present at verification')
    d = read_report(root, ident)
    ai.require(d.get('status') == 'unsigned' and d.get('signing_split') is True and d.get('target') == ident,
               'report is not the unsigned hand-off for this target')
    ai.require(d['unsigned']['binding'] == ai.run_binding(env), 'report is from another workflow run or attempt')
    signed = one_apk(root, 'release')
    unsigned = one_apk(root, WORK)
    ai.require(signed.name == unsigned.name, 'signed APK name differs from the unsigned one')
    before = ai.record(root, WORK + '/' + unsigned.name)
    ai.require(before['sha256'] == d['output']['sha256'] and before['bytes'] == d['output']['bytes'],
               'unsigned APK changed before verification')
    after = ai.record(root, 'release/' + signed.name)
    ai.require(after['sha256'] != before['sha256'], 'signed APK equals the unsigned bytes')
    tool_path, text = ai.verifier_output(root, signed, env)
    signer = {'certificate_sha256': ai.parse_signers(text), 'verifier': tool_path, 'cryptographic_verification': 'passed'}
    ai.validate_signer(root, signer, d['inputs'])
    schemes = parse_schemes(text)
    want = expected_schemes(d['manifest']['min_sdk'])
    ai.require(schemes == want, 'signature schemes %s differ from the patcher rule %s' % (schemes, want))
    proof = compare(unsigned, signed)
    ai.require(proof['alignment']['signed']['four_byte'], 'signed APK is not 4-byte aligned')
    ai.require(proof['alignment']['signed']['library_16k'] or not proof['alignment']['unsigned']['library_16k'],
               'signing lost 16 KiB native library alignment')
    tool = zipalign_check(unsigned, signed, env)
    meta = ai.metadata(root, signed.resolve(), env)
    # Compare what the APK says, not which reader path printed it (jobs run on separate runners).
    semantic = lambda m: {k: v for k, v in m.items() if k != 'reader'}
    ai.require(semantic(meta) == semantic(d['manifest']), 'signed APK manifest differs from the unsigned APK')
    report = dict(d)
    report.update({'status': 'verified', 'output': after, 'signature': signer,
                   'unsigned_output': d['output'],
                   'signing': {'schemes': schemes, 'binding': d['unsigned']['binding'], 'zipalign': tool,
                               'pin': ai.pinned_certificate(root), **proof}})
    ai.atomic_json(report_path(root, ident), report)
    print('SIGNING_SPLIT_OK %s signer=%s schemes=%s entries=%d unsigned=%s signed=%s library16k=%s' % (
        ident, signer['certificate_sha256'][:12] + '...' + signer['certificate_sha256'][-4:],
        '+'.join(k for k, v in schemes.items() if v), proof['entries_compared'],
        before['sha256'][:12], after['sha256'][:12],
        'yes' if proof['alignment']['signed']['library_16k'] else 'no'))
    return report


def main(argv):
    root = pathlib.Path('.').resolve()
    mode, ident = argv[0], argv[1]
    if mode == 'place':
        place(root, ident, 'handoff')
    elif mode == 'handoff':
        handoff(root, ident, dict(os.environ))
    elif mode == 'sign':
        sign(root, ident, dict(os.environ))
    elif mode == 'verify':
        verify(root, ident, dict(os.environ))
    else:
        raise ValueError('unknown signing mode')


if __name__ == '__main__':
    try:
        if len(sys.argv) != 3:
            raise ValueError('usage: sign_apk.py place|handoff|sign|verify TARGET')
        main(sys.argv[1:])
    except (ValueError, OSError, KeyError, IndexError, TypeError, subprocess.TimeoutExpired, zipfile.BadZipFile) as e:
        print('::error::signing split: ' + str(e), file=sys.stderr)
        sys.exit(1)
