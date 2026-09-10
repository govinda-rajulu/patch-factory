#!/usr/bin/env python3
"""Numeric build suffix compatible with existing -b[0-9]+ release filters.

New: UTC date(8) + GitHub run id(20, zero-padded) + run attempt(6).
Old date-only suffixes remain readable, but are not emitted by new builds.
This identifies workflow attempts, not APK versionCode or publisher authenticity.
"""
import datetime
import os
import re
import sys


def require(ok, message):
    if not ok:
        raise ValueError(message)


def positive(value, width, label):
    require(isinstance(value, str) and re.fullmatch(r'[1-9][0-9]*', value)
            and len(value) <= width, 'missing/invalid ' + label)
    return int(value)


def create(env, now=None):
    run = positive(env.get('GITHUB_RUN_ID'), 20, 'GITHUB_RUN_ID')
    attempt = positive(env.get('GITHUB_RUN_ATTEMPT'), 6, 'GITHUB_RUN_ATTEMPT')
    now = now or datetime.datetime.now(datetime.timezone.utc)
    require(now.tzinfo is not None, 'build time must include timezone')
    date = now.astimezone(datetime.timezone.utc).strftime('%Y%m%d')
    return '-b' + date + str(run).zfill(20) + str(attempt).zfill(6)


def parse(suffix):
    require(isinstance(suffix, str) and re.fullmatch(r'-b(?:[0-9]{8}|[0-9]{34})', suffix),
            'invalid build suffix format')
    digits = suffix[2:]
    datetime.datetime.strptime(digits[:8], '%Y%m%d')
    result = {'date': digits[:8], 'legacy': len(digits) == 8, 'run_id': None, 'attempt': None}
    if not result['legacy']:
        result['run_id'] = int(digits[8:28]);result['attempt'] = int(digits[28:34])
        require(result['run_id'] > 0 and result['attempt'] > 0, 'zero workflow identity in build suffix')
    return result


def verify_run(suffix, env):
    result = parse(suffix)
    require(not result['legacy'], 'publishing requires a unique workflow-attempt build suffix')
    require(result['run_id'] == positive(env.get('GITHUB_RUN_ID'), 20, 'GITHUB_RUN_ID')
            and result['attempt'] == positive(env.get('GITHUB_RUN_ATTEMPT'), 6, 'GITHUB_RUN_ATTEMPT'),
            'build suffix belongs to another workflow run/attempt')
    return result


if __name__ == '__main__':
    try:
        print(create(os.environ))
    except ValueError as error:
        raise SystemExit('BUILD_IDENTITY_FAILED: ' + str(error))
