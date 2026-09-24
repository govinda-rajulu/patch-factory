#!/usr/bin/env python3
"""Bounded runtime/public invocation evidence, not complete transitive closure."""
import hashlib
import os
from pathlib import Path
import platform
import shutil
import stat

import input_recipe as recipe
import patch_target
import shadow_inputs as shadow

DOMAIN = "patch-factory/execution-observation/v1"
PATH = "build-evidence/execution-inputs.json"
LIMITS = ["observed runtime subset only; shared-library/container/network closure incomplete",
          "implicit defaults bound by exact patcher/bundle bytes, not enumerated or approved",
          "same-run observation, not independent attestation or skip authority"]


def public_command(root, ident, winner, env):
    # Actual producer, dummy credentials. No real signing values read/hashed.
    clean = {"KEYSTORE_PASS": "OMITTED", "KEYSTORE_ALIAS": "OMITTED"}
    if env.get("COE"):
        clean["COE"] = "true"
    root = Path(root).resolve()
    args = patch_target.command(root, ident, winner, clean)
    forbidden = ("--keystore=", "--keystore-password=", "--keystore-entry-alias=",
                 "--keystore-entry-password=", "--out=")
    result = []
    for arg in args:
        if arg.startswith(forbidden):
            continue
        prefix = str(root) + "/"
        result.append(arg[len(prefix):] if arg.startswith(prefix) else arg)
    return {"argv": result, "defaults": "delegated to exact patcher and ordered bundle bytes",
            "approval": "not evaluated"}


def file_identity(path, maximum=512 * 1024 * 1024):
    path = Path(path).resolve(strict=True)
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= maximum:
            raise ValueError("invalid runtime file")
        h, size = hashlib.sha256(), 0
        for b in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(b)
            if size > maximum:
                raise ValueError("runtime file too large")
            h.update(b)
        after = os.fstat(stream.fileno())
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (
            after.st_size, after.st_mtime_ns, after.st_ino) or size != before.st_size:
        raise ValueError("runtime file changed")
    return {"bytes": size, "sha256": h.hexdigest(), "executable": bool(before.st_mode & stat.S_IXUSR)}


def runtime(env):
    # Do not persist or hash potentially secret-bearing JVM injection values.
    if any(env.get(k) for k in ("JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "_JAVA_OPTIONS", "CLASSPATH")):
        raise ValueError("unmodeled JVM configuration")
    rows = {}
    for tool in ("java", "bash", "python3", "unzip"):
        path = shutil.which(tool, path=env.get("PATH"))
        if not path:
            raise ValueError("runtime tool missing")
        rows[tool] = file_identity(path)
    java = Path(shutil.which("java", path=env.get("PATH"))).resolve()
    home = java.parent.parent
    for relative in ("release", "lib/modules", "lib/server/libjvm.so", "conf/security/java.security"):
        rows["java/" + relative] = file_identity(home / relative)
    rows["os-release"] = file_identity("/etc/os-release", 65536)
    locale = {k: recipe.digest(env.get(k, "")) for k in ("LANG", "LC_ALL", "TZ")}
    return {"files": rows, "kernel": platform.release(), "machine": platform.machine(),
            "locale_sha256": locale}


def capture(root, ident, winner, env):
    root = Path(root).resolve()
    if (root / PATH).exists() or (root / PATH).is_symlink():
        raise ValueError("execution observation already exists")
    try:
        material = {"invocation": public_command(root, ident, winner, env), "runtime": runtime(env)}
        body = {"status": "OBSERVED_SUBSET", "material": material}
    except (ValueError, OSError, KeyError, StopIteration):
        body = {"status": "UNKNOWN", "reason": "RUNTIME_OR_INVOCATION_UNAVAILABLE"}
    doc = shadow.seal({"domain": DOMAIN, "schema": 1, "target": ident, "winner": winner,
                       "limits": LIMITS, **body})
    shadow.write(root, PATH, doc)
    return doc


def verify(root, ident, winner, env):
    doc = recipe.read_json(Path(root), PATH)
    shadow.unseal(doc, DOMAIN)
    shadow.need(doc["target"] == ident and doc["winner"] == winner and
                doc["limits"] == LIMITS, "execution identity/coverage differs")
    shadow.need(doc["status"] in ("OBSERVED_SUBSET", "UNKNOWN"), "invalid execution state")
    if doc["status"] == "OBSERVED_SUBSET":
        shadow.need(set(doc) == {"domain", "schema", "target", "winner", "limits", "status", "material", "sha256"},
                    "unexpected execution fields")
        shadow.need(doc["material"] == {
            "invocation": public_command(root, ident, winner, env), "runtime": runtime(env)},
            "runtime/invocation changed since patching")
    else:
        shadow.need(set(doc) == {"domain", "schema", "target", "winner", "limits", "status", "reason", "sha256"} and
                    doc["reason"] == "RUNTIME_OR_INVOCATION_UNAVAILABLE", "invalid unknown observation")
    return doc
