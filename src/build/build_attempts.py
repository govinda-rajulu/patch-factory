#!/usr/bin/env python3
"""Provider fallback around build.sh (packet W13, owner design 10 Oct 2026).

Attempt 1 is the build exactly as before: the primary candidates compete in resolve.sh
(fallback candidates never do). When it fails, the next untried candidate is built: other
primaries first, then "fallback": true ones, in src/targets.json order, at most
PF_MAX_FALLBACKS (default 2) more attempts. A later attempt
  * pins that candidate and lays its "overrides" (its own version, version code, dpi,
    extra bundles...) over the target, in this runner's checkout only;
  * never consumes the daily Plan's prepared inputs (they were resolved for attempt 1);
  * starts clean: files the failed attempt created are deleted, tracked files restored.
PF_PROVIDER (Manual Patch input "provider") builds exactly that candidate, with its
overrides, and nothing else. A target "pin" or "fallback": false keeps one attempt.

Writes release/.fallback after a successful later attempt, and fallback=, winner= and
attempts= to GITHUB_OUTPUT. Exit status is the last attempt's.
Usage: build_attempts.py TARGET_ID
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'etc'))
import preflight  # noqa: E402

WINNER = re.compile(r'\[\+\] winner=([A-Za-z0-9_-]+) ')
REASON = re.compile(r'\[-\] .{1,240}')
ANSI = re.compile(r'\x1b\[[0-9;]*m')


def git(root, *args):
    return subprocess.run(['git', *args], cwd=root, capture_output=True, check=True).stdout


def untracked(root):
    return {p for p in git(root, 'ls-files', '-o', '-z').decode('utf-8', 'surrogateescape').split('\0') if p}


def tree_dirs(root):
    return {d for d, _, _ in os.walk(root) if '.git' not in Path(os.path.relpath(d, root)).parts}


def reset(root, keep, keep_dirs):
    """Delete what the failed attempt created; restore tracked files it changed."""
    for rel in sorted(untracked(root) - keep, reverse=True):
        p = root / rel
        if p.is_symlink() or p.is_file():
            p.unlink()
    for d in sorted(tree_dirs(root) - keep_dirs, key=len, reverse=True):
        if os.path.isdir(d) and not os.listdir(d):
            os.rmdir(d)
    git(root, 'checkout', '--', '.')


def plan(t, provider):
    names = [c['name'] for c in t['candidates']]
    if provider:
        if provider not in names:
            raise ValueError('provider %s is not a candidate of %s (have: %s)' % (provider, t['id'], ', '.join(names)))
        return [provider]
    if t.get('pin') or t.get('fallback') is False:
        return [None]
    return [None] + [c['name'] for c in t['candidates'] if not c.get('fallback')] + \
        [c['name'] for c in t['candidates'] if c.get('fallback')]


def view(root, ident, name, original):
    """Write src/targets.json with target ident pinned to candidate name and its overrides."""
    rows = json.loads(original)
    for t in rows:
        if t.get('id') == ident:
            c = next(x for x in t['candidates'] if x['name'] == name)
            t.update(preflight.effective(t, c))
    (root / 'src/targets.json').write_text(json.dumps(rows, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def attempt(root, ident, env, log):
    winner, reason = None, None
    # restore_signals=False: build.sh keeps SIGPIPE ignored, as in a plain Actions step. Python's
    # default resets it, and `unzip -l | grep -q` under pipefail then dies with 141 (W13 smoke, L052).
    with subprocess.Popen(['bash', 'src/build/build.sh', ident], cwd=root, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, restore_signals=False) as p, open(log, 'wb') as out:
        for raw in p.stdout:
            sys.stdout.buffer.write(raw)
            sys.stdout.flush()
            out.write(raw)
            line = ANSI.sub('', raw.decode('utf-8', 'replace'))
            m = WINNER.search(line)
            if m:
                winner = m[1]
            m = REASON.search(line)
            if m and reason is None:
                reason = m[0].strip()
    return p.returncode, winner, reason


def output(env, **fields):
    path = env.get('GITHUB_OUTPUT')
    if path:
        with open(path, 'a', encoding='utf-8') as f:
            for k, v in fields.items():
                f.write('%s=%s\n' % (k, v))


def main(argv, env=None, root=None):
    env = dict(os.environ if env is None else env)
    root = Path(root or '.').resolve()
    if len(argv) != 1:
        print('usage: build_attempts.py TARGET_ID', file=sys.stderr)
        return 2
    ident = argv[0]
    original = (root / 'src/targets.json').read_text(encoding='utf-8')
    rows = [t for t in json.loads(original) if t.get('id') == ident and t.get('enabled')]
    if len(rows) != 1:
        print('::error::%s is not one enabled target' % ident)
        return 1
    t = rows[0]
    try:
        steps = plan(t, (env.get('PF_PROVIDER') or '').strip())
    except ValueError as e:
        print('::error::' + str(e))
        return 1
    limit = 1 + int(env.get('PF_MAX_FALLBACKS', '2'))
    keep, keep_dirs = untracked(root), tree_dirs(root)
    logdir = Path(env.get('RUNNER_TEMP') or '/tmp') / ('pf-attempts-' + ident)
    logdir.mkdir(parents=True, exist_ok=True)
    tried, failures, rc, n = [], [], 1, 0
    for name in steps:
        if name is not None and name in tried:
            continue
        if n >= limit:
            break
        n += 1
        if n > 1:
            print('::group::reset after failed attempt %d' % (n - 1))
            reset(root, keep, keep_dirs)
            print('::endgroup::')
        e = dict(env)
        if name is not None:
            view(root, ident, name, original)
            e.update(PF_RESOLVED_READY='false', PF_SOURCE_READY='false')
        print('ATTEMPT %d %s: %s' % (n, ident, name or 'primary candidates as configured'), flush=True)
        rc, winner, reason = attempt(root, ident, e, logdir / ('attempt-%d.log' % n))
        if rc == 0:
            if n > 1:
                text = 'Built with fallback provider %s after %s' % (winner or name, '; '.join(failures))
                (root / 'release').mkdir(exist_ok=True)
                (root / 'release/.fallback').write_text(text[:900] + '\n', encoding='utf-8')
                print('::warning::PROVIDER_FALLBACK %s: %s' % (ident, text[:900]))
            output(env, fallback='true' if n > 1 else 'false', winner=winner or name or '', attempts=n)
            print('ATTEMPTS_OK %s: attempt %d of %d, winner %s' % (ident, n, len(steps), winner or name), flush=True)
            return 0
        tried.append(winner or name or '?')
        failures.append('%s failed (%s)' % (winner or name or 'the primary', (reason or 'exit %d' % rc)[:200]))
        print('ATTEMPT_FAILED %d %s: %s' % (n, ident, failures[-1]), flush=True)
    output(env, fallback='false', winner='', attempts=n)
    print('::error::ATTEMPTS_FAILED %s: %s' % (ident, '; '.join(failures)[:1500]))
    return rc or 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
