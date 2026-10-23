#!/usr/bin/env python3
"""Fill packet.tmpl.py into a controller (kept in the repository since W15i, 23 Oct 2026).

Usage: build_ctl.py REPO_DIR BRANCH BASE BASE_TREE PREREQ CFG OUT
  CFG is a file holding the template's CONFIG block (from '# ---- CONFIG' up to the BUNDLE line),
  with BASE, BASE_TREE, PREREQ and TREE written as 40 zeros; this script fills them.
  OUT is written; name the result pf-<packet>-<first 8 of its sha256>.py before handing over.
"""
import base64, re, subprocess, sys, tempfile

repo, branch, base, base_tree, prereq, cfg_path, out = sys.argv[1:8]
tree = subprocess.check_output(['git', '-C', repo, 'rev-parse', branch + '^{tree}'], text=True).strip()
with tempfile.NamedTemporaryFile(suffix='.bundle') as b:
    subprocess.check_call(['git', '-C', repo, 'bundle', 'create', b.name, prereq + '..' + branch], stderr=subprocess.DEVNULL)
    bundle = base64.b64encode(open(b.name, 'rb').read()).decode()
cfg = open(cfg_path).read()
for k, v in (('BASE', base), ('BASE_TREE', base_tree), ('PREREQ', prereq), ('TREE', tree)):
    if k == 'BASE':
        cfg, n = re.subn(r"(?m)^BASE = os.environ.get\('PF_BASE', '[0-9a-f]{40}'\)", "BASE = os.environ.get('PF_BASE', '%s')" % v, cfg)
    else:
        cfg, n = re.subn(r"(?m)^%s = '[0-9a-f]{40}'" % k, "%s = '%s'" % (k, v), cfg)
    assert n == 1, k
src = open(repo + '/docs/review/controllers/packet.tmpl.py').read()
s = src.index('# ---- CONFIG'); e = src.index("BUNDLE = '@@BUNDLE@@'", s)
text = src[:s] + cfg + "BUNDLE = '" + bundle + "'" + src[e + len("BUNDLE = '@@BUNDLE@@'"):]
assert "TREE = '%s'" % tree in text and '@@' not in text and "BASE_TREE = '%s'" % base_tree in text
open(out, 'w').write(text)
print('tree', tree)
