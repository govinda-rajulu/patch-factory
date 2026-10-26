#!/usr/bin/env python3
"""pf-keys (23 Oct 2026, before W15g). Owner runs it once on Cloud Shell.

1. Kilo and Z.AI keys: you paste each one (hidden). It is tested live (model list + one tiny
   chat). Only a key that answers is saved as a repository secret (KILO_API_KEY, ZAI_API_KEY).
   Keys are never printed, logged or written to disk.
2. Council probe on main: every seat and model answers or says why (existing six providers).
3. CodeQL: setup state and open alerts (names, files, lines only).
4. morphe-desktop 1.19.0 side files: runs list-versions the way the shadow resolver does and
   lists every file it creates (the Check new patch shadow jobs refuse an unlisted file).
5. Zip of the logs folder for upload. RESULT OK removes this script and appends a ledger line.
"""
import datetime, getpass, re, hashlib, json, os, pathlib, shutil, subprocess, sys, time, urllib.error, urllib.request

REPO = 'govinda-rajulu/patch-factory'
GH = os.environ.get('PF_GH', 'gh')
HOME = pathlib.Path.home()
WORK = HOME / 'work'
STAMP = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
LOGS = WORK / 'run-logs' / ('pf-keys-' + STAMP)
SELF = pathlib.Path(__file__).resolve()
KILO = os.environ.get('PF_KILO_BASE', 'https://ai-gateway.kilo.ai/api/v1')
ZAI = os.environ.get('PF_ZAI_BASE', 'https://api.z.ai/api/paas/v4')
JAR_URL = os.environ.get('PF_JAR_URL', 'https://github.com/MorpheApp/morphe-desktop/releases/download/v1.19.0/morphe-desktop-1.19.0-all.jar')
JAR_SHA = os.environ.get('PF_JAR_SHA', 'deb5d931f3899b20a119637473d338c52585f0c561b5d8b2856b916fe90163b5')
MPP_URL = os.environ.get('PF_MPP_URL', 'https://github.com/SysAdminDoc/HushFacebook/releases/download/v0.17.0/patches-0.17.0.mpp')
MPP_SHA = os.environ.get('PF_MPP_SHA', '2e7255df0eacfaa69c37c3c45ffc0396fe1a1023f6a96b098c75ffc463063525')
PROBE_WAIT = int(os.environ.get('PF_PROBE_WAIT', '2400'))
POLL = int(os.environ.get('PF_POLL', '20'))
R = {'script': 'pf-keys.py', 'stamp': STAMP, 'steps': []}
SECRETS = []


def say(step, status, detail):
    # Status details are supplied as fixed text and counts only. Key-bearing data is
    # written through write(), whose artifact redaction is separate from this path.
    R['steps'].append({'step': step, 'status': status, 'detail': detail})
    print('%s %s: %s' % (status, step, detail), flush=True)
    (LOGS / 'RESULT.json').write_text(json.dumps(R, indent=1) + '\n', encoding='utf-8')


def write(name, text):
    for s in SECRETS:
        text = text.replace(s, '[key]')
    (LOGS / name).write_text(text, encoding='utf-8')


def gh(*args, inp=None, timeout=120):
    return subprocess.run([GH] + list(args), input=inp, capture_output=True, text=True, timeout=timeout)


def http(method, url, key, body=None, timeout=90):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Authorization', 'Bearer ' + key)
    req.add_header('Content-Type', 'application/json')
    req.add_header('User-Agent', 'patch-factory-keytest/1')
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            code, hdrs, raw = r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        code, hdrs, raw = e.code, dict(e.headers or {}), e.read()
    except Exception as e:  # network, TLS, timeout
        return 0, {}, str(e)[:200], round(time.time() - t0, 1)
    rl = {k: v for k, v in hdrs.items() if 'ratelimit' in k.lower() or 'retry-after' in k.lower()}
    try:
        doc = json.loads(raw.decode('utf-8', 'replace'))
    except ValueError:
        doc = raw.decode('utf-8', 'replace')[:300]
    return code, rl, doc, round(time.time() - t0, 1)


