"""Scenario tests for W15g ZIP/APK content invariants.

These tests deliberately exercise the content-only verifier without an Android SDK.  The
few known failures are retained as red tests so a contract regression is visible.
"""
import hashlib
import json
import os
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / 'src' / 'build'))
import artifact_identity as ai
import sign_apk

REPORT = ROOT.parent / 'A-REPORT.md'


def _enc(name, flags):
    return name.encode('utf-8' if flags & 0x800 else 'cp437')


def raw_zip(path, rows):
    """Write a ZIP with controllable names, methods, flags, descriptors and extras."""
    path.parent.mkdir(parents=True, exist_ok=True)
    out = bytearray(); central = []; locations = {}
    for row in rows:
        name = row['name']; data = row.get('data', b''); flags = row.get('flags', 0)
        method = row.get('method', 0); local_extra = row.get('local_extra', b'')
        central_extra = row.get('central_extra', local_extra)
        name_b = _enc(name, flags)
        if method == 8:
            co = zlib.compressobj(6, zlib.DEFLATED, -15)
            payload = co.compress(data) + co.flush()
        else:
            payload = data
        crc = zlib.crc32(data) & 0xffffffff
        descriptor = bool(flags & 0x08)
        local_crc = row.get('local_crc', 0 if descriptor else crc)
        local_csize = row.get('local_csize', 0 if descriptor else len(payload))
        local_usize = row.get('local_usize', 0 if descriptor else len(data))
        # All local extra fields are supplied by the scenario; alignment padding is
        # represented as a 0xD935 field, like real APK zipalign output.
        offset = len(out)
        struct.pack_into if False else None
        out += struct.pack('<IHHHHHIIIHH', 0x04034b50, 20, flags, method, 0, 0,
                           local_crc, local_csize, local_usize, len(name_b), len(local_extra))
        out += name_b + local_extra + payload
        if descriptor:
            out += struct.pack('<IIII', 0x08074b50, crc, len(payload), len(data))
        locations[name] = {'local_header': offset, 'data': offset + 30 + len(name_b) + len(local_extra),
                           'payload_len': len(payload), 'name_b': name_b}
        central.append((name, name_b, flags, method, crc, len(payload), len(data), central_extra, offset,
                        row.get('external_attr', 0)))
    cd_offset = len(out)
    for name, name_b, flags, method, crc, csize, usize, extra, offset, external in central:
        out += struct.pack('<IHHHHHHIIIHHHHHII', 0x02014b50, 20, 20, flags, method, 0, 0,
                           crc, csize, usize, len(name_b), len(extra), 0, 0, 0, external, offset)
        out += name_b + extra
    cd_size = len(out) - cd_offset
    out += struct.pack('<IHHHHIIH', 0x06054b50, 0, 0, len(central), len(central), cd_size, cd_offset, 0)
    path.write_bytes(out)
    return locations


def align_extra(current, name, alignment, flags=0):
    name_len = len(_enc(name, flags))
    base = current + 30 + name_len
    pad = (-base) % alignment
    if pad and pad < 4:
        pad += alignment
    return struct.pack('<HH', 0xD935, max(0, pad - 4)) + b'X' * max(0, pad - 4) if pad else b''


def aligned_rows(rows):
    result = []; current = 0
    for row in rows:
        row = dict(row); align = row.pop('alignment', 4)
        extra = align_extra(current, row['name'], align, row.get('flags', 0))
        row['local_extra'] = extra
        row.setdefault('central_extra', extra)
        result.append(row)
        current += 30 + len(_enc(row['name'], row.get('flags', 0))) + len(extra)
        if row.get('method', 0) == 8:
            co = zlib.compressobj(6, zlib.DEFLATED, -15)
            current += len(co.compress(row.get('data', b'')) + co.flush())
        else:
            current += len(row.get('data', b''))
        if row.get('flags', 0) & 8:
            current += 16
    return result


def payload_rows():
    return aligned_rows([
        {'name': 'classes.dex', 'data': b'dex payload', 'alignment': 4},
        {'name': 'lib/arm64-v8a/libdemo.so', 'data': b'native payload', 'alignment': 16384},
        {'name': 'resources.arsc', 'data': b'resources payload', 'alignment': 4},
    ])


