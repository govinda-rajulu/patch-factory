#!/usr/bin/env python3
"""Offline-first safety scan for a patched APK and its provider bundle.

The scanner deliberately does not attempt to understand an APK's binary XML itself.  On the
runner aapt2 is the authoritative manifest decoder; if it is unavailable, permission evidence is
UNKNOWN and the scan cannot be a PASS.  Optional ClamAV and VirusTotal checks are recorded without
making an unconfigured scanner look clean.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

ALLOWLIST = Path(__file__).with_name("provider_scan_allowlist.json")

# These are intentionally exact hosts, not suffix matches.  A provider's GitHub repository and
# the GitHub/CDN endpoints commonly used to serve its release assets are the only defaults.
DEFAULT_ALLOWED_HOSTS = {
    "github.com", "raw.githubusercontent.com", "githubusercontent.com",
    "objects.githubusercontent.com", "githubassets.com", "gitlab.com", "cdn.jsdelivr.net",
}
SENSITIVE_PERMISSION_RE = re.compile(
    r"(?:SMS|CALL_LOG|CONTACTS|BIND_ACCESSIBILITY_SERVICE|REQUEST_INSTALL_PACKAGES|"
    r"QUERY_ALL_PACKAGES|SYSTEM_ALERT_WINDOW|READ_PHONE_STATE|LOCATION|"
    r"CAMERA|RECORD_AUDIO|MICROPHONE|BIND_DEVICE_ADMIN)", re.I
)
PERMISSION_RE = re.compile(r"(?:android\.)?permission\.([A-Za-z0-9_]+)")
URL_RE = re.compile(r"https?://(?:[^\s\"'<>\\]|\\.)+", re.I)
DOMAIN_RE = re.compile(r"(?<![A-Za-z0-9_.-])(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}(?![A-Za-z0-9_.-])", re.I)
PRINTABLE_RE = re.compile(rb"[ -~]{4,}")
# W16y-c (wrong call 118): a bare dotted word counts as a host only when its last label is a
# real, common public top-level domain. Source-file names kept in dex debug info
# (BooleanSetting.java), Java/Kotlin package names (app.morphe.extension.shared.logger) and
# obfuscated identifiers (rek.ql) are not hosts. Anything after http:// or https:// always counts.
CODE_ROOTS = frozenset("r com org net io app android androidx java javax kotlin kotlinx dalvik google".split())
BARE_HOST_TLDS = frozenset("""
com net org info biz io co me dev app xyz top site online club pro cloud link live tech store
ai gg tv cc ws to ly sh fm am in us uk de fr ru cn jp kr br es it nl pl tr ua ir id vn th my sg
hk tw ph pk bd au ca mx ar za ng eg sa ae il se no fi dk ch at be cz ro hu gr pt ie nz su
""".split())
FLAG_PATTERNS = {
    "DexClassLoader": re.compile(r"DexClassLoader"),
    "PathClassLoader": re.compile(r"PathClassLoader"),
    "InMemoryDexClassLoader": re.compile(r"InMemoryDexClassLoader"),
    "Runtime.exec": re.compile(r"Runtime(?:\.|/|;->|->)exec"),
    "su": re.compile(r"(?<![A-Za-z0-9_])su(?![A-Za-z0-9_])"),
    "busybox": re.compile(r"(?<![A-Za-z0-9_])busybox(?![A-Za-z0-9_])", re.I),
}


def _read_allowlist() -> dict[str, set[str]]:
    try:
        raw = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
        return {str(k): {str(h).lower().rstrip(".") for h in v} for k, v in raw.items() if isinstance(v, list)}
    except (OSError, ValueError):
        return {}


def _run_aapt2(apk: Path) -> tuple[set[str] | None, str]:
    tool = os.environ.get("PF_AAPT2") or shutil.which("aapt2")
    if not tool:
        for root in (os.environ.get("ANDROID_HOME"), os.environ.get("ANDROID_SDK_ROOT")):
            if root:
                candidates = sorted(Path(root).glob("build-tools/*/aapt2"), reverse=True)
                if candidates:
                    tool = str(candidates[0])
                    break
    if not tool:
        return None, "aapt2 unavailable"
    outputs: list[str] = []
    for subcommand in (("dump", "permissions"), ("dump", "badging")):
        try:
            p = subprocess.run([tool, *subcommand, str(apk)], text=True, capture_output=True,
                               timeout=60, check=False)
        except (OSError, subprocess.SubprocessError) as exc:
            outputs.append(str(exc))
            continue
        outputs.append((p.stdout or "") + "\n" + (p.stderr or ""))
        perms = {m.group(1) for m in PERMISSION_RE.finditer(outputs[-1])}
        # dump permissions exits successfully for a manifest with no uses-permission entries.
        if p.returncode == 0 and (perms or subcommand == ("dump", "permissions")):
            return perms, "aapt2 " + " ".join(subcommand)
    # An APK with no declared permissions is valid, but a command which returned no decodable
    # manifest is not evidence of an empty permission set.
    return None, "aapt2 could not decode permissions"


def _zip_printable(path: Path) -> tuple[set[str], set[str], list[str]]:
    """Return printable strings, discovered hosts, and errors for relevant APK entries."""
    strings: set[str] = set()
    hosts: set[str] = set()
    errors: list[str] = []
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            relevant = [n for n in names if re.fullmatch(r"classes(?:[0-9]+)?\.dex", n)
                        or n == "resources.arsc" or n.startswith("res/")]
            for name in relevant:
                try:
                    data = zf.read(name)
                except (OSError, KeyError, RuntimeError) as exc:
                    errors.append(f"{name}: {exc}")
                    continue
                for match in PRINTABLE_RE.finditer(data):
                    text = match.group().decode("utf-8", "ignore")
                    strings.add(text)
                    for u in URL_RE.findall(text):
                        host = _host_from_url(u)
                        if host:
                            hosts.add(host)
                    for x in DOMAIN_RE.findall(text):
                        x = x.lower().rstrip(".")
                        labels = x.split(".")
                        # Second review: reversed-domain package names (com.example.app,
                        # androidx.core.app) and resource references (R.id) are code, not hosts.
                        if labels[-1] in BARE_HOST_TLDS and labels[0] not in CODE_ROOTS:
                            hosts.add(x)
            return strings, hosts, errors
    except (OSError, zipfile.BadZipFile) as exc:
        return set(), set(), [str(exc)]


def _host_from_url(value: str) -> str | None:
    value = value.rstrip(".,;:)]}>\"'")
    match = re.match(r"https?://([^/?:#]+)", value, re.I)
    return match.group(1).lower().rstrip(".") if match else None


def _clamav(paths: list[Path]) -> tuple[str, list[str]]:
    tool = shutil.which("clamscan")
    if not tool:
        return "UNKNOWN", ["ClamAV (clamscan) is not installed"]
    reasons: list[str] = []
    status = "clean"
    for path in paths:
        try:
            p = subprocess.run([tool, "--no-summary", "--stdout", str(path)], text=True,
                               capture_output=True, timeout=180, check=False)
        except (OSError, subprocess.SubprocessError) as exc:
            return "UNKNOWN", [f"ClamAV error: {exc}"]
        report = (p.stdout or "") + "\n" + (p.stderr or "")
        if re.search(r"\bFOUND\b", report, re.I):
            status = "FOUND"
            reasons.append("ClamAV found a signature in " + path.name)
        elif p.returncode != 0:
            # W16y-b round 2: exit 1 means "found"; without a FOUND line it is not a clean scan.
            status = "FOUND" if status == "FOUND" else "UNKNOWN"
            reasons.append("ClamAV could not scan " + path.name)
    return status, reasons


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _vt_one(base: str, key: str, path: Path) -> tuple[str, list[str]]:
    digest = _sha256(path)
    req = urllib.request.Request(base.rstrip("/") + "/files/" + digest,
                                 headers={"x-apikey": key, "accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return "unknown to VT", []
        return "UNKNOWN", [f"VirusTotal HTTP {exc.code}"]
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return "UNKNOWN", [f"VirusTotal lookup failed: {exc.__class__.__name__}"]
    # W16y-b review: a response without analysis stats (or of the wrong shape) is UNKNOWN,
    # never clean, and never a crash.
    try:
        stats = body["data"]["attributes"]["last_analysis_stats"]
        if not isinstance(stats, dict) or not stats:
            raise ValueError("empty stats")
        malicious, suspicious = int(stats.get("malicious", 0)), int(stats.get("suspicious", 0))
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return "UNKNOWN", ["VirusTotal response did not contain analysis stats"]
    if malicious > 0:
        return "malicious", [f"VirusTotal reports malicious={malicious} for {path.name}"]
    if suspicious > 0:
        return "suspicious", [f"VirusTotal reports suspicious={suspicious} for {path.name}"]
    return "clean", []


def _vt(mpp: Path, apk: Path) -> tuple[str, dict[str, str], list[str]]:
    key = os.environ.get("VT_API_KEY", "")
    if not key:
        return "NOT_CONFIGURED", {}, []
    base = os.environ.get("PF_VT_BASE", "https://www.virustotal.com/api/v3")
    statuses: dict[str, str] = {}
    reasons: list[str] = []
    # Two requests are within VT public API's four requests/minute allowance.  Do not upload.
    for label, path in (("mpp", mpp), ("patched_apk", apk)):
        status, why = _vt_one(base, key, path)
        statuses[label] = status
        reasons.extend(why)
    if any(x == "malicious" for x in statuses.values()):
        return "malicious", statuses, reasons
    if any(x == "suspicious" for x in statuses.values()):
        return "suspicious", statuses, reasons
    if any(x == "UNKNOWN" for x in statuses.values()):
        return "UNKNOWN", statuses, reasons
    if any(x == "unknown to VT" for x in statuses.values()):
        return "unknown to VT", statuses, reasons
    return "clean", statuses, reasons


def scan(original: Path, patched: Path, mpp: Path, target: str, provider: str) -> dict[str, Any]:
    reasons: list[str] = []
    unknown = False
    if not original.is_file() or not patched.is_file() or not mpp.is_file():
        missing = [str(p) for p in (original, patched, mpp) if not p.is_file()]
        reasons.append("missing input: " + ", ".join(missing))
        return {"verdict": "HOLD", "reasons": reasons, "permissions_added": [], "new_hosts": [],
                "flags": [], "clamav": "UNKNOWN", "vt": "UNKNOWN"}

    old_perms, old_source = _run_aapt2(original)
    new_perms, new_source = _run_aapt2(patched)
    if old_perms is None or new_perms is None:
        unknown = True
        reasons.append("permission evidence UNKNOWN: " + (old_source if old_perms is None else new_source))
        added: list[str] = []
    else:
        added = sorted(new_perms - old_perms)
        sensitive = [p for p in added if SENSITIVE_PERMISSION_RE.search(p)]
        if sensitive:
            reasons.append("sensitive Android permissions added: " + ", ".join(sensitive))

    old_strings, old_hosts, old_errors = _zip_printable(original)
    new_strings, new_hosts_seen, new_errors = _zip_printable(patched)
    new_hosts = sorted(new_hosts_seen - old_hosts)
    allow = _read_allowlist()
    allowed = allow.get(provider.lower(), set()) | allow.get("*", set()) | DEFAULT_ALLOWED_HOSTS
    disallowed_hosts = [h for h in new_hosts if h not in allowed]
    if disallowed_hosts:
        reasons.append("new host(s) not on provider allowlist: " + ", ".join(disallowed_hosts))
    if old_errors or new_errors:
        unknown = True
        reasons.append("APK string extraction had unreadable entries")
    delta = "\n".join(sorted(new_strings - old_strings))
    flags: list[str] = []
    for name, pattern in FLAG_PATTERNS.items():
        if pattern.search(delta):
            flags.append(name)
    try:
        with zipfile.ZipFile(original) as z:
            old_so = {i.filename: i.CRC for i in z.infolist() if i.filename.startswith("lib/") and i.filename.endswith(".so")}
        with zipfile.ZipFile(patched) as z:
            new_so = {i.filename: i.CRC for i in z.infolist() if i.filename.startswith("lib/") and i.filename.endswith(".so")}
        flags.extend("new " + n for n in sorted(set(new_so) - set(old_so)))
        # W16y-b review: a library replaced under the same name is a change too.
        flags.extend("changed " + n for n in sorted(set(new_so) & set(old_so)) if new_so[n] != old_so[n])
    except (OSError, zipfile.BadZipFile):
        unknown = True
        reasons.append("APK library comparison UNKNOWN")
    flags = sorted(set(flags))
    if flags:
        reasons.append("new code red flag(s): " + ", ".join(flags))

    clamav, clam_reasons = _clamav([mpp, patched])
    reasons.extend(clam_reasons)
    vt, vt_details, vt_reasons = _vt(mpp, patched)
    reasons.extend(vt_reasons)

    # W16y-b review: a check that did not answer is never a pass. ClamAV must say clean;
    # VirusTotal must answer (clean, or "unknown to VT" = no reputation yet, which is normal
    # for a freshly signed build). Missing key, HTTP errors and rate limits hold the scan.
    if clamav not in ("clean", "FOUND"):
        unknown = True
        reasons.append("ClamAV result %s: not a clean scan" % clamav)
    if vt not in ("clean", "unknown to VT", "malicious", "suspicious"):
        unknown = True
        reasons.append("VirusTotal result %s: not a completed lookup" % vt)
    if clamav == "FOUND":
        verdict = "BLOCK"
    elif vt == "malicious":
        verdict = "BLOCK"
    elif any((added and SENSITIVE_PERMISSION_RE.search(p)) for p in added) or disallowed_hosts or flags:
        verdict = "HOLD"
    elif vt == "suspicious":
        verdict = "HOLD"
    elif unknown:
        verdict = "HOLD"
    else:
        verdict = "PASS"
    return {
        "target": target, "provider": provider, "verdict": verdict, "reasons": reasons,
        "permissions_added": added, "new_hosts": new_hosts, "flags": flags,
        "clamav": clamav, "vt": vt, "vt_details": vt_details,
        "permission_source": {"original": old_source, "patched": new_source},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan an original/patched APK and provider .mpp")
    parser.add_argument("original_apk")
    parser.add_argument("patched_apk")
    parser.add_argument("provider_mpp")
    parser.add_argument("target")
    parser.add_argument("provider")
    parser.add_argument("output_json")
    args = parser.parse_args(argv)
    result = scan(*(Path(x) for x in (args.original_apk, args.patched_apk, args.provider_mpp)),
                  args.target, args.provider)
    out = Path(args.output_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("PROVIDER_SCAN target=%s provider=%s verdict=%s perms_added=%d new_hosts=%d flags=%d clamav=%s vt=%s" %
          (args.target, args.provider, result["verdict"], len(result["permissions_added"]),
           len(result["new_hosts"]), len(result["flags"]), result["clamav"], result["vt"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
