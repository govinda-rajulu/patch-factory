#!/usr/bin/env python3
"""Validate an exact reviewed original variant, never infer one from a filename."""
import json
import re
import sys
from pathlib import Path


def need(ok, message):
    if not ok:
        raise ValueError('source variant: ' + message)


def validate(variant, source, mapping, version, ceiling):
    need(isinstance(variant, dict) and
         set(variant) == {'kind', 'abis', 'min_sdk', 'apkmirror_url'}, 'unknown fields')
    need(variant['kind'] in ('apk', 'bundle'), 'unknown container type')
    abis = variant['abis']
    need(isinstance(abis, list) and all(a in ('arm64-v8a', 'armeabi-v7a', 'x86', 'x86_64')
         for a in abis) and abis == sorted(set(abis)) and (not abis or 'arm64-v8a' in abis),
         'invalid native ABI inventory')
    need(type(variant['min_sdk']) is int and 0 < variant['min_sdk'] <= ceiling,
         'minimum SDK outside ceiling')
    if source == 'apkmirror':
        need(re.fullmatch(r'[0-9]+(?:[.][0-9]+)*', version), 'invalid exact version')
        prefix = ('https://www.apkmirror.com/apk/' + mapping['org'] + '/' + mapping['name'] +
                  '/' + mapping['name'] + '-' + version.replace('.', '-') + '-release/')
        url = variant['apkmirror_url']
        need(isinstance(url, str) and url.startswith(prefix) and
             re.fullmatch(r'[a-z0-9-]+-android-apk-download/', url[len(prefix):]),
             'variant URL outside exact app/release')
    else:
        need(source == 'apkpure' and variant['apkmirror_url'] is None,
             'unexpected store or variant URL')
    return variant


def from_file(path, source, package, version):
    # Input is generated in the isolated fallback directory after admission.
    def unique(pairs):
        d = {}
        for k, v in pairs:
            need(k not in d, 'duplicate field')
            d[k] = v
        return d
    file = Path(path)
    need(file.is_file() and not file.is_symlink() and file.stat().st_size < 16384, 'unsafe selector')
    doc = json.loads(file.read_text(), object_pairs_hook=unique)
    need(set(doc) == {'source', 'package', 'version', 'mapping', 'ceiling', 'variant'} and
         (doc['source'], doc['package'], doc['version']) == (source, package, version),
         'selector target differs')
    return validate(doc['variant'], source, doc['mapping'], version, doc['ceiling'])


def main():
    try:
        need(len(sys.argv) == 6, 'usage: selector FIELD FILE SOURCE PACKAGE VERSION')
        field, path, source, package, version = sys.argv[1:]
        need(field in ('kind', 'apkmirror_url'), 'unsupported selector field')
        value = from_file(path, source, package, version)[field]
        need(isinstance(value, str), 'selector value absent')
        print(value)
        return 0
    except (ValueError, TypeError, KeyError, OSError):
        print('SOURCE_VARIANT_REFUSED', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