def make_pair(root, rows=None, signed_rows=None, signed_append=None, insert_block=False):
    rows = rows or payload_rows()
    unsigned = root / 'unsigned.apk'; signed = root / 'signed.apk'
    raw_zip(unsigned, rows)
    if signed_rows is None:
        shutil.copyfile(unsigned, signed)
    else:
        raw_zip(signed, signed_rows)
    if signed_append:
        append_raw(signed, signed_append)
    if insert_block:
        insert_signing_block(signed, b'APK Sig Block 42' + b'X' * 32)
    return unsigned, signed


def _eocd(data):
    pos = data.rfind(b'PK\x05\x06'); assert pos >= 0
    return pos


def append_raw(path, rows):
    """Append local records at the old CD and add central records, preserving order."""
    data = bytearray(path.read_bytes()); ep = _eocd(data)
    _, _, _, count, _, cd_size, cd_offset, _ = struct.unpack_from('<IHHHHIIH', data, ep)
    old_cd = bytes(data[cd_offset:cd_offset + cd_size]); new_local = bytearray(); additions = []
    for row in rows:
        name = row['name']; flags = row.get('flags', 0); method = row.get('method', 0)
        name_b = _enc(name, flags); payload = row.get('data', b'')
        if method == 8:
            co = zlib.compressobj(6, zlib.DEFLATED, -15); payload = co.compress(payload) + co.flush()
        crc = zlib.crc32(row.get('data', b'')) & 0xffffffff
        extra = row.get('local_extra', b''); off = cd_offset + len(new_local)
        new_local += struct.pack('<IHHHHHIIIHH', 0x04034b50, 20, flags, method, 0, 0, crc,
                                 len(payload), len(row.get('data', b'')), len(name_b), len(extra))
        new_local += name_b + extra + payload
        additions.append((name_b, flags, method, crc, len(payload), len(row.get('data', b'')), extra, off))
    new_cd = bytearray(old_cd)
    for name_b, flags, method, crc, csize, usize, extra, off in additions:
        new_cd += struct.pack('<IHHHHHHIIIHHHHHII', 0x02014b50, 20, 20, flags, method, 0, 0, crc,
                              csize, usize, len(name_b), len(extra), 0, 0, 0, 0, off) + name_b + extra
    new = data[:cd_offset] + new_local + new_cd
    new_ep = cd_offset + len(new_local) + len(new_cd)
    new[ new_ep:new_ep + 22 ] = struct.pack('<IHHHHIIH', 0x06054b50, 0, 0, count + len(additions),
                                              count + len(additions), len(new_cd), cd_offset + len(new_local), 0)
    path.write_bytes(new)


def insert_signing_block(path, block):
    data = bytearray(path.read_bytes()); ep = _eocd(data)
    _, _, _, count, _, cd_size, cd_offset, _ = struct.unpack_from('<IHHHHIIH', data, ep)
    data[cd_offset:cd_offset] = block
    ep += len(block)
    data[ep:ep + 22] = struct.pack('<IHHHHIIH', 0x06054b50, 0, 0, count, count, cd_size,
                                   cd_offset + len(block), 0)
    path.write_bytes(data)


def patch_payload(path, name, old, new):
    data = bytearray(path.read_bytes()); z = zipfile.ZipFile(path); info = z.getinfo(name)
    off = info.header_offset; nlen, elen = struct.unpack_from('<HH', data, off + 26)
    start = off + 30 + nlen + elen; pos = bytes(data).find(old, start, start + info.compress_size)
    assert pos >= 0
    data[pos:pos + len(old)] = new
    path.write_bytes(data)


def patch_local(path, name, field, value):
    data = bytearray(path.read_bytes()); z = zipfile.ZipFile(path); info = next(i for i in z.infolist() if i.filename == name)
    off = info.header_offset
    pos = {'crc': 14, 'method': 8, 'name': 30}[field]
    if field == 'crc': data[off + pos:off + pos + 4] = struct.pack('<I', value)
    elif field == 'method': data[off + pos:off + pos + 2] = struct.pack('<H', value)
    else:
        nb = _enc(value, info.flag_bits); assert len(nb) == info.filename.encode('utf-8' if info.flag_bits & 0x800 else 'cp437').__len__()
        data[off + pos:off + pos + len(nb)] = nb
    path.write_bytes(data)