def chat(base, key, model, extra=None):
    body = {'model': model, 'max_tokens': 512,
            'messages': [{'role': 'user', 'content': 'Reply with the single word OK.'}]}
    body.update(extra or {})
    code, rl, doc, secs = http('POST', base + '/chat/completions', key, body)
    out = {'model': model, 'http': code, 'seconds': secs, 'ratelimit_headers': rl}
    if code == 200 and isinstance(doc, dict) and doc.get('choices'):
        msg = doc['choices'][0].get('message') or {}
        out['reply'] = (msg.get('content') or '')[:60]
        out['reasoning_chars'] = len(msg.get('reasoning_content') or msg.get('reasoning') or '')
        out['finish'] = doc['choices'][0].get('finish_reason')
        out['usage'] = doc.get('usage')
        out['served_model'] = doc.get('model')
        out['ok'] = bool(out['reply'].strip())
    else:
        out['error'] = json.dumps(doc)[:300] if not isinstance(doc, str) else doc[:300]
        out['ok'] = False
    return out


def models(base, key):
    code, rl, doc, secs = http('GET', base + '/models', key)
    if code != 200 or not isinstance(doc, dict):
        return {'http': code, 'ids': None, 'error': (json.dumps(doc) if not isinstance(doc, str) else doc)[:200]}
    ids = sorted(m.get('id', '') for m in doc.get('data', []) if isinstance(m, dict))
    return {'http': code, 'count': len(ids), 'ids': ids, 'ratelimit_headers': rl}


def test_key(name, secret, base, picks, extra_tries):
    key = getpass.getpass('Paste your %s key and press Enter (hidden; just Enter to skip): ' % name).strip()
    if not key:
        say(name, 'SKIP', 'no key pasted; nothing tested or saved')
        return
    SECRETS.append(key)
    report = {'provider': name, 'base': base}
    m = models(base, key)
    report['models'] = {k: v for k, v in m.items() if k != 'ids'}
    ids = m.get('ids') or []
    free = [i for i in ids if 'free' in i.lower()]
    report['free_ids'] = free[:40]
    report['all_ids_sample'] = ids[:60]
    tries = [p for p in picks if not ids or p in ids] or ([free[0]] if free else picks[:1])
    report['chats'] = [chat(base, key, t) for t in tries[:3]]
    for label, model, extra in extra_tries:
        r = chat(base, key, model, extra)
        r['variant'] = label
        report['chats'].append(r)
    good = [c for c in report['chats'] if c.get('ok')]
    write('key-%s.json' % name.lower().replace('.', ''), json.dumps(report, indent=1) + '\n')
    if not good:
        say(name, 'FAIL', 'no model answered; secret NOT saved')
        return
    p = gh('secret', 'set', secret, '-R', REPO, inp=key)
    if p.returncode != 0:
        say(name, 'FAIL', 'key worked but saving the repository secret failed')
        return
    say(name, 'OK', '%d model(s) answered; %d models listed, %d with free access'
        % (len(good), m.get('count') or 0, len(free)))


def probe():
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=10)
    p = gh('workflow', 'run', 'council.yml', '-R', REPO, '--ref', 'main', '-f', 'mode=probe')
    if p.returncode != 0:
        say('probe', 'FAIL', 'dispatch refused')
        return
    run = None
    deadline = time.time() + PROBE_WAIT
    while time.time() < deadline:
        time.sleep(POLL)
        q = gh('run', 'list', '-R', REPO, '--workflow', 'council.yml', '--event', 'workflow_dispatch', '--limit', '10',
               '--json', 'databaseId,createdAt,status,conclusion,url')
        try:
            rows = json.loads(q.stdout or '[]')
        except ValueError:
            rows = []
        mine = [r for r in rows if datetime.datetime.fromisoformat(r['createdAt'].replace('Z', '+00:00')) >= since]
        if not mine:
            continue
        run = sorted(mine, key=lambda r: r['createdAt'])[0]
        if run['status'] == 'completed':
            break
        print('  probe run %s: %s' % (run['databaseId'], run['status']), flush=True)
    if not run or run['status'] != 'completed':
        say('probe', 'FAIL', 'probe run did not finish after %d seconds' % PROBE_WAIT)
        return
    log = gh('run', 'view', str(run['databaseId']), '-R', REPO, '--log', timeout=300).stdout or ''
    write('probe.log', log)
    lines = [l.split('PROBE_MODEL ', 1)[1] for l in log.splitlines() if 'PROBE_MODEL ' in l]
    served = sum(' status=SERVED' in l for l in lines)
    write('probe-summary.txt', '\n'.join(lines) + '\n')
    say('probe', 'OK' if run['conclusion'] == 'success' else 'FINDING',
        '%d of %d models served' % (served, len(lines)))


