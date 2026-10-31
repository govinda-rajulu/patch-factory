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
W16j (25 Oct 2026, owner: heval99 Truecaller primary, the combo as its backup): when the
target has exactly one primary candidate and it carries "overrides", attempt 1 builds that
candidate with its overrides too (pinned, no prepared inputs), so a primary can drop the
target's extra bundles while the fallback keeps them.

Writes release/.fallback after a successful later attempt, and fallback=, winner= and
attempts= to GITHUB_OUTPUT. Exit status is the last attempt's.
Usage: build_attempts.py TARGET_ID
"""
import json
import atexit
import os
import shutil
import tempfile
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'etc'))
import preflight  # noqa: E402

WINNER = re.compile(r'\[\+\] winner=([A-Za-z0-9_-]+) ')
REASON = re.compile(r'\[-\] .{1,240}')
# Only fatal output markers belong in an attempt reason; a recoverable utils warning is [ - ] too.
RECOVERABLE = "[-] Can't found lastest user-agent"
# W16r (#262): the attempt's reason is the line that ENDED it. The Amazon Music T1 failure was
# reported as its first red line (an APKMirror transfer the store chain recovered from); the
# patcher then failed on the APKPure APK. Morphe's abort line wins, else the last red line.
PATCH_ABORT = re.compile(r'Patching aborted: (.{1,200})')
STORE_USED = re.compile(r'STORE_CHAIN used ([A-Za-z0-9_-]+)')
# W16v (27 Oct 2026): a refused older fallback APK ends the attempt; name it, not the transfer line.
DOWNGRADE = re.compile(r'STORE_DOWNGRADE_REFUSED (.{1,200})')
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


def primary_view(t):
    """The one primary candidate's name when it carries overrides, else None (W16j)."""
    primary = [c for c in t['candidates'] if not c.get('fallback')]
    if len(primary) == 1 and primary[0].get('overrides') and not t.get('pin'):
        return primary[0]['name']
    return None


def view_text(original, ident, name):
    """src/targets.json text with target ident pinned to candidate name and its overrides.
    W15g: the Sign and Publish jobs recompute this to check the patch job's carried copy."""
    rows = json.loads(original)
    for t in rows:
        if t.get('id') == ident:
            c = next(x for x in t['candidates'] if x['name'] == name)
            t.update(preflight.effective(t, c))
    return json.dumps(rows, indent=2, ensure_ascii=False) + '\n'


def view(root, ident, name, original):
    """Write src/targets.json with target ident pinned to candidate name and its overrides."""
    (root / 'src/targets.json').write_text(view_text(original, ident, name), encoding='utf-8')


def ensure_store_services(root, env):
    """Start store helpers only when this attempt may download an APK.

    store_services.sh performs the health check and reuses healthy containers;
    a failed check is the only path that starts a fresh container.  Keeping this
    at the attempt boundary means a prepared source APK costs no service startup,
    while a primary/fallback pair shares the same healthy services.
    """
    helper = root / "src/build/store_services.sh"
    # W16g (L087): only the Manual Patch build step sets PF_STORE_LAZY=1. Tests and other callers
    # never start containers; Validate went red when a test started real helpers on the runner.
    if env.get("PF_STORE_LAZY") != "1":
        return
    if not helper.exists():
        # Keep isolated controller fixtures and older checkouts usable; Actions
        # checkouts always contain the helper.
        return
    result = subprocess.run(["bash", str(helper)], cwd=root, env=env, check=False)
    if result.returncode != 0:
        raise RuntimeError("store download services could not be started or reused")