def patch_local_extra(path, name):
    data = bytearray(path.read_bytes()); z = zipfile.ZipFile(path); info = next(i for i in z.infolist() if i.filename == name)
    off = info.header_offset; nlen, elen = struct.unpack_from('<HH', data, off + 26)
    if elen:
        p = off + 30 + nlen
        data[p:p + elen] = bytes((x ^ 0x5A) for x in data[p:p + elen])
    path.write_bytes(data)


def patch_central_size(path, name, extra_size, local=True):
    data = bytearray(path.read_bytes()); ep = _eocd(data)
    _, _, _, count, _, cd_size, cd_offset, _ = struct.unpack_from('<IHHHHIIH', data, ep)
    p = cd_offset
    for _ in range(count):
        assert data[p:p + 4] == b'PK\x01\x02'
        nlen, elen, clen = struct.unpack_from('<HHH', data, p + 28)
        n = bytes(data[p + 46:p + 46 + nlen]).decode('utf8' if data[p + 9] & 8 else 'cp437')
        if n == name:
            old = struct.unpack_from('<I', data, p + 20)[0]
            struct.pack_into('<I', data, p + 20, old + extra_size)
            struct.pack_into('<I', data, p + 24, old + extra_size)
            if local:
                zi = zipfile.ZipFile(path).getinfo(name); struct.pack_into('<I', data, zi.header_offset + 18, old + extra_size)
                struct.pack_into('<I', data, zi.header_offset + 22, old + extra_size)
            path.write_bytes(data); return
        p += 46 + nlen + elen + clen
    raise AssertionError(name)


def content_check(unsigned, signed):
    proof = sign_apk.compare(unsigned, signed)
    ai.require(proof['alignment']['signed']['four_byte'], 'signed APK is not 4-byte aligned')
    ai.require(proof['alignment']['signed']['library_16k'] or not proof['alignment']['unsigned']['library_16k'],
               'signing lost 16 KiB native library alignment')
    return proof


def observed(fn):
    try:
        fn(); return 'accept', 'no exception (accepted)'
    except Exception as e:
        return 'refuse', type(e).__name__ + ': ' + str(e)


