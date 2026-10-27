#!/usr/bin/env python3
"""Join a read-only owner probe and a built packet controller into ONE owner file (W16q, 27 Oct 2026).

Owner ask (27 Oct): "1 file that does some work and collects some work for you so i can reduce
some back and forth". The combo first runs the probe (collect: logs, run evidence, a bundle of
main), then the controller (do: the packet), streaming both, and ends with one RESULT line.

Usage: build_combo.py PROBE.py CONTROLLER.py PACKET OUT
  CONTROLLER.py must already carry its final name pf-<packet>-<sha8>.py (build_ctl.py), so it
  removes itself on RESULT OK. Name OUT pf-<packet>-combo-<first 8 of its sha256>.py.
Both inner scripts are embedded with their sha256 and unpacked into ~/work/run-logs, never into
the home folder, so the launcher's "exactly one ~/pf-<packet>-*.py" check sees only the combo.
The probe copy is removed after it runs; the controller is kept on anything but its RESULT OK
(it removes itself then), so running the same combo again resumes the packet as designed.
"""
import base64, hashlib, pathlib, sys

TEMPLATE = r'''#!/usr/bin/env python3
"""@@NAME@@: one owner run, built by build_combo.py (patch-factory W16q). Engineered by ClickUp
Brain on Anthropic's Claude for Govindarajulu K (owner and architect).
Step 1 runs the read-only probe @@PROBE_NAME@@ (collects evidence into one zip, writes nothing to
GitHub). Step 2 runs the packet controller @@CTL_NAME@@. Both print as they go; the last line is
one RESULT line for both."""
import base64, fcntl, hashlib, os, pathlib, subprocess, sys, time
PACKET = '@@PACKET@@'
PROBE_NAME, PROBE_SHA = '@@PROBE_NAME@@', '@@PROBE_SHA@@'
CTL_NAME, CTL_SHA = '@@CTL_NAME@@', '@@CTL_SHA@@'
PROBE_B64 = '@@PROBE_B64@@'
CTL_B64 = '@@CTL_B64@@'
HOME = pathlib.Path(os.environ.get('PF_HOME', str(pathlib.Path.home())))
RUN = HOME / 'work' / 'run-logs'
STAMP = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())


def unpack(b64, sha, path):
    data = base64.b64decode(b64)
    if hashlib.sha256(data).hexdigest() != sha:
        raise SystemExit('RESULT STOP: the embedded %s does not match its sha256; nothing ran. Combo kept.' % path.name)
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == sha:
        return path
    tmp = path.with_name(path.name + '.part')
    tmp.write_bytes(data)
    os.chmod(str(tmp), 0o600)
    os.replace(str(tmp), str(path))
    return path


def run(path):
    """Run one inner script, stream its output, return (exit code, its last RESULT line)."""
    last = ''
    p = subprocess.Popen([sys.executable, str(path)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, text=True, errors='replace')
    for line in p.stdout:
        print(line, end='', flush=True)
        if line.startswith('RESULT'):
            last = line.strip()
    return p.wait(), last or 'RESULT missing (exit %s)' % p.returncode


def main():
    """One combo at a time (W16q round 3): a second launcher while the first still runs (a Cloud
    Shell reconnect) stops at once instead of racing it; any setup error still ends in one RESULT."""
    try:
        RUN.mkdir(parents=True, exist_ok=True)
        lock = open(str(RUN / ('pf-%s-combo.lock' % PACKET)), 'a')
    except OSError as e:
        print('RESULT STOP: cannot use %s (%s); nothing ran. Combo kept.' % (RUN, e), flush=True)
        return 1
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print('RESULT STOP: another %s combo is still running; watch ~/work/run-logs/pf-%s-nohup.log instead. Nothing ran. Combo kept.' % (PACKET, PACKET), flush=True)
        return 1
    try:
        return steps()
    except Exception as e:  # never a bare traceback for the owner
        print('RESULT STOP: combo error %s: %s. Files kept; running the same launcher again resumes.' % (type(e).__name__, str(e)[:200]), flush=True)
        return 1


def steps():
    print('COMBO %s: step 1 of 2, read-only probe %s' % (PACKET, PROBE_NAME), flush=True)
    probe = unpack(PROBE_B64, PROBE_SHA, RUN / ('combo-probe-%s-%s' % (STAMP, PROBE_NAME)))
    try:
        code1, res1 = run(probe)
    finally:
        if probe.exists():
            probe.unlink()
    print('COMBO %s: step 2 of 2, packet controller %s' % (PACKET, CTL_NAME), flush=True)
    ctl = unpack(CTL_B64, CTL_SHA, RUN / CTL_NAME)
    code2, res2 = run(ctl)
    print('COMBO probe: ' + res1, flush=True)
    print('COMBO packet: ' + res2, flush=True)
    me = pathlib.Path(__file__).resolve()
    if code1 == 0 and code2 == 0:
        mine = me.parent == HOME and me.name.startswith('pf-%s-combo-' % PACKET) and \
            hashlib.sha256(me.read_bytes()).hexdigest().startswith(me.stem.split('-')[-1])
        if mine:
            me.unlink()
        print('RESULT OK. Upload the two zips or folders the lines above name. %s' % ('Combo removed.' if mine else 'Combo kept.'))
        return 0
    print('RESULT STOP: read the two COMBO lines above; upload what they name. Combo kept; running the same launcher again resumes.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
'''


def build(probe_path, ctl_path, packet):
    probe, ctl = pathlib.Path(probe_path).read_bytes(), pathlib.Path(ctl_path).read_bytes()
    name = pathlib.Path(ctl_path).name
    if not (name.startswith('pf-%s-' % packet) and hashlib.sha256(ctl).hexdigest().startswith(name[:-3].split('-')[-1])):
        raise SystemExit('controller must be named pf-%s-<first 8 of its sha256>.py' % packet)
    out = TEMPLATE
    for k, v in (('@@PROBE_B64@@', base64.b64encode(probe).decode()), ('@@CTL_B64@@', base64.b64encode(ctl).decode()),
                 ('@@PROBE_SHA@@', hashlib.sha256(probe).hexdigest()), ('@@CTL_SHA@@', hashlib.sha256(ctl).hexdigest()),
                 ('@@PROBE_NAME@@', pathlib.Path(probe_path).name), ('@@CTL_NAME@@', name),
                 ('@@PACKET@@', packet), ('@@NAME@@', 'pf-%s-combo' % packet)):
        out = out.replace(k, v)
    return out


if __name__ == '__main__':
    probe_path, ctl_path, packet, out = sys.argv[1:5]
    pathlib.Path(out).write_text(build(probe_path, ctl_path, packet), encoding='utf-8')
    print('wrote %s (%d bytes)' % (out, pathlib.Path(out).stat().st_size))
