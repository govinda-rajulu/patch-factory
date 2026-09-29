#!/usr/bin/env python3
"""Deterministic selection-name check: every include line must name a patch the provider
really offers, read the same way the build reads it.

Replaces the Nightly namecheck/headroom readers, which passed a GitHub URL to list-patches
and got no names for any provider (Nightly #99, 28 Sep 2026), while the Monday provider watch
read all 19 from exact local bundles. This reuses that reader: the exact channel-selected .mpp
(GitHub and GitLab, candidates and extras), list-patches filtered by package but including
universal patches, no credentials in the patcher's environment.
Read-only: it prints a report and never edits a selection, baseline or issue.
"""
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/etc"))
import provider_watch  # noqa: E402


def lines(path):
    if not path.exists():
        return None
    return [l.split("|", 1)[0] for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def rules(root, kind):
    p = root / "src/patches" / kind
    rows = [l.strip().lower() for l in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []
    return [r for r in rows if r and not r.startswith("#")]


def tag(name, banned, confirm):
    low = name.lower()
    if any(b in low for b in banned):
        return "BAN"
    if any(c in low for c in confirm):
        return "CFM"
    return "   "


def check(root, observe, out=print):
    """Returns (checked, missing_dirs, unverified). Unreadable is never counted as fine."""
    rows = provider_watch.inventory(__import__("json").loads((root / "src/targets.json").read_text()))
    banned, confirm = rules(root, "BANNED"), rules(root, "CONFIRM")
    checked = missing_dirs = unverified = 0
    headroom = []
    for row in rows:
        label = row["target"] + "/" + row["patch_dir"]
        inc = lines(root / "src/patches" / row["patch_dir"] / "include-patches")
        exc = lines(root / "src/patches" / row["patch_dir"] / "exclude-patches")
        if inc is None or exc is None:
            out("?? %s: selection files missing - UNVERIFIED" % label)
            unverified += 1
            continue
        try:
            names = set(observe(row)["names"])
        except Exception as error:  # fixed codes only; never raw provider output
            code = str(error) if isinstance(error, provider_watch.WatchError) else type(error).__name__
            out("?? %s: provider list unreadable - UNVERIFIED (%s)" % (label, code))
            unverified += 1
            continue
        checked += 1
        gone = [n for n in inc if n not in names]
        if gone:
            missing_dirs += 1
            for n in gone:
                out("-- %s MISSING: %s" % (label, n))
        else:
            out("ok %s (%d include names)" % (label, len(inc)))
        for n in exc:
            if n not in names:
                # An exclude for a name the provider no longer offers is harmless but stale.
                out("~~ %s exclude not offered by provider: %s" % (label, n))
        unused = sorted(names - set(inc))
        headroom.append((label, len(inc), len(names), unused))
    out("")
    out("### headroom")
    for label, used, total, unused in headroom:
        out("")
        out("=== %s  using %d of %d" % (label, used, total))
        for n in unused:
            out("  %s  %s" % (tag(n, banned, confirm), n))
    out("")
    out("checked=%d dirs_with_missing_names=%d not_checked=%d" % (checked, missing_dirs, unverified))
    return checked, missing_dirs, unverified


def main():
    with tempfile.TemporaryDirectory(prefix="pf-selection-names-") as work:
        # No "-x -u": those flags hide universal patches, which include lists name
        # (ES/MX "Remove Ads", Reddit "Disable mobile ads"); the first live run on
        # 29 Sep 2026 reported 15 applied names as missing because of them.
        observer = provider_watch.Observer(ROOT, Path(work), flags=())
        checked, missing, unverified = check(ROOT, observer)
    return 1 if missing or not checked else 0


if __name__ == "__main__":
    if len(sys.argv) != 1:
        print("usage: selection_names.py", file=sys.stderr)
        sys.exit(2)
    sys.exit(main())