class ScenarioZipContracts(unittest.TestCase):
    results = []

    @classmethod
    def tearDownClass(cls):
        lines = ['# W15g packet: ZIP/APK scenario report', '',
                 '| ID | Shape | Expected | Actual | Result |', '|---|---|---|---|---|']
        for r in cls.results:
            result = 'PASS' if r['actual'] == r['expected'] else 'FINDING'
            lines.append('| %s | %s | %s | %s | %s |' % (r['id'], r['shape'], r['expected'], r['actual'], result))
        findings = [r for r in cls.results if r['actual'] != r['expected']]
        lines += ['', '## Findings', '']
        if not findings:
            lines.append('None.')
        for r in findings:
            lines += ['### %s — %s' % (r['id'], r['severity']), '',
                      '- **Evidence:** `%s` → `%s`' % (r['command'], r['detail']),
                      '- **Smallest fix:** %s' % r['fix'], '']
        REPORT.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    def run_scenario(self, ident, shape, expected, fn, severity='HIGH', fix='No fix required.', command='python3 -m unittest discover -s tests -p scenario_zip_contracts.py'):
        actual, detail = observed(fn)
        self.__class__.results.append({'id': ident, 'shape': shape, 'expected': expected, 'actual': actual,
                                       'severity': severity, 'detail': detail or 'completed', 'fix': fix,
                                       'command': command})

    def test_01_legit_shapes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # Data descriptors, zero stored file, directory, existing extra, UTF-8,
            # cp437 and uppercase .SO all in one realistic APK.
            rows = aligned_rows([
                {'name': 'classes.dex', 'data': b'dex', 'flags': 0x08, 'alignment': 4},
                {'name': 'empty.bin', 'data': b'', 'alignment': 4},
                {'name': 'res/', 'data': b'', 'alignment': 4},
                {'name': 'META-INF/services/com.example.Service', 'data': b'impl\n', 'alignment': 4},
                {'name': 'META-INF/app.version', 'data': b'1\n', 'alignment': 4},
                {'name': 'café.txt', 'data': 'utf8'.encode(), 'flags': 0x800, 'alignment': 4},
                {'name': 'café-cp437.txt', 'data': b'cp437', 'flags': 0, 'alignment': 4},
                {'name': 'lib/arm64-v8a/UPPER.SO', 'data': b'so', 'alignment': 16384},
                {'name': 'lib/arm64-v8a/compressed.so', 'data': b'compressed so', 'method': 8, 'alignment': 4},
            ])
            # cp437 name is representable; UTF-8 rows are explicitly flagged.
            u, s = make_pair(root, rows)
            self.run_scenario('L01', 'descriptor/zero/dir/UTF8/CP437/.SO/compressed SO', 'accept', lambda: content_check(u, s))

    def test_02_zip64_large_count(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); rows = []
            # zipfile emits ZIP64 EOCD once the entry count exceeds 65535.
            p = root / 'large.apk'
            with zipfile.ZipFile(p, 'w', allowZip64=True) as z:
                for i in range(65536):
                    name = 'f%05d' % i; info = zipfile.ZipInfo(name); info.compress_type = zipfile.ZIP_STORED
                    cur = z.fp.tell() + 30 + len(name)
                    pad = (-cur) % 4
                    if pad: info.extra = struct.pack('<HH', 0xD935, pad - 4) + b'X' * max(0, pad - 4)
                    z.writestr(info, b'')
            u = root / 'unsigned.apk'; shutil.copyfile(p, u); s = root / 'signed.apk'; shutil.copyfile(p, s)
            # Keep the large-count case focused on ZIP64 parsing; identical signed bytes are valid content.
            self.run_scenario('L02', 'ZIP64 / 65536 zero-length stored entries', 'accept', lambda: content_check(u, s), command='python3 -m unittest discover -s tests -p scenario_zip_contracts.py -k zip64')

    def test_03_signing_metadata_shapes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base = aligned_rows([
                {'name': 'classes.dex', 'data': b'dex payload', 'alignment': 4},
                {'name': 'lib/arm64-v8a/libdemo.so', 'data': b'native payload', 'alignment': 16384},
                {'name': 'resources.arsc', 'data': b'resources payload', 'alignment': 4},
                {'name': 'META-INF/CERT.RSA', 'data': b'old rsa', 'alignment': 4},
                {'name': 'META-INF/CERT.SF', 'data': b'old sf', 'alignment': 4},
                {'name': 'META-INF/MANIFEST.MF', 'data': b'Manifest-Version: 1.0\nName: classes.dex\n', 'alignment': 4},
                {'name': 'META-INF/services/x', 'data': b'provider', 'alignment': 4},
                {'name': 'META-INF/app.version', 'data': b'2', 'alignment': 4},
            ])
            # v2-only: stale signature files unchanged; signing block before CD.
            u, s = make_pair(root / 'v2', base, insert_block=True)
            self.run_scenario('L03', 'v2-only block insertion; stale RSA/SF/MANIFEST unchanged; services/version compared', 'accept', lambda: content_check(u, s))
            # v1: old signature files are replaced and appended (deflated), with no duplicate names.
            old = base; new = aligned_rows([
                {'name': 'classes.dex', 'data': b'dex payload', 'alignment': 4},
                {'name': 'lib/arm64-v8a/libdemo.so', 'data': b'native payload', 'alignment': 16384},
                {'name': 'resources.arsc', 'data': b'resources payload', 'alignment': 4},
                {'name': 'META-INF/services/x', 'data': b'provider', 'alignment': 4},
                {'name': 'META-INF/app.version', 'data': b'2', 'alignment': 4},
                {'name': 'META-INF/MANIFEST.MF', 'data': b'new manifest', 'method': 8, 'alignment': 4},
                {'name': 'META-INF/CERT.SF', 'data': b'new sf', 'method': 8, 'alignment': 4},
                {'name': 'META-INF/CERT.RSA', 'data': b'new rsa', 'method': 8, 'alignment': 4},
            ])
            u2, s2 = make_pair(root / 'v1', old, signed_rows=new)
            self.run_scenario('L04', 'v1 replacement of stale signature files, appended and deflated', 'accept', lambda: content_check(u2, s2))
            # Rewriting only the local extra-field padding is explicitly tolerated.
            u3, s3 = make_pair(root / 'extra', payload_rows()); patch_local_extra(s3, 'classes.dex')
            self.run_scenario('L05', 'apksigner rewrites only local extra-field padding', 'accept', lambda: content_check(u3, s3))

    def test_04_bad_signings(self):
        cases = []
        def add(ident, shape, mutate, fix='Validate the corresponding central/local ZIP invariant before accepting the signer output.', severity='BLOCKER'):
            cases.append((ident, shape, mutate, fix, severity))
        add('B01', 'changed entry bytes', lambda u, s: patch_payload(s, 'classes.dex', b'dex payload', b'BAD payload'), severity='BLOCKER')
        add('B02', 'changed method', lambda u, s: patch_local(s, 'classes.dex', 'method', 8), severity='BLOCKER')
        add('B03', 'CRC changed in local header only (data descriptor)', lambda u, s: patch_local(s, 'classes.dex', 'crc', 0xDEADBEEF), severity='BLOCKER')
        add('B04', 'local header name differs from central directory', lambda u, s: patch_local(s, 'classes.dex', 'name', 'classes.dax'), severity='BLOCKER')
        add('B05', 'dropped non-signature entry', lambda u, s: None, severity='BLOCKER')
        add('B06', 'added non-signature entry', lambda u, s: append_raw(s, [{'name': 'assets/added.bin', 'data': b'added'}]), severity='BLOCKER')
        add('B07', 'reordered entries', lambda u, s: None, severity='BLOCKER')
        add('B08', 'duplicate names', lambda u, s: append_raw(s, [{'name': 'classes.dex', 'data': b'copy'}]), severity='BLOCKER')
        add('B09', 'entry renamed by case only', lambda u, s: None, severity='BLOCKER')
        add('B10', 'META-INF/X.SF hides dex-like payload', lambda u, s: append_raw(s, [{'name': 'META-INF/X.SF', 'data': b'dex\x0a0359\x00'}]), severity='BLOCKER', fix='Do not trust the filename regex alone: authenticate newly added signature files and reject unverified signature-like payloads.')
        add('B11', 'META-INF/sub/x.RSA must not be excluded', lambda u, s: append_raw(s, [{'name': 'META-INF/sub/x.RSA', 'data': b'payload'}]), severity='BLOCKER', fix='Keep the regex anchored to exactly one META-INF path component and compare this payload.')
        add('B12', 'lost 4-byte alignment', lambda u, s: None, severity='BLOCKER')
        add('B13', 'lost 16 KiB .so alignment', lambda u, s: None, severity='BLOCKER')
        add('B14', 'truncated entry', lambda u, s: patch_central_size(s, 'classes.dex', 100, local=True), severity='BLOCKER')
        add('B15', 'overlapping entries', lambda u, s: None, severity='BLOCKER', fix='Reject overlapping local data ranges after parsing each local header.')
        for ident, shape, mutate, fix, sev in cases:
            with self.subTest(ident=ident):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td)
                    if ident == 'B03':
                        desc = aligned_rows([{'name': 'classes.dex', 'data': b'dex payload', 'flags': 0x08, 'alignment': 4},
                                             {'name': 'lib/arm64-v8a/libdemo.so', 'data': b'native payload', 'alignment': 16384},
                                             {'name': 'resources.arsc', 'data': b'resources payload', 'alignment': 4}])
                        u, s = make_pair(root, desc)
                    else:
                        u, s = make_pair(root)
                    if ident == 'B05':
                        raw_zip(s, aligned_rows([{'name': 'classes.dex', 'data': b'dex', 'alignment': 4},
                                                  {'name': 'resources.arsc', 'data': b'resources payload', 'alignment': 4}]))
                    elif ident == 'B07':
                        raw_zip(s, list(reversed(payload_rows())))
                    elif ident == 'B09':
                        raw_zip(s, aligned_rows([{'name': 'classes.DEX', 'data': b'dex payload', 'alignment': 4},
                                                  {'name': 'lib/arm64-v8a/libdemo.so', 'data': b'native payload', 'alignment': 16384},
                                                  {'name': 'resources.arsc', 'data': b'resources payload', 'alignment': 4}]))
                    elif ident == 'B12':
                        raw_zip(s, [{'name': 'classes.dex', 'data': b'dex'}, {'name': 'lib/arm64-v8a/libdemo.so', 'data': b'native payload'}])
                    elif ident == 'B13':
                        raw_zip(s, aligned_rows([{'name': 'classes.dex', 'data': b'dex', 'alignment': 4},
                                                  {'name': 'lib/arm64-v8a/libdemo.so', 'data': b'native payload', 'alignment': 4},
                                                  {'name': 'resources.arsc', 'data': b'resources payload', 'alignment': 4}]))
                    elif ident == 'B15':
                        # Make classes.dex's declared range include the following local header/data.
                        raw_zip(s, payload_rows()); patch_central_size(s, 'classes.dex', 0)
                        z = zipfile.ZipFile(s); a = z.getinfo('classes.dex'); b = z.getinfo('lib/arm64-v8a/libdemo.so')
                        data = bytearray(s.read_bytes()); overlap = (b.header_offset + 30 + len(b.filename.encode()) + len(b.extra) + b.compress_size) - a.header_offset - 30 - len(a.filename.encode()) - len(a.extra)
                        # Keep local and central sizes in agreement for the first entry.
                        patch_central_size(s, 'classes.dex', overlap, local=True)
                    if ident not in ('B05', 'B07', 'B09', 'B12', 'B13', 'B15'):
                        mutate(u, s)
                    self.run_scenario(ident, shape, 'refuse', lambda u=u, s=s: content_check(u, s), sev, fix)

    def test_05_manifest_and_regex_judgment(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base = aligned_rows([{'name': 'classes.dex', 'data': b'dex payload', 'alignment': 4}, {'name': 'lib/arm64-v8a/libdemo.so', 'data': b'native payload', 'alignment': 16384}, {'name': 'resources.arsc', 'data': b'resources payload', 'alignment': 4}, {'name': 'META-INF/MANIFEST.MF', 'data': b'Manifest-Version: 1.0\nX-Runtime-Payload: old\n', 'alignment': 4}])
            changed = aligned_rows([{'name': 'classes.dex', 'data': b'dex payload', 'alignment': 4}, {'name': 'lib/arm64-v8a/libdemo.so', 'data': b'native payload', 'alignment': 16384}, {'name': 'resources.arsc', 'data': b'resources payload', 'alignment': 4}, {'name': 'META-INF/MANIFEST.MF', 'data': b'Manifest-Version: 1.0\nX-Runtime-Payload: changed\n', 'alignment': 4}])
            u, s = make_pair(root / 'manifest', base, signed_rows=changed)
            self.run_scenario('J01', 'non-signature META-INF/MANIFEST.MF changed', 'refuse', lambda: content_check(u, s), 'BLOCKER', 'Classify MANIFEST.MF by authenticated signing context; do not blanket-exclude arbitrary runtime-readable manifest payloads.')
            u2, s2 = make_pair(root / 'sig', payload_rows(), signed_append=[{'name': 'META-INF/SIG-custom', 'data': b'payload', 'method': 8}])
            self.run_scenario('J02', 'META-INF/SIG-* name', 'accept', lambda: content_check(u2, s2), 'LOW', 'SIG-* is an apksig signature-file convention; retain the anchored, case-insensitive match but authenticate its contents.')

    def test_06_zipalign_check_logic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); u, s = make_pair(root, payload_rows())
            tool = root / 'zipalign'; tool.write_text('#!/usr/bin/env python3\nimport sys\nsys.exit(1 if "FAIL" in sys.argv[-1] else 0)\n'); tool.chmod(0o755)
            env = {'ANDROID_HOME': str(root)}
            # sdk_tools needs build-tools/<ver>/zipalign.
            sdktool = root / 'build-tools' / '35.0.0' / 'zipalign'; sdktool.parent.mkdir(parents=True); shutil.copy(tool, sdktool); sdktool.chmod(0o755)
            self.run_scenario('Z01', 'zipalign -c 4 success and 16K preservation check', 'accept', lambda: sign_apk.zipalign_check(u, s, env))
            bad = root / 'signed-FAIL.apk'; shutil.copy(s, bad)
            self.run_scenario('Z02', 'zipalign -c 4 failure', 'refuse', lambda: sign_apk.zipalign_check(u, bad, env), 'BLOCKER', 'Keep the mandatory zipalign -c 4 result gate.')


    def test_99_expected_contracts(self):
        mismatches = [r for r in self.results if r['actual'] != r['expected']]
        self.assertFalse(mismatches, 'known findings: ' + '; '.join(r['id'] + '=' + r['actual'] for r in mismatches))

if __name__ == '__main__':
    unittest.main()