def codeql():
    s = gh('api', 'repos/%s/code-scanning/default-setup' % REPO)
    setup = json.loads(s.stdout) if s.returncode == 0 and s.stdout.strip().startswith('{') else {'error': (s.stderr or '')[:200]}
    a = gh('api', '--paginate', 'repos/%s/code-scanning/alerts?state=open&per_page=100' % REPO, timeout=180)
    try:
        alerts = json.loads(a.stdout) if a.returncode == 0 else []
    except ValueError:
        alerts = []
    rows = [{'rule': x.get('rule', {}).get('id'), 'severity': x.get('rule', {}).get('security_severity_level') or x.get('rule', {}).get('severity'),
             'tool': x.get('tool', {}).get('name'), 'path': x.get('most_recent_instance', {}).get('location', {}).get('path'),
             'line': x.get('most_recent_instance', {}).get('location', {}).get('start_line'),
             'message': (x.get('most_recent_instance', {}).get('message', {}).get('text') or '')[:200]} for x in alerts if isinstance(x, dict)]
    an = gh('api', 'repos/%s/code-scanning/analyses?per_page=10' % REPO)
    try:
        analyses = [{'created_at': x.get('created_at'), 'category': x.get('category'), 'results': x.get('results_count'), 'error': x.get('error')}
                    for x in json.loads(an.stdout)] if an.returncode == 0 else []
    except ValueError:
        analyses = []
    write('codeql.json', json.dumps({'setup': setup, 'alerts': rows, 'analyses': analyses}, indent=1) + '\n')
    sec = gh('secret', 'list', '-R', REPO, '--json', 'name,updatedAt')
    write('secret-names.json', sec.stdout if sec.returncode == 0 else '[]\n')
    by = {}
    for r in rows:
        by[r['severity']] = by.get(r['severity'], 0) + 1
    say('codeql', 'OK' if setup.get('state') == 'configured' else 'FINDING',
        '%d analyses seen; %d open alerts' % (len(analyses), len(rows)))


def fetch(url, dest, want):
    p = subprocess.run(['curl', '--fail', '--silent', '--show-error', '--location', '--proto', '=https', '--max-time', '300',
                        '--output', str(dest), url], capture_output=True, text=True)
    if p.returncode != 0:
        return 'download failed: ' + p.stderr[:120]
    got = hashlib.sha256(dest.read_bytes()).hexdigest()
    return None if got == want else 'sha256 %s, expected %s' % (got[:16], want[:16])


def tree(base):
    return {str(p.relative_to(base)) + ('/' if p.is_dir() else '') for p in base.rglob('*')}


def java_bin():
    # CI uses Java 21; Cloud Shell may default to an older one. Prefer any installed 21+.
    found = []
    for cand in ['java'] + sorted(str(p) for p in pathlib.Path('/usr/lib/jvm').glob('*/bin/java')):
        if not shutil.which(cand) and not os.path.exists(cand):
            continue
        j = subprocess.run([cand, '-version'], capture_output=True, text=True)
        line = ((j.stderr or j.stdout).splitlines() or [''])[0]
        m = re.search(r'version "(\d+)', line)
        if m:
            found.append((int(m.group(1)), cand, line))
    best = [f for f in found if f[0] >= 21]
    return (best[0] if best else (max(found) if found else None))


