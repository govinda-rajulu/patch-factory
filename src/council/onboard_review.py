#!/usr/bin/env python3
"""Agent review for onboarding pull requests (new app, provider or patch name).

Packet W1, 8 Oct 2026. The owner's rule: nothing new reaches src/targets.json or an
include list without an agent review. This script is that review. It runs from the
reviewed BASE checkout with the model keys; the pull request's own files arrive only
as the manifest that src/etc/onboard_check.py wrote (untrusted data, never code).

Each council seat that takes the 'review' job gets the manifest inside a JSON data
envelope plus a per-run canary, and must answer
  {"canary", "verdict": approve|changes|block, "summary", "findings": [...]}.
A finding counts only when its quote appears verbatim in the manifest. A changes or
block verdict with no counted finding is unsupported and does not count.

The check passes when at least ONBOARD_QUORUM seats gave a counted verdict, fewer than
half of them say block, and the deterministic onboarding check had no problems. It
posts or edits one pull request comment and exits 1 otherwise. It never pushes,
merges, labels or dispatches. Transport and seat plumbing come from council.py.
"""
import concurrent.futures
import json
import os
import re
import secrets
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import council  # noqa: E402  (same directory, standard library only)

ONBOARD_QUORUM = 2
PACK_LIMIT = 60000
MARKER = '<!-- pf-onboard-review -->'
VERDICTS = ('approve', 'changes', 'block')
SEVERITIES = ('high', 'medium', 'low')
GH_ALLOWED = (
    ('GET', re.compile(r'^repos/[\w.-]+/[\w.-]+/issues/\d+/comments\?per_page=100&page=[1-3]$')),
    ('POST', re.compile(r'^repos/[\w.-]+/[\w.-]+/issues/\d+/comments$')),
    ('PATCH', re.compile(r'^repos/[\w.-]+/[\w.-]+/issues/comments/\d+$')),
)


def gh(env, method, path, body=None):
    if not any(m == method and rx.match(path) for m, rx in GH_ALLOWED):
        raise council.Refused('GitHub call outside the onboarding allowlist: %s %s' % (method, path))
    status, text = council.http(method, 'https://api.github.com/' + path,
                                {'Authorization': 'Bearer ' + env['GITHUB_TOKEN'],
                                 'Accept': 'application/vnd.github+json',
                                 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'pf-onboard'},
                                body, timeout=60)
    if status not in (200, 201):
        raise council.Refused('GitHub %s %s returned %s' % (method, path.split('?')[0], status))
    return json.loads(text) if text else None


def instructions():
    return council.prompt('ONBOARD.md')


def check_answer(obj, canary, haystack):
    """Validated answer with only the findings whose quote is in the manifest."""
    if not isinstance(obj, dict) or set(obj) != {'canary', 'verdict', 'summary', 'findings'}:
        raise ValueError('keys')
    if obj['canary'] != canary:
        raise ValueError('canary')
    # W13: small-model slips ("Block", "High", extra keys, an over-long issue) no longer throw the
    # whole seat away; a finding that still does not fit is dropped and counted as malformed.
    if isinstance(obj.get('verdict'), str):
        obj = dict(obj, verdict=obj['verdict'].strip().lower())
    if isinstance(obj.get('summary'), str) and len(obj['summary']) > 500:
        obj = dict(obj, summary=obj['summary'][:497] + '...')
    if obj['verdict'] not in VERDICTS or not council.short(obj['summary'], 500):
        raise ValueError('verdict or summary')
    f = obj['findings']
    if not isinstance(f, list):
        raise ValueError('findings')
    kept, dropped, malformed = [], 0, 0
    for x in f[:8]:
        if not isinstance(x, dict) or not {'severity', 'item', 'quote', 'issue'} <= set(x):
            malformed += 1
            continue
        x = {k: x[k] for k in ('severity', 'item', 'quote', 'issue')}
        if isinstance(x['severity'], str):
            x['severity'] = x['severity'].strip().lower()
        for k, n in (('item', 200), ('issue', 400)):
            if isinstance(x[k], str) and len(x[k]) > n:
                x[k] = x[k][:n - 3] + '...'
        if x['severity'] not in SEVERITIES or not council.short(x['item'], 200) \
                or not council.short(x['issue'], 400) or not council.short(x['quote'], 300):
            malformed += 1
            continue
        if x['quote'] in haystack:
            kept.append(x)
        else:
            dropped += 1
    obj = dict(obj, findings=kept, dropped=dropped + malformed, malformed=malformed)
    obj['counted'] = obj['verdict'] == 'approve' or bool(kept)
    return obj


