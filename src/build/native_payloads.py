#!/usr/bin/env python3
"""Distinguish native ELF from unchanged packaged data; never infer format from .so."""
import hashlib
import json
import pathlib
import struct
import tempfile
import zipfile
import zlib

# Resource limits are refusal boundaries, not format guesses.
MAX_MEMBER_BYTES = 128 * 1024 * 1024
MAX_EXPANDED_BYTES = 256 * 1024 * 1024
MAX_ENTRIES = 10000
MAX_DEPTH = 3
ZIP_HEADERS = (b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def arm64_elf(header, name):
    require(len(header) >= 20 and header[:4] == b'\x7fELF' and header[4] == 2
            and header[5] == 1 and int.from_bytes(header[18:20], 'little') == 183,
            'native library is not ELF64 AArch64: ' + name)


def member_hash(archive, name):
    digest = hashlib.sha256()
    count = 0
    with archive.open(name) as stream:
        while True:
            block = stream.read(1048576)
            if not block:
                break
            digest.update(block)
            count += len(block)
    require(count == archive.getinfo(name).file_size, 'member size mismatch: ' + name)
    return digest.hexdigest()


def checked_name(name):
    require(not name.startswith('/') and '\\' not in name and '\x00' not in name,
            'unsafe archive member name')
    parts = pathlib.PurePosixPath(name).parts
    require('..' not in parts, 'archive member traversal')


def inspect_zip(stream, budget=None, depth=0):
    if budget is None:
        budget = {'bytes': 0, 'entries': 0}
    require(depth <= MAX_DEPTH, 'packaged ZIP nesting exceeds inspection limit')
    result = {'entries': 0, 'visible_arm64_elf_members': 0,
              'nested_zip_archives': 0, 'other_data_members': 0}
    with zipfile.ZipFile(stream) as archive:
        entries = archive.infolist()
        require(entries and len(entries) == len({i.filename for i in entries}),
                'packaged ZIP empty or has duplicate members')
        budget['entries'] += len(entries)
        require(budget['entries'] <= MAX_ENTRIES, 'packaged ZIP entry limit exceeded')
        for item in entries:
            checked_name(item.filename)
            require(not item.flag_bits & 1, 'encrypted packaged ZIP member is uninspectable')
            require((item.external_attr >> 16) & 0o170000 != 0o120000,
                    'packaged ZIP symlink rejected')
            require(item.file_size <= MAX_MEMBER_BYTES, 'packaged ZIP member too large')
            budget['bytes'] += item.file_size
            require(budget['bytes'] <= MAX_EXPANDED_BYTES, 'packaged ZIP expansion limit exceeded')
            result['entries'] += 1
            if item.is_dir():
                continue
            # Read to EOF for CRC verification. Spill large members to a temporary
            # file; never extract names supplied by the archive onto the filesystem.
            with archive.open(item) as source, tempfile.SpooledTemporaryFile(max_size=8*1024*1024) as copy:
                count = 0
                while True:
                    block = source.read(1048576)
                    if not block:
                        break
                    count += len(block)
                    require(count <= item.file_size and count <= MAX_MEMBER_BYTES,
                            'packaged ZIP member exceeded its declared size')
                    copy.write(block)
                require(count == item.file_size, 'packaged ZIP member truncated')
                copy.seek(0)
                header = copy.read(20)
                copy.seek(0)
                if header.startswith(b'\x7fELF'):
                    arm64_elf(header, item.filename)
                    result['visible_arm64_elf_members'] += 1
                elif header[:4] in ZIP_HEADERS:
                    nested = inspect_zip(copy, budget, depth+1)
                    result['nested_zip_archives'] += 1 + nested['nested_zip_archives']
                    for field in ('visible_arm64_elf_members', 'other_data_members'):
                        result[field] += nested[field]
                else:
                    # Contents may be resources or application-specific compressed
                    # payloads. Do not claim they were decoded or ABI-verified.
                    result['other_data_members'] += 1
    return result


def inspect_dex(blob):
    """Check a standard DEX container, not instruction semantics or runtime safety.

    Layout/checksum ranges: https://source.android.com/docs/core/runtime/dex-format
    Reject unsupported containers rather than treating a .dex.so name as proof.
    SHA-1/Adler-32 are format checks only, not authenticity checks.
    """
    require(112 <= len(blob) <= MAX_MEMBER_BYTES, 'DEX size outside inspection bounds')
    require(blob[:4] == b'dex\n' and blob[7:8] == b'\0'
            and blob[4:7] in (b'035', b'037', b'038', b'039', b'040'),
            'unsupported DEX magic/version')
    words = struct.unpack_from('<20I', blob, 32)
    size, header_size, endian, link_size, link_off, map_off = words[:6]
    require(size == len(blob) and header_size == 112, 'DEX file/header size mismatch')
    require(endian == 0x12345678, 'unsupported DEX endian tag')
    require(struct.unpack_from('<I', blob, 8)[0] == zlib.adler32(blob[12:]),
            'DEX Adler-32 mismatch')
    require(blob[12:32] == hashlib.sha1(blob[32:]).digest(), 'DEX SHA-1 mismatch')
    data_size, data_off = words[18:20]
    require(data_size > 0 and data_off >= 112 and data_off % 4 == 0
            and data_off + data_size == size, 'DEX data bounds invalid')
    # Linked data has unspecified format in AOSP; do not claim to inspect it.
    require(link_size == 0 and link_off == 0, 'linked DEX is unsupported')
    expected = {0: (1, 0)}
    widths = {0: 112, 1: 4, 2: 4, 3: 12, 4: 8, 5: 8, 6: 32, 7: 4, 8: 8}
    ranges = [(0, 112)]
    for kind in range(1, 7):
        count, offset = words[6 + (kind-1)*2:8 + (kind-1)*2]
        require((count == 0) == (offset == 0), 'DEX section count/offset mismatch')
        if count:
            end = offset + count * widths[kind]
            require(offset >= 112 and offset % 4 == 0 and end <= data_off,
                    'DEX fixed section out of bounds')
            ranges.append((offset, end))
            expected[kind] = (count, offset)
    require(data_off <= map_off <= size-4 and map_off % 4 == 0, 'DEX map offset invalid')
    total = struct.unpack_from('<I', blob, map_off)[0]
    require(2 <= total <= 100 and map_off + 4 + total*12 <= size, 'DEX map length invalid')
    known = set(widths) | {0x1000, 0x1001, 0x1002, 0x1003,
                          0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005, 0x2006}
    seen = {}
    previous = -1
    entries = []
    for i in range(total):
        kind, unused, count, offset = struct.unpack_from('<HHII', blob, map_off+4+i*12)
        require(kind in known and kind not in seen and unused == 0 and count > 0,
                'DEX map type/count invalid')
        require(previous < offset < size, 'DEX map offsets unsorted/out of bounds')
        previous = offset
        seen[kind] = (count, offset)
        if kind in widths:
            end = offset + count * widths[kind]
            require(offset % 4 == 0 and end <= (size if kind in (7, 8) else data_off),
                    'DEX map fixed section invalid')
            if kind in (7, 8):
                require(blob[4:7] >= b'038', 'DEX version lacks call-site/method-handle support')
                require(offset >= 112 and (end <= data_off or offset >= data_off),
                        'DEX extended section crosses data boundary')
                if offset < data_off:
                    ranges.append((offset, end))
        else:
            require(offset >= data_off and count <= size-offset, 'DEX map data bounds invalid')
            if kind in (0x1000, 0x1001, 0x1002, 0x1003, 0x2001, 0x2006):
                require(offset % 4 == 0, 'DEX map data alignment invalid')
            end = offset + (4 + total*12 if kind == 0x1000 else count)
        entries.append((offset, end))
    require(seen.get(0x1000) == (1, map_off), 'DEX map self-entry mismatch')
    require({k: v for k, v in seen.items() if k <= 6} == expected,
            'DEX header/map section mismatch')
    ranges.append((data_off, size))
    for sections in (sorted(ranges), entries):
        require(all(a[1] <= b[0] for a, b in zip(sections, sections[1:])),
                'DEX sections overlap')
    return {'version': blob[4:7].decode(), 'file_bytes': size,
            'header_bytes': header_size, 'map_entries': total,
            'adler32_verified': True, 'sha1_verified': True,
            'header_and_map_bounds_checked': True,
            'bytecode_semantics_verified': False,
            'scope': 'container checks only; not a full DEX verifier or runtime safety proof'}


def packaged_data(output, source, name):
    require(source is not None, 'non-ELF member needs a corresponding input APK: ' + name)
    require(source.namelist().count(name) == 1, 'missing/ambiguous corresponding input member: ' + name)
    info = output.getinfo(name)
    require(info.file_size <= MAX_MEMBER_BYTES, 'non-ELF member exceeds inspection limit')
    require(source.getinfo(name).file_size == info.file_size, 'non-ELF member size changed: ' + name)
    before = member_hash(source, name)
    after = member_hash(output, name)
    require(before == after, 'non-ELF member bytes changed during patching: ' + name)
    with output.open(name) as stream:
        header = stream.read(20)
    evidence = {'member': name, 'bytes': info.file_size, 'input_sha256': before,
                'output_sha256': after, 'preserved_from_patcher_input': True}
    if header == b'1.0' and info.file_size == 3:
        # Exact data bytes observed in Prime Video, not a general text/filename bypass.
        evidence.update(format='literal-text-1.0', executable_elf=False)
    elif header == b'release=452' and info.file_size == 11:
        # Full 11 bytes observed in input/output, run 34456028004.
        evidence.update(format='literal-text-release-452', executable_elf=False)
    elif header.startswith(b'dex\n'):
        with output.open(name) as stream:
            blob = stream.read(MAX_MEMBER_BYTES + 1)
        evidence.update(format='dex-container-checked', executable_elf=False,
                        executable_bytecode=True, dex_inspection=inspect_dex(blob))
    elif header[:4] in ZIP_HEADERS:
        with tempfile.SpooledTemporaryFile(max_size=8*1024*1024) as copy:
            with output.open(name) as stream:
                while True:
                    block = stream.read(1048576)
                    if not block:
                        break
                    copy.write(block)
            copy.seek(0)
            evidence.update(format='validated-zip', executable_elf=False,
                            archive_inspection=inspect_zip(copy))
    else:
        raise ValueError('unclassified non-ELF member remains rejected: ' + name)
    evidence['scope'] = 'format and unchanged-byte proof only; not runtime safety or original-publisher authenticity'
    return evidence


def verify_native_payloads(apk, source_apk=None):
    data = []
    failures = []
    elf_count = 0
    with zipfile.ZipFile(apk) as output:
        names = output.namelist()
        require(len(names) == len(set(names)), 'duplicate APK members')
        natives = [n for n in names if n.startswith('lib/') and not n.endswith('/')]
        source = None
        try:
            for name in natives:
                bits = name.split('/')
                require(len(bits) == 3 and bits[1] == 'arm64-v8a', 'non-arm64 native member: ' + name)
                with output.open(name) as stream:
                    header = stream.read(20)
                if header.startswith(b'\x7fELF'):
                    # ELF is checked even if a filename does not end in .so.
                    arm64_elf(header, name)
                    elf_count += 1
                    continue
                try:
                    if source is None and source_apk is not None:
                        source = zipfile.ZipFile(source_apk)
                    data.append(packaged_data(output, source, name))
                except (ValueError, zipfile.BadZipFile, NotImplementedError, RuntimeError) as error:
                    evidence = {'member': name, 'output_header_hex': header.hex(),
                                'output_member_bytes': output.getinfo(name).file_size,
                                'policy': 'still rejected; classification needs evidence',
                                'reason': str(error)}
                    if source is not None and name in source.namelist():
                        with source.open(name) as stream:
                            evidence['input_header_hex'] = stream.read(20).hex()
                        evidence['input_member_bytes'] = source.getinfo(name).file_size
                    print('NATIVE_MEMBER_DIAGNOSTIC ' + json.dumps(evidence, sort_keys=True), flush=True)
                    failures.append({'member': name, 'reason': str(error)})
        finally:
            if source is not None:
                source.close()
    if failures:
        print('NATIVE_SCAN_SUMMARY ' + json.dumps({'unclassified': failures, 'accepted_packaged_data': data,
                                                 'direct_arm64_elf_count': elf_count}, sort_keys=True), flush=True)
        raise ValueError(str(len(failures)) + ' native-data member(s) rejected; complete inventory logged: '
                         + '; '.join(x['reason'] for x in failures))
    # A data-only lib/ tree is not evidence of a functioning native application.
    require(not data or elf_count > 0, 'packaged data present but no direct arm64 ELF confirmed')
    return {'classification': 'arm64-v8a' if elf_count else 'no-native-libraries',
            'native_file_count': len(natives), 'direct_arm64_elf_count': elf_count,
            'packaged_data': data,
            'scope': 'direct ELF plus visible ELF inside bounded ZIPs; other packaged data is preserved, not ABI-certified'}
