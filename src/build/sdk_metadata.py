#!/usr/bin/env python3
"""Strict minimum-SDK readers shared by input and finished-APK gates."""
import pathlib
import re
import sys


class InvalidSdkMetadata(ValueError):
    """A declaration is present, but malformed or ambiguous."""


def positive_decimal(value):
    if not re.fullmatch(r'[1-9][0-9]{0,8}', value):
        raise InvalidSdkMetadata('minimum SDK must be one positive decimal integer')
    return int(value)


def parse_badging_sdk(text):
    # Both labels are observed aapt2 output, not targetSdkVersion/compileSdkVersion.
    lines = [line.strip() for line in text.splitlines()
             if re.match(r'^\s*(?:minSdkVersion|sdkVersion)\b', line)]
    if not lines:
        return None
    if len(lines) != 1:
        raise InvalidSdkMetadata('ambiguous minimum SDK declarations')
    match = re.fullmatch(r"(?:minSdkVersion|sdkVersion):'([1-9][0-9]{0,8})'", lines[0])
    if match is None:
        raise InvalidSdkMetadata('malformed minimum SDK declaration')
    return positive_decimal(match[1])


def parse_xmltree_sdk(text):
    lines = [line.strip() for line in text.splitlines()
             if re.search(r'\bminSdkVersion\b', line)]
    if not lines:
        return None
    if len(lines) != 1:
        raise InvalidSdkMetadata('ambiguous XML minimum SDK declarations')
    match = re.fullmatch(
        r'A: android:minSdkVersion(?:\(0x[0-9a-fA-F]+\))?='
        r'\(type 0x10\)(0x[0-9a-fA-F]{1,8})', lines[0])
    if match is None:
        raise InvalidSdkMetadata('malformed XML minimum SDK declaration')
    return positive_decimal(str(int(match[1], 16)))


def parse_scalar_sdk(text):
    value = text.strip()
    return positive_decimal(value) if value else None


def parse_manifest_sdk(elements):
    if len(elements) != 1:
        raise InvalidSdkMetadata('ambiguous uses-sdk declarations')
    value = elements[0].get('{http://schemas.android.com/apk/res/android}minSdkVersion')
    if value is None:
        raise InvalidSdkMetadata('missing minimum SDK in XML manifest')
    return positive_decimal(value)


def main(args):
    readers = {'badging': parse_badging_sdk, 'xmltree': parse_xmltree_sdk,
               'scalar': parse_scalar_sdk}
    try:
        if len(args) != 2 or args[0] not in readers:
            raise ValueError('invalid SDK reader request')
        value = readers[args[0]](pathlib.Path(args[1]).read_text(encoding='utf-8'))
        if value is None:
            return 2  # Absent declaration: another successful reader may be tried.
        print(value)
        return 0
    except (ValueError, OSError):
        print('::error::invalid or ambiguous minimum SDK metadata', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
