import sys, zipfile, pathlib, glob, importlib
sys.path.insert(0, 'src/build')
import sign_apk
def build(path, names, drop):
    with zipfile.ZipFile(path, 'w') as z:
        for n, m in names:
            if drop and (n.endswith('/') or n == 'stamp-cert-sha256'): continue
            i = zipfile.ZipInfo(n); i.compress_type = zipfile.ZIP_STORED if m == 0 else zipfile.ZIP_DEFLATED
            z.writestr(i, b'' if n.endswith('/') else n.encode())
        if drop: z.writestr('META-INF/CERT.SF', b'x')
ok = 0
for f in sorted(glob.glob(sys.argv[1] + '/entries-*.txt')):
    rows = [l.split('\t') for l in open(f).read().splitlines() if l]
    names = [(r[0], int(r[1])) for r in rows]
    u, s = pathlib.Path('/tmp/u.apk'), pathlib.Path('/tmp/s.apk')
    build(u, names, False); build(s, names, True)
    try:
        p = sign_apk.compare(u, s); res = 'PASS entries=%d dropped=%s' % (p['entries_compared'], p['dropped_by_signer'][:4]); ok += 1
    except ValueError as e:
        res = 'STOP ' + str(e)[:150]
    print(f.split('entries-')[1][:11], len(names), res)
print('REPLAY', ok, 'of', len(glob.glob(sys.argv[1] + '/entries-*.txt')))