def morphe():
    jb = java_bin()
    if not jb:
        say('morphe', 'SKIP', 'no java on this shell; side-file check not run')
        return
    major, java, jv = jb
    t = WORK / ('pf-diag-' + STAMP)
    try:
        for d in ('payload', 'candidates', 'root'):
            (t / d).mkdir(parents=True, exist_ok=True)
        jar, mpp = t / 'payload' / 'morphe-desktop-1.19.0-all.jar', t / 'candidates' / 'patches-0.17.0.mpp'
        for url, dest, want in ((JAR_URL, jar, JAR_SHA), (MPP_URL, mpp, MPP_SHA)):
            err = fetch(url, dest, want)
            if err:
                say('morphe', 'FAIL', 'download or checksum validation failed')
                return
        home_before = {p.name for p in HOME.iterdir()}
        cfg_before = {p.name for p in (HOME / '.config').iterdir()} if (HOME / '.config').is_dir() else set()
        runs = []
        for n in (1, 2):
            before = tree(t)
            p = subprocess.run([java, '-jar', str(jar), 'list-versions', '--patches=' + str(mpp), '-x', '-u', '-f', 'com.facebook.katana'],
                               cwd=t / 'root', capture_output=True, text=True, timeout=600)
            new = sorted(tree(t) - before)
            runs.append({'run': n, 'exit': p.returncode, 'new_files': new, 'output_head': (p.stdout + p.stderr).splitlines()[:40]})
        home_new = sorted({p.name for p in HOME.iterdir()} - home_before)
        cfg_new = sorted(({p.name for p in (HOME / '.config').iterdir()} if (HOME / '.config').is_dir() else set()) - cfg_before)
        write('morphe.json', json.dumps({'java': jv, 'runs': runs, 'new_in_home': home_new, 'new_in_config': cfg_new}, indent=1) + '\n')
        side = [f for f in runs[0]['new_files']]
        say('morphe', 'OK' if runs[0]['exit'] == 0 else 'FINDING',
            'list-versions exit %d; %d new files; %d new home/config entries' % (runs[0]['exit'], len(side), len(home_new + cfg_new)))
    finally:
        shutil.rmtree(t, ignore_errors=True)


def main():
    LOGS.mkdir(parents=True, exist_ok=True)
    a = gh('auth', 'status')
    if a.returncode != 0:
        say('gate', 'STOP', 'gh is not signed in on this shell')
        return 1
    say('gate', 'OK', 'gh signed in; logs in ' + str(LOGS))
    test_key('Kilo', 'KILO_API_KEY', KILO, ['kilo-auto/free'], [])
    test_key('Z.AI', 'ZAI_API_KEY', ZAI, ['glm-4.7-flash', 'glm-4.5-flash'],
             [('thinking off', 'glm-4.7-flash', {'thinking': {'type': 'disabled'}})])
    print('Keys done. The rest runs by itself (about 10 to 30 minutes). Keep this tab open.', flush=True)
    for step in (codeql, morphe, probe):
        try:
            step()
        except Exception as e:  # one broken step must not hide the others
            say(step.__name__, 'FAIL', 'step raised an error')
    bad = [s for s in R['steps'] if s['status'] in ('FAIL', 'STOP')]
    R['result'] = 'OK' if not bad else 'STOP'
    (LOGS / 'RESULT.json').write_text(json.dumps(R, indent=1) + '\n', encoding='utf-8')
    z = shutil.make_archive(str(LOGS), 'zip', LOGS.parent, LOGS.name)
    if not bad:
        digest = hashlib.sha256(SELF.read_bytes()).hexdigest()
        if SELF.name.startswith('pf-keys-') and digest.startswith(SELF.stem.split('-')[-1]):
            SELF.unlink()
        with open(WORK / 'run-ledger.txt', 'a', encoding='utf-8') as f:
            f.write('%s pf-keys.py %s OK\n' % (STAMP, digest[:12]))
        print('RESULT OK. Upload this zip to chat: cloudshell download %s' % z)
        return 0
    print('RESULT STOP (%d step(s) failed, listed above). Script kept. Upload this zip anyway: cloudshell download %s' % (len(bad), z))
    return 1


if __name__ == '__main__':
    sys.exit(main())
