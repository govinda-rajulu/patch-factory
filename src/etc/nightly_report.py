#!/usr/bin/env python3
"""Collect legacy Nightly Watch output honestly; no signing, publication or approval decisions."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

SCHEMA = 1
LIMIT = 8 * 1024 * 1024

def redact(text, env):
    # Known runtime credentials plus common PAT forms and URL query/userinfo values.
    for key, value in env.items():
        if value and len(value) >= 8 and any(x in key.upper() for x in ('TOKEN', 'PASSWORD', 'SECRET')):
            text = text.replace(value, '[REDACTED]')
    text = re.sub(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})', '[REDACTED]', text)
    text = re.sub(r'(https?://)[^/\s@]+@', r'\1[REDACTED]@', text)
    text = re.sub(r'(https?://[^\s?]+)\?[^\s]+', r'\1?[REDACTED]', text)
    text = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', text)
    return text

def analyze(text, rc, setup_ok, targets, env):
    safe = redact(text, env)
    reasons = []
    matches = re.findall(r'^report mode=full fail=([01])\s*$', safe, re.M)
    markers_ok = len(matches) == 1
    if not setup_ok: reasons.append('patcher setup failed or did not complete')
    if not markers_ok: reasons.append('missing or duplicate final report result')
    if not safe.strip(): reasons.append('empty report')
    if re.search(r'(?im)^.*(?:UNVERIFIED|unreadable|skipping|returned nothing).*$', safe):
        reasons.append('legacy reader reported incomplete inputs')
    if not isinstance(targets, list) or not targets or any(not isinstance(t,dict) for t in targets):
        reasons.append('target coverage inventory unavailable')
        targets = []
    # Legacy readers do not cover all extras/default selections or use the full build resolver.
    # Make that limitation explicit even when the subprocess exits zero.
    gaps = ['namecheck omits extra bundles and empty/default include sets',
            'provider readers are not yet aligned with build channel/byte resolution',
            'release reader does not paginate; historical coverage can be incomplete']
    gitlab = sorted({t.get('id','unknown') for t in targets
                     if any(b.get('host') == 'gitlab' for b in t.get('candidates',[]) + t.get('extra_bundles',[]) if isinstance(b,dict))})
    if gitlab: gaps.append('GitLab provider coverage missing for: ' + ', '.join(gitlab))
    failed = rc not in (0, None) or (markers_ok and matches[0] == '1')
    if markers_ok and rc == 0 and matches[0] == '1': reasons.append('report exit/result mismatch')
    status = 'FAILED' if failed else 'UNKNOWN' if reasons else 'PARTIAL'
    run_id = env.get('GITHUB_RUN_ID','')
    attempt = env.get('GITHUB_RUN_ATTEMPT','')
    repo = env.get('GITHUB_REPOSITORY','')
    source = env.get('GITHUB_SHA','')
    identity_ok = (repo == 'govinda-rajulu/patch-factory' and re.fullmatch(r'[0-9]+',run_id or '')
                   and re.fullmatch(r'[0-9]+',attempt or '') and re.fullmatch(r'[0-9a-f]{40}',source or ''))
    if not identity_ok:
        reasons.append('missing or invalid run identity')
        if status != 'FAILED': status = 'UNKNOWN'
    data = {'schema':SCHEMA,'kind':'nightly-watch','status':status,'report_exit_code':rc,
            'setup_ok':setup_ok,'coverage':'partial','coverage_gaps':gaps,'reasons':reasons,
            'source_commit':source if identity_ok else None,
            'run_id':run_id if identity_ok else None,'attempt':attempt if identity_ok else None,
            'run_url':f'https://github.com/{repo}/actions/runs/{run_id}' if identity_ok else None,
            'report_sha256':hashlib.sha256(safe.encode()).hexdigest(),
            'report_bytes':len(safe.encode()),'report_file':'nightly-report.txt',
            'redaction':'known environment credentials, PAT patterns and URL query/userinfo redacted; not an exhaustive secret audit'}
    return safe, data

def summary(data):
    lines = ['## Nightly Watch: ' + data['status'],
             '', 'Report execution and coverage are separate. A green job is not full provider health.',
             '', 'Full redacted text and JSON: this run’s nightly-report artifact (30-day retention).',
             'The JSON schema is groundwork for the existing GitHub page, not a deployed page integration.', '']
    for reason in data['reasons'] + data['coverage_gaps']: lines.append('- ' + reason)
    if data['run_url']: lines += ['', '[Exact run](' + data['run_url'] + ')']
    return '\n'.join(lines) + '\n'

def collect(root, env):
    dest = root/'watch-evidence'
    dest.mkdir(exist_ok=False)
    setup_ok = env.get('WATCH_SETUP') == 'success'
    rc = None
    if setup_ok:
        # Known legacy readers run with no shell signing material and isolated report output.
        try:
            proc = subprocess.run(['bash','src/etc/report.sh','full'], cwd=root, env=env,
                                  capture_output=True, timeout=900)
            rc = proc.returncode
            raw = proc.stdout + proc.stderr
            if len(raw)>LIMIT:
                raw = b'Report exceeded 8 MiB capture limit; content not published.\n'
                rc = 2
        except subprocess.TimeoutExpired:
            raw = b'Report exceeded 15-minute limit; completeness unknown.\n';rc = 2
    else:
        raw = b'Report not executed because patcher setup did not succeed.\n'
    try: targets = json.loads((root/'src/targets.json').read_text())
    except (OSError, ValueError): targets = None
    safe, data = analyze(raw.decode('utf-8',errors='replace'),rc,setup_ok,targets,env)
    (dest/'nightly-report.txt').write_text(safe,encoding='utf-8')
    (dest/'nightly-report.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    # Preserve the existing issue publisher's input path, redacted before persistence.
    (root/'.nightly-report.txt').write_text(safe,encoding='utf-8')
    if env.get('GITHUB_STEP_SUMMARY'):
        with open(env['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as out: out.write(summary(data))
    print('NIGHTLY_STATUS='+data['status'])
    return data

def enforce(root):
    data = json.loads((root/'watch-evidence/nightly-report.json').read_text())
    raw = (root/'watch-evidence/nightly-report.txt').read_bytes()
    if (data.get('schema') != SCHEMA or data.get('report_sha256') != hashlib.sha256(raw).hexdigest()
            or data.get('report_bytes') != len(raw)):
        raise ValueError('missing or changed Nightly Watch evidence')
    if data.get('status') in ('FAILED', 'UNKNOWN'):
        print('::error::Nightly Watch '+str(data.get('status'))+'; read the full artifact and job summary')
        return 1
    if data.get('status') != 'PARTIAL' or data.get('coverage') != 'partial':
        raise ValueError('unsupported Nightly Watch state')
    print('::warning::Nightly checks completed with PARTIAL coverage; this is not full provider health')
    return 0

if __name__ == '__main__':
    try:
        if sys.argv[1:] == ['collect']: collect(Path.cwd(),dict(os.environ));sys.exit(0)
        if sys.argv[1:] == ['enforce']: sys.exit(enforce(Path.cwd()))
        raise ValueError('usage: nightly_report.py collect|enforce')
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print('::error::Nightly report collection failed: '+type(exc).__name__)
        sys.exit(2)