def ask_seat(seat, system, user, env, canary, haystack):
    row = {'seat': seat['id'], 'provider': seat['provider'], 'model': '', 'status': '', 'answer': None}
    if not env.get(council.PROVIDERS[seat['provider']]['key']):
        row['status'] = 'SKIPPED_NO_KEY'
        return row
    if len(system) + len(user) > seat['max_input_chars']:
        row['status'] = 'ABSTAIN_OVER_BUDGET'
        return row
    models = [m for m in council.candidates(seat, env)
              if (seat['provider'], m) not in council.remembered('missing')][:4]
    for index, model in enumerate(models):
        row['model'] = model
        try:
            text = council.complete(seat, model, system, user, env, retry=index == len(models) - 1)
        except council.ModelMissing:
            council.remembered('missing').add((seat['provider'], model))
            continue
        except (council.Truncated, council.Busy):
            continue
        except council.Refused as e:
            row['status'] = 'REFUSED ' + council.scrub(str(e), env)[:120]
            return row
        last = 'no JSON object'
        try:
            found = council.json_candidates(text) if text else []
        except ValueError:
            found = []
        for obj in found:
            try:
                row['answer'] = check_answer(obj, canary, haystack)
                row['status'] = 'OK'
                return row
            except ValueError as e:
                last = str(e)
        row['status'] = 'INVALID ' + last
        return row
    row['model'] = ''
    row['status'] = 'UNAVAILABLE no listed model answered'
    return row


def decide(rows, deterministic_ok):
    counted = [r for r in rows if r['answer'] and r['answer']['counted']]
    blocks = [r for r in counted if r['answer']['verdict'] == 'block']
    ok = deterministic_ok and len(counted) >= ONBOARD_QUORUM and 2 * len(blocks) < len(counted)
    if not deterministic_ok:
        why = 'the deterministic onboarding check failed'
    elif len(counted) < ONBOARD_QUORUM:
        why = 'only %d counted verdict(s); quorum is %d' % (len(counted), ONBOARD_QUORUM)
    elif not ok:
        why = '%d of %d counted verdicts say block' % (len(blocks), len(counted))
    else:
        why = '%d counted verdict(s), %d block' % (len(counted), len(blocks))
    return ok, why


def render(rows, ok, why, m):
    lines = [MARKER, '## Onboarding review: %s' % ('PASS' if ok else 'FAIL'), '',
             'Agent review required by AGENTS.md for every new app, provider or patch name. ' + why[0].upper() + why[1:] + '.',
             'Advisory seats; the owner still decides and merges. Deterministic problems: %d.' % len(m.get('problems') or []),
             '', '| seat | model | status | verdict | counted findings |', '| --- | --- | --- | --- | --- |']
    for r in rows:
        a = r['answer'] or {}
        lines.append('| %s | %s | %s | %s | %s |' % (r['seat'], r['model'] or '-', r['status'][:60],
                                                   a.get('verdict', '-'), len(a.get('findings') or [])))
    for r in rows:
        a = r['answer']
        if not a:
            continue
        lines += ['', '**%s** (%s): %s' % (r['seat'], a['verdict'], a['summary'])]
        for f in a['findings']:
            lines.append('- %s `%s`: %s (quote: "%s")' % (f['severity'], f['item'], f['issue'], f['quote'][:160]))
        if a.get('dropped'):
            lines.append('- %d finding(s) dropped: quote not found in the manifest' % a['dropped'])
    for p in m.get('problems') or []:
        lines.append('- deterministic: ' + p)
    return '\n'.join(lines) + '\n'


def post(env, repo, pr, body):
    found = None
    for page in (1, 2, 3):
        rows = gh(env, 'GET', 'repos/%s/issues/%s/comments?per_page=100&page=%d' % (repo, pr, page)) or []
        for c in rows:
            if MARKER in (c.get('body') or '') and (c.get('user') or {}).get('type') == 'Bot':
                found = c['id']
        if len(rows) < 100:
            break
    if found:
        gh(env, 'PATCH', 'repos/%s/issues/comments/%d' % (repo, found), {'body': body})
    else:
        gh(env, 'POST', 'repos/%s/issues/%s/comments' % (repo, pr), {'body': body})


def main(env=os.environ):
    path = Path(env.get('PF_MANIFEST', 'onboard-manifest/manifest.json'))
    if not path.is_file():
        print('::error::onboarding manifest missing: ' + str(path))
        return 1
    raw = path.read_text(encoding='utf-8')
    m = json.loads(raw)
    if not m.get('onboarding') and not m.get('problems'):
        print('ONBOARD_REVIEW SKIP: no onboarding change in this pull request')
        return 0
    cfg = json.loads((ROOT / 'src' / 'council' / 'seats.json').read_text(encoding='utf-8'))
    seats = [s for s in cfg['seats'] if 'review' in s.get('jobs', council.JOBS)]
    canary = 'pf-' + secrets.token_hex(6)
    data, cut = council.envelope('onboarding manifest', raw, PACK_LIMIT)
    system = instructions()
    user = 'Canary for this run: %s\n%s%s' % (canary, data, '\n(manifest cut at %d characters)' % PACK_LIMIT if cut else '')
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(lambda s: ask_seat(s, system, user, env, canary, raw[:PACK_LIMIT]), seats))
    ok, why = decide(rows, not m.get('problems'))
    body = render(rows, ok, why, m)
    print(body)
    summary = env.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as fh:
            fh.write(body)
    if env.get('PF_PR') and env.get('PF_REPO'):
        post(env, env['PF_REPO'], env['PF_PR'], body)
    print('ONBOARD_REVIEW %s: %s' % ('PASS' if ok else 'FAIL', why))
    return 0 if ok else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (council.Refused, ValueError, KeyError, OSError) as e:
        print('::error::onboard review: ' + council.scrub(str(e), os.environ))
        sys.exit(1)
