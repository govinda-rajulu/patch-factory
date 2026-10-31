#!/usr/bin/env python3
# W15g STOP probe (read-only): waits for the packet/w15g smokes, reads each Sign job result,
# lists the hand-off APK entries the signer may drop (directories, source stamp). Deletes only its own downloads.
import json, os, pathlib, shutil, subprocess, sys, time, zipfile, datetime
REPO = 'govinda-rajulu/patch-factory'
stamp = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
out = pathlib.Path.home() / 'work/run-logs' / ('pf-sp-' + stamp)
out.mkdir(parents=True)
def gh(*a, timeout=300):
    return subprocess.run(['gh'] + list(a), capture_output=True, text=True, timeout=timeout)
def say(s):
    print(s, flush=True)
    with open(out / 'PROBE.txt', 'a') as f: f.write(s + '\n')
deadline = time.time() + 60 * 60
while True:
    r = gh('run', 'list', '--repo', REPO, '--workflow', 'manual-patch.yml', '--branch', 'packet/w15g', '--limit', '40',
           '--json', 'databaseId,status,conclusion,displayTitle,createdAt,event')
    if r.returncode:
        say('STOP gh run list failed: ' + r.stderr.strip()[:200]); sys.exit(1)
    runs = json.loads(r.stdout)
    waiting = [x for x in runs if x['status'] != 'completed']
    if not waiting or time.time() > deadline: break
    say('WAIT %d of %d smokes still running' % (len(waiting), len(runs))); time.sleep(120)
(out / 'runs.json').write_text(json.dumps(runs, indent=1))
say('OK %d smoke runs on packet/w15g, %d still running' % (len(runs), len(waiting)))
rows = []
for x in runs:
    rid = str(x['databaseId'])
    if x['status'] != 'completed':
        rows.append(dict(run=rid, title=x['displayTitle'], status=x['status'])); continue
    lg = gh('run', 'view', rid, '--repo', REPO, '--log', timeout=600)
    text = lg.stdout if lg.returncode == 0 else ''
    keep = [l for l in text.splitlines() if ('##[error]' in l or 'SIGNING_SPLIT_OK ' in l or 'SIGNED ' in l or 'HANDOFF_OK' in l
             or 'UNSIGNED IDENTITY VERIFIED' in l or 'ATTEMPTS_OK' in l or 'UNSIGNED_UNSUPPORTED' in l or 'patcher supports' in l)
            and 'echo' not in l and 'print(' not in l]
    (out / ('keep-' + rid + '.txt')).write_text('\n'.join(keep) + '\n')
    errs = [l for l in keep if '##[error]' in l]
    row = dict(run=rid, title=x['displayTitle'], conclusion=x['conclusion'], ok=[l.split('Z ', 1)[-1][:200] for l in keep if 'SIGNING_SPLIT_OK ' in l],
               errors=[l[:300] for l in errs][:6], log_bytes=len(text))
    if any('non-signature entry' in l or 'changed entry bytes' in l or 'reordered' in l for l in errs):
        al = gh('api', 'repos/%s/actions/runs/%s/artifacts' % (REPO, rid))
        names = [a['name'] for a in json.loads(al.stdout or '{}').get('artifacts', []) if a['name'].startswith('patch-output-')]
        if names:
            tmp = out / ('dl-' + rid)
            d = gh('run', 'download', rid, '--repo', REPO, '-n', names[0], '-D', str(tmp), timeout=900)
            apks = sorted(tmp.glob('release/*.apk'))
            if d.returncode == 0 and apks:
                with zipfile.ZipFile(apks[0]) as z:
                    infos = z.infolist()
                    names_all = [i.filename for i in infos]
                    row['apk'] = apks[0].name; row['entries'] = len(infos)
                    row['dirs'] = [n for n in names_all if n.endswith('/')][:40]; row['dir_count'] = sum(n.endswith('/') for n in names_all)
                    row['stamp'] = [n for n in names_all if 'stamp' in n.lower()]
                    row['meta_top'] = [n for n in names_all if n.startswith('META-INF/') and n.count('/') == 1][:40]
                    row['dupes'] = sorted({n for n in names_all if names_all.count(n) > 1})[:20]
                    row['odd'] = [n for n in names_all if n.startswith('/') or '..' in n or '\\' in n][:20]
                    (out / ('entries-' + rid + '.txt')).write_text('\n'.join('%s\t%d\t%d\t%d' % (i.filename, i.compress_type, i.file_size, i.flag_bits) for i in infos) + '\n')
            else:
                row['download'] = 'failed: ' + (d.stderr or '')[:200]
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            row['download'] = 'no patch-output artifact'
    rows.append(row)
    say('%s %s %s ok=%d err=%s' % (rid, x['displayTitle'][:60], x['conclusion'], len(row.get('ok', [])), (row.get('errors') or [''])[-1].split('##[error]')[-1][:120]))
(out / 'rows.json').write_text(json.dumps(rows, indent=1))
shutil.make_archive(str(out), 'zip', out.parent, out.name)
z = pathlib.Path(str(out) + '.zip')
say('RESULT OK. Upload %s (%d bytes).' % (z, z.stat().st_size))