def cleanup_store_services(root, env):
    """W16o F-08: remove helper containers once the provider controller exits."""
    helper = root / "src/build/store_services.sh"
    if env.get("PF_STORE_LAZY") == "1" and helper.exists():
        subprocess.run(["bash", str(helper), "cleanup"], cwd=root, env=env, check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def attempt(root, ident, env, log):
    winner, reason, abort, store, downgrade = None, None, None, None, None
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
            if m and RECOVERABLE not in m[0]:
                reason = m[0].strip()
            m = PATCH_ABORT.search(line)
            if m:
                abort = m[1].strip()
            if 'VERSION_STEP_DOWN ' in line or 'VARIANT_RETRY ' in line:
                store = None
            m = STORE_USED.search(line)
            if m:
                store = m[1]
            m = DOWNGRADE.search(line)
            if m:
                downgrade = m[1].strip()
    if downgrade and not abort:
        reason = 'store: refused a fallback APK of another version (%s)' % downgrade
    if abort:
        reason = 'patcher: ' + abort.rstrip(';')
    if reason and store:
        reason = '%s; APK from %s after the first store failed' % (reason, store)
    return p.returncode, winner, reason


def output(env, **fields):
    path = env.get('GITHUB_OUTPUT')
    if path:
        with open(path, 'a', encoding='utf-8') as f:
            for k, v in fields.items():
                f.write('%s=%s\n' % (k, v))


def main(argv, env=None, root=None):
    env = dict(os.environ if env is None else env)
    # W15g: a signing secret in the patch job means the workflow split regressed; stop, never sign here.
    leaked = sorted(k for k in env if k.startswith('KEYSTORE'))
    if leaked:
        print('::error::signing secret reached the patch job (%s); the release key belongs to the Sign job only' % ', '.join(leaked))
        return 1
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
    # W16o: F-03, mkdtemp gives each controller a private 0700 log directory.
    logdir = Path(tempfile.mkdtemp(prefix='pf-attempts-', dir=env.get('RUNNER_TEMP') or '/tmp'))
    atexit.register(shutil.rmtree, logdir, ignore_errors=True)
    if env.get('PF_STORE_LAZY') == '1':
        atexit.register(cleanup_store_services, root, env)
    tried, failures, rc, n = [], [], 1, 0
    first = primary_view(t)
    for name in steps:
        if name is None and first:
            name = first
        if name is not None and name in tried:
            continue
        if n >= limit:
            break
        n += 1
        if n > 1:
            print('::group::reset after failed attempt %d' % (n - 1))
            reset(root, keep, keep_dirs)
            print('::endgroup::')
        # W15g: patching is unsigned and keyless (main() refused any KEYSTORE* variable above).
        e = dict(env)
        e['PF_UNSIGNED'] = 'true'
        if e.get('PF_STORE_LAZY') == '1':
            e['PF_KEEP_STORE_SERVICES'] = '1'
        if name is not None:
            view(root, ident, name, original)
            e.update(PF_RESOLVED_READY='false', PF_SOURCE_READY='false')
        print('ATTEMPT %d %s: %s' % (n, ident, name or 'primary candidates as configured'), flush=True)
        # A checked/prepared APK does not use the stores.  Unprepared primary
        # attempts and every later provider attempt do; the helper's health
        # check makes the latter reuse the primary attempt's services.
        if e.get('PF_SOURCE_READY', 'false') != 'true' or n > 1:
            ensure_store_services(root, e)
        rc, winner, reason = attempt(root, ident, e, logdir / ('attempt-%d.log' % n))
        if rc == 0:
            # W16y-a review: a run pinned to a fallback provider (manual provider=<fallback>) is a
            # fallback build too, so the coverage floor and the blind-publish refusal apply to it.
            chosen = winner or name
            is_fb = n > 1 or any(c.get('name') == chosen and c.get('fallback') for c in t.get('candidates') or [])
            if is_fb:
                text = 'Built with fallback provider %s after %s' % (winner or name, '; '.join(failures) or 'a run pinned to that fallback')
                (root / 'release').mkdir(exist_ok=True)
                (root / 'release/.fallback').write_text(text[:900] + '\n', encoding='utf-8')
                (root / 'release/.fallback-provider').write_text((winner or name) + '\n', encoding='utf-8')
                print('::warning::PROVIDER_FALLBACK %s: %s' % (ident, text[:900]))
            output(env, fallback='true' if is_fb else 'false', winner=winner or name or '', attempts=n)
            summary = 'fallback test build; publication requires the coverage floor' if is_fb else 'primary build'
            print('ATTEMPTS_OK %s: attempt %d of %d, winner %s (%s)' %
                  (ident, n, len(steps), winner or name, summary), flush=True)
            return 0
        tried.append(winner or name or '?')
        failures.append('%s failed (%s)' % (winner or name or 'the primary', (reason or 'exit %d' % rc)[:200]))
        print('ATTEMPT_FAILED %d %s: %s' % (n, ident, failures[-1]), flush=True)
    output(env, fallback='false', winner='', attempts=n)
    print('::error::ATTEMPTS_FAILED %s: %s' % (ident, '; '.join(failures)[:1500]))
    return rc or 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
