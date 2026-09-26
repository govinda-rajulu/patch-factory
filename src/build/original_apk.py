#!/usr/bin/env python3
"""Strict original split metadata. Separate from the finished-APK reader.

An empty versionName is allowed only on a named split. Package, versionCode,
nonempty versionName, SDK and the unique base are checked against the admission.
No expected value is substituted for missing observed metadata. A configuration
split (config.X or FEATURE.config.X) may omit the SDK because Android applies the
base/feature manifest; it is returned as None, never guessed.
"""
import re

import artifact_identity as identity
from sdk_metadata import parse_badging_sdk


CONFIG_SPLIT = r'(?:[A-Za-z0-9_]+[.])?config[.][A-Za-z0-9_]+'


def is_config_split(split):
    return isinstance(split, str) and re.fullmatch(CONFIG_SPLIT, split) is not None


def parse(text):
    identity.require(len(text.encode('utf-8')) <= 1024 * 1024, 'original metadata too large')
    lines = [line for line in text.splitlines() if line.startswith('package:')]
    identity.require(len(lines) == 1, 'ambiguous original package declaration')
    pairs = re.findall(r"([A-Za-z][A-Za-z0-9]*)='([^']*)'", lines[0])
    identity.require(len(pairs) == len({key for key, _ in pairs}), 'duplicate original package field')
    fields = dict(pairs)
    package, code, version = (fields.get(k) for k in ('name', 'versionCode', 'versionName'))
    split = fields.get('split')
    identity.require(isinstance(package, str) and
                     re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*(?:[.][A-Za-z0-9_]+)+', package),
                     'invalid original package')
    identity.require(isinstance(code, str) and re.fullmatch(r'[0-9]+', code),
                     'missing original versionCode')
    identity.require(split is None or
                     (isinstance(split, str) and re.fullmatch(r'[A-Za-z0-9_]+(?:[.][A-Za-z0-9_]+)*', split)),
                     'invalid original split name')
    identity.require(isinstance(version, str) and
                     (re.fullmatch(r'[0-9]+(?:[.][0-9]+)*', version) or (split is not None and version == '')),
                     'invalid original versionName')
    sdk = parse_badging_sdk(text)
    identity.require((type(sdk) is int and sdk > 0) or (sdk is None and is_config_split(split)),
                     'original minimum SDK missing')
    return {'package': package, 'version_code': code, 'version_name': version,
            'min_sdk': sdk, 'split': split}


def metadata(root, apk, env):
    tools = identity.sdk_tools('aapt2', env)
    identity.require(tools, 'aapt2 required for original split metadata')
    # Invalid/ambiguous metadata never falls through to another reader.
    text = identity.command([tools[0], 'dump', 'badging', str(apk)], root, env).decode()
    return parse(text)
