#!/usr/bin/env python3
"""Qualified exact-version APK failover. No implicit source or signer admission.

Existing primaries are unchanged. A fallback is usable only after a reviewed
qualification admits exact original container bytes for a particular version.
Page/package metadata, CI signing keys and merged APKs cannot establish trust.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

import artifact_identity as identity
import github_bundle
import input_recipe as recipe
import native_payloads
import original_apk
import source_inputs
import source_variant

POLICY = "src/build/helper/source-fallbacks.json"
MAX_BYTES = 256 * 1024 * 1024
MAX_EXPANDED = 768 * 1024 * 1024
RECEIPT = ".source-fallback-receipt.json"
LIMITS = ["qualification is version-specific", "not an Android device or runtime-safety test"]


def need(ok, why):
    if not ok:
        raise ValueError("source fallback: " + why)


def version_key(value):
    need(isinstance(value, str) and re.fullmatch(r"[0-9]+(?:[.][0-9]+)*", value),
         "exact numeric version required")
    parts = [int(p) for p in value.split(".")]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def file_record(path):
    need(not path.is_symlink() and path.is_file(), "regular file required")
    size = path.stat().st_size
    need(0 < size <= MAX_BYTES, "file size outside bounds")
    result = {"bytes": size, "sha256": identity.sha(path)}
    need(path.stat().st_size == size, "file size changed during inspection")
    return result


def target(root, ident):
    rows = recipe.read_json(root, "src/targets.json")
    matches = [t for t in rows if t.get("id") == ident and t.get("enabled") is True]
    need(len(matches) == 1, "unknown, disabled or duplicate target")
    t = matches[0]
    need(re.fullmatch(r"[a-zA-Z0-9_-]+", t["apk_name"]), "invalid APK output name")
    need(t.get("source", "apkmirror") in ("apkmirror", "apkpure"), "unknown primary source")
    return t


def mapping_ok(source, mapping, package):
    need(isinstance(mapping, dict), "missing mapping")
    if source == "apkpure":
        need(set(mapping) == {"download_url"}, "unexpected APKPure mapping")
        # Reviewed app-specific URL, not an arbitrary or redirected download URL.
        need(re.fullmatch(r"https://apkpure[.]com/[a-zA-Z0-9_-]+/" +
                          re.escape(package) + r"/download", mapping["download_url"]),
             "APKPure mapping is not app-scoped")
    elif source == "apkmirror":
        need(set(mapping) == {"list_url", "org", "name"}, "unexpected APKMirror mapping")
        need(all(isinstance(mapping[k], str) and re.fullmatch(r"[a-z0-9-]+", mapping[k])
                 for k in ("org", "name")), "invalid APKMirror slug")
        need(mapping["list_url"] == "https://www.apkmirror.com/uploads/?appcategory=" +
             mapping["name"], "APKMirror category differs")
    else:
        raise ValueError("source fallback: unsupported alternate")


def policy(root):
    doc = recipe.read_json(root, POLICY)
    need(set(doc) == {"schema", "targets"} and type(doc["schema"]) is int and
         doc["schema"] == 1, "unknown policy schema")
    targets = recipe.read_json(root, "src/targets.json")
    enabled = {t["id"]: t for t in targets if t.get("enabled") is True}
    need(isinstance(doc["targets"], dict) and set(doc["targets"]) == set(enabled),
         "policy must cover every enabled target exactly")
    for ident, row in doc["targets"].items():
        need(isinstance(row, dict) and
             set(row) == {"package", "primary", "blocked_reason", "admissions"},
             "unknown policy fields")
        t = enabled[ident]
        need(row["package"] == t["package"] and row["primary"] == t.get("source", "apkmirror"),
             "policy target identity differs")
        need(isinstance(row["blocked_reason"], str) and row["blocked_reason"] and
             isinstance(row["admissions"], list), "missing policy state")
        seen = set()
        for a in row["admissions"]:
            need(isinstance(a, dict) and set(a) == {
                "source", "version_name", "version_code", "container", "certificate_sha256",
                "mapping", "evidence", "variant"}, "unknown admission fields")
            version_key(a["version_name"])
            need(isinstance(a["version_code"], str) and
                 re.fullmatch(r"[0-9]+", a["version_code"]), "invalid admitted version code")
            need(a["source"] != row["primary"], "alternate equals primary")
            mapping_ok(a["source"], a["mapping"], t["package"])
            source_variant.validate(a["variant"], a["source"], a["mapping"],
                                    a["version_name"], t["min_sdk_ceiling"])
            need(a["version_name"] not in seen, "ambiguous version admission")
            seen.add(a["version_name"])
            need(isinstance(a["certificate_sha256"], str) and
                 re.fullmatch("[0-9a-f]{64}", a["certificate_sha256"]),
                 "original signer pin missing")
            c = a["container"]
            need(isinstance(c, dict) and set(c) == {"bytes", "sha256"} and
                 type(c["bytes"]) is int and 0 < c["bytes"] <= MAX_BYTES and
                 isinstance(c["sha256"], str) and re.fullmatch("[0-9a-f]{64}", c["sha256"]),
                 "unqualified container bytes")
            # Reviewed evidence belongs in the repo; a URL alone is not admission.
            need(isinstance(a["evidence"], str) and
                 a["evidence"].startswith("docs/review/source-qualifications/") and
                 a["evidence"].endswith(".json"), "missing reviewed qualification")
            ev = recipe.read_json(root, a["evidence"])
            need(isinstance(ev, dict) and type(ev.get("schema")) is int and
                 ev.get("publisher_anchor_reviewed") is True and
                 ev.get("variant_compatibility_reviewed") is True, "qualification flags must be boolean")
            need(ev == {"schema": 1, "target": ident, "package": t["package"],
                        "source": a["source"], "version_name": a["version_name"],
                        "version_code": a["version_code"], "container": a["container"],
                        "certificate_sha256": a["certificate_sha256"],
                        "variant": a["variant"],
                        "publisher_anchor_reviewed": True,
                        "variant_compatibility_reviewed": True},
                 "qualification does not bind the admitted artifact")
    return doc


def admission(root, ident, requested):
    t = target(root, ident)
    version_key(requested)
    need(not t.get("any_version", False), "latest/any-version fallback is not allowed")
    if t.get("max_app_version"):
        need(version_key(requested) <= version_key(t["max_app_version"]), "version exceeds ceiling")
    row = policy(root)["targets"][ident]
    matches = [a for a in row["admissions"] if a["version_name"] == requested]
    need(len(matches) == 1, "BLOCKED_UNQUALIFIED_SOURCE: " + row["blocked_reason"])
    return t, matches[0]


def apk_metadata(root, apk, env, original=False):
    return original_apk.metadata(root, apk, env) if original else identity.metadata(root, apk, env)


def apk_certificate(root, apk, env):
    # Never emit raw verifier output or filenames to the public build log.
    with contextlib.redirect_stdout(io.StringIO()):
        return identity.apk_signer(root, apk, env)["certificate_sha256"]


def inspect_original(root, raw, t, a, env, scratch):
    """Verify every original split BEFORE APKEditor can invalidate signatures."""
    before = file_record(raw)
    need(before == a["container"], "original container differs from qualified bytes")
    github_bundle.zip_inspect(raw, MAX_BYTES, MAX_EXPANDED, 20000)
    with zipfile.ZipFile(raw) as archive:
        names = archive.namelist()
        standalone = names.count("AndroidManifest.xml") == 1
        need(standalone == (a["variant"]["kind"] == "apk"), "original container type differs")
        if standalone:
            paths = [raw]
        else:
            members = [n for n in names if n.endswith(".apk")]
            need(1 <= len(members) <= 128, "unrecognized or oversized split set")
            paths = []
            # Generated paths only. Never extract archive-supplied filesystem names.
            for index, member in enumerate(members):
                path = scratch / ("split-" + str(index) + ".apk")
                with archive.open(member) as src, path.open("xb") as dst:
                    shutil.copyfileobj(src, dst, 1024 * 1024)
                paths.append(path)
    records, abis, manifests = [], set(), []
    expanded_total = 0
    for apk in paths:
        prior = file_record(apk)
        with zipfile.ZipFile(apk) as z:
            expanded_total += sum(i.file_size for i in z.infolist())
        need(expanded_total <= MAX_EXPANDED, "aggregate split expansion exceeds bound")
        github_bundle.zip_inspect(apk, MAX_BYTES, MAX_EXPANDED, 20000)
        with zipfile.ZipFile(apk) as z:
            need(z.namelist().count("AndroidManifest.xml") == 1, "split manifest missing")
            # A nested APK inside an alleged standalone is not a qualified split set.
            need(not any(n.endswith(".apk") for n in z.namelist()), "nested APK refused")
            for name in z.namelist():
                if name.startswith("lib/") and not name.endswith("/"):
                    bits = name.split("/")
                    need(len(bits) == 3 and bits[1] in
                         ("arm64-v8a", "armeabi-v7a", "x86", "x86_64"), "unknown native layout")
                    abis.add(bits[1])
                    if bits[1] == "arm64-v8a":
                        with z.open(name) as stream:
                            header = stream.read(20)
                        # Non-ELF data remains subject to the existing final-output gate.
                        if header.startswith(b"\x7fELF"):
                            native_payloads.arm64_elf(header, name)
        meta = apk_metadata(root, apk, env, original=True)
        split = meta.get("split")
        need(meta["package"] == t["package"] and
             (meta["version_name"] == a["version_name"] or
              (split is not None and meta["version_name"] == "")) and
             meta["version_code"] == a["version_code"], "original package/version mismatch")
        if meta["min_sdk"] is None:
            # Only a named configuration split may inherit; the base check below stays strict.
            need(original_apk.is_config_split(split), "original minimum SDK missing")
        else:
            need(type(meta["min_sdk"]) is int and
                 0 < meta["min_sdk"] <= t["min_sdk_ceiling"], "original SDK ceiling exceeded")
            need(meta["min_sdk"] == a["variant"]["min_sdk"], "original SDK differs from reviewed variant")
        need(apk_certificate(root, apk, env) == a["certificate_sha256"], "original signer differs")
        need(file_record(apk) == prior, "original changed during verification")
        records.append(prior)
        manifests.append(meta)
    names = [m.get("split") for m in manifests]
    need(names.count(None) == 1, "exactly one original base required")
    need(all(m["min_sdk"] == a["variant"]["min_sdk"] for m in manifests if m.get("split") is None),
         "original base minimum SDK missing")
    need(len(names) == len(set(names)), "duplicate original split names")
    need(sorted(abis) == a["variant"]["abis"], "original ABI inventory differs")
    need(file_record(raw) == before, "container changed during verification")
    return {"container": before, "splits": records, "standalone": standalone,
            "abis": sorted(abis), "certificate_sha256": a["certificate_sha256"]}


def run_checked(args, cwd, env, timeout=1200):
    # stdout/stderr can include transport response details. Do not echo them.
    result = subprocess.run(args, cwd=cwd, env=env, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, timeout=timeout, check=False)
    need(result.returncode == 0, "alternate adapter/tool refused")


def validate_receipt(root, ident, receipt, apk):
    need(isinstance(receipt, dict) and set(receipt) == {
        "schema", "target", "source", "requested_version", "original", "patcher_input", "limits"},
        "unknown receipt fields")
    need(type(receipt["schema"]) is int and receipt["schema"] == 1 and
         receipt["target"] == ident and receipt["limits"] == LIMITS, "receipt identity differs")
    _, a = admission(root, ident, receipt["requested_version"])
    need(receipt["source"] == a["source"] and
         receipt["patcher_input"] == {k: apk[k] for k in ("bytes", "sha256")},
         "receipt does not bind consumed APK")
    original = receipt["original"]
    need(isinstance(original, dict) and set(original) ==
         {"container", "splits", "standalone", "abis", "certificate_sha256"},
         "unknown original proof")
    need(original["container"] == a["container"] and
         original["certificate_sha256"] == a["certificate_sha256"] and
         type(original["standalone"]) is bool and
         isinstance(original["splits"], list) and 1 <= len(original["splits"]) <= 128,
         "receipt differs from qualified original")
    for split in original["splits"]:
        need(isinstance(split, dict) and set(split) == {"bytes", "sha256"} and
             type(split["bytes"]) is int and 0 < split["bytes"] <= MAX_BYTES and
             isinstance(split["sha256"], str) and re.fullmatch("[0-9a-f]{64}", split["sha256"]),
             "invalid split proof")
    need(isinstance(original["abis"], list) and
         all(isinstance(a, str) and a in ("arm64-v8a", "armeabi-v7a", "x86", "x86_64")
             for a in original["abis"]) and
         original["abis"] == sorted(set(original["abis"])) and
         (not original["abis"] or "arm64-v8a" in original["abis"]), "invalid original ABI proof")
    if original["standalone"]:
        need(original["splits"] == [original["container"]], "standalone proof differs")
    need(original["standalone"] == (a["variant"]["kind"] == "apk") and
         original["abis"] == a["variant"]["abis"], "receipt variant differs")
    return receipt


def read_receipt(root, ident, apk):
    path = root / RECEIPT
    if not path.exists() and not path.is_symlink():
        return None
    return validate_receipt(root, ident, recipe.read_json(root, RECEIPT), apk)


def execute(root, ident, requested, env):
    root = Path(root).resolve()
    t, a = admission(root, ident, requested)  # No directories/network until admitted.
    need(not (root / RECEIPT).exists() and not (root / RECEIPT).is_symlink(),
         "existing receipt; use a fresh checkout")
    clean = source_inputs.clean_env(env)
    for key in ("GH_TOKEN", "GITHUB_TOKEN", "KEYSTORE_ALIAS", "KEYSTORE_PASS"):
        clean.pop(key, None)
    # Dedicated root is deliberately retained on failure and success.
    work = Path(tempfile.mkdtemp(prefix=".source-fallback-", dir=root))
    for rel in ("src/build",):
        source = root / rel
        need(not source.is_symlink() and
             not any(p.is_symlink() for p in source.rglob("*")), "symlink in adapter source")
        shutil.copytree(source, work / rel, ignore=shutil.ignore_patterns("__pycache__"))
    (work / "src/targets.json").write_bytes((root / "src/targets.json").read_bytes())
    # Supply ONLY the reviewed mapping for this target and source.
    (work / "src/build/helper/apps.json").write_text(
        json.dumps({a["source"]: {t["package"]: a["mapping"]}}) + "\n")
    (work / "qualified-variant.json").write_text(json.dumps({
        "source": a["source"], "package": t["package"], "version": requested,
        "mapping": a["mapping"], "ceiling": t["min_sdk_ceiling"], "variant": a["variant"]}) + "\n")
    run_checked(["bash", "src/build/source_alternate.sh", ident, requested, a["source"]],
                work, clean)
    download = work / "download"
    need(download.is_dir() and not download.is_symlink(), "alternate download missing")
    files = list(download.iterdir())
    need(len(files) == 1, "ambiguous alternate outputs")
    scratch = work / "verified-originals"
    scratch.mkdir()
    proof = inspect_original(work, files[0], t, a, clean, scratch)
    result = work / "checked-source.apk"
    if proof["standalone"]:
        shutil.copyfile(files[0], result)
    else:
        # Existing pinned APKEditor; its bytes were verified by utils/tooling.
        run_checked(["java", "-jar", "APKEditor.jar", "m", "-i", str(files[0]),
                     "-o", str(result)], work, clean, 600)
    result_before = file_record(result)
    need(result_before["bytes"] > 1000000, "merged APK below existing size gate")
    github_bundle.zip_inspect(result, MAX_BYTES, MAX_EXPANDED, 20000)
    meta = apk_metadata(work, result, clean)
    need(meta["package"] == t["package"] and meta["version_name"] == requested and
         meta["version_code"] == a["version_code"] and
         type(meta["min_sdk"]) is int and 0 < meta["min_sdk"] <= t["min_sdk_ceiling"],
         "merged package/version/SDK differs")
    need(file_record(result) == result_before, "merged bytes changed during inspection")
    receipt = {"schema": 1, "target": ident, "source": a["source"],
               "requested_version": requested, "original": proof,
               "patcher_input": result_before,
               "limits": LIMITS}
    validate_receipt(root, ident, receipt, result_before)
    (work / "receipt.json").write_text(json.dumps(receipt, sort_keys=True) + "\n")
    outdir = root / "download"
    need(not outdir.is_symlink() and (not outdir.exists() or outdir.is_dir()), "unsafe output directory")
    outdir.mkdir(exist_ok=True)
    final = outdir / (t["apk_name"] + ".apk")
    need(not final.is_symlink() and (not final.exists() or final.is_file()), "unsafe existing output")
    candidate = work / "install.cand"
    shutil.copyfile(result, candidate)
    need(file_record(candidate) == result_before, "install bytes differ")
    # Preserve a partial primary rather than deleting or silently overwriting it.
    if final.exists():
        final.rename(work / "preserved-primary.apk")
    os.replace(candidate, final)
    need(file_record(final) == result_before, "installed fallback bytes differ")
    with (root / RECEIPT).open("x") as stream:
        json.dump(receipt, stream, sort_keys=True)
        stream.write("\n")
    need(read_receipt(root, ident, file_record(final)) == receipt, "installed receipt differs")
    return receipt


def main():
    try:
        if sys.argv[1:] == ["coverage"]:
            doc = policy(Path.cwd())
            print(json.dumps({k: {"qualified_versions": len(v["admissions"]),
                                  "blocked_reason": v["blocked_reason"]}
                              for k, v in doc["targets"].items()}, indent=2))
            return 0
        need(len(sys.argv) == 3, "usage: source_fallback.py TARGET EXACT_VERSION | coverage")
        receipt = execute(Path.cwd(), sys.argv[1], sys.argv[2], dict(os.environ))
        print("SOURCE_FALLBACK_VERIFIED " + json.dumps({
            "target": receipt["target"], "source": receipt["source"],
            "version": receipt["requested_version"],
            "sha256": receipt["patcher_input"]["sha256"]}, sort_keys=True))
        return 0
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError,
            zipfile.BadZipFile, RuntimeError):
        # Fixed diagnostic, not untrusted URLs, filenames, metadata or verifier text.
        print("SOURCE_FALLBACK_REFUSED: unqualified source or failed original/identity gate",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
