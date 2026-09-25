"""Pure community-index comparison candidate. No network or repository writes.

Discovery evidence only: never approval to add providers, patches or builds.
Missing applicability means UNKNOWN, not universal and not irrelevant.
"""
import collections
import hashlib
import html
import json
import re

PKG = re.compile(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+")
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*")
VOLATILE = {"stars", "hotRank", "firstSeen", "appFirstSeen", "appUpdates", "avatarUrl", "bundleIconUrl"}
LIMITS = [
    "Index metadata only, not provider bundle execution, provenance or safety approval.",
    "Unknown patch applicability remains visible; it is not assumed universal.",
    "Duplicate patch names retain every variant; changed variants are not guessed renames.",
    "Options/defaults/versions are compared only when represented by the index.",
    "No baseline acknowledgement, provider wiring, patch selection or build authority.",
]


def need(value, message):
    if not value:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def string(value, label):
    need(isinstance(value, str) and value.strip() and len(value) <= 2000 and
         not any(ord(c) < 32 or ord(c) == 127 for c in value), "INVALID_" + label)
    return value


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def read_json(data):
    need(isinstance(data, bytes) and 0 < len(data) <= 12 * 1024 * 1024, "INDEX_SIZE")
    return json.loads(data, object_pairs_hook=unique_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("NONFINITE_JSON")))


def compatibility(value):
    """Return package-keyed records while retaining all version/target fields."""
    if value in ([], {}):
        return {}
    rows = {}
    if isinstance(value, dict):
        # Older provider format: {"com.example.app": ["1.0", ...]}.
        for package, versions in value.items():
            need(PKG.fullmatch(package), "UNRECOGNIZED_COMPATIBILITY_MAP")
            need(isinstance(versions, list) and all(isinstance(v, str) and v for v in versions),
                 "INVALID_VERSION_LIST")
            rows[package] = [{"versions": sorted(set(versions))}]
    elif isinstance(value, list):
        for entry in value:
            need(isinstance(entry, dict), "INVALID_COMPATIBILITY_ENTRY")
            package = entry.get("packageName")
            need(isinstance(package, str) and PKG.fullmatch(package), "INVALID_PACKAGE")
            normalized = dict(entry)
            normalized.pop("packageName")
            # Display names do not change patch applicability.
            normalized.pop("name", None)
            if "targets" in normalized:
                targets = normalized["targets"]
                need(isinstance(targets, list) and all(isinstance(t, dict) for t in targets),
                     "INVALID_COMPATIBILITY_TARGETS")
                normalized["targets"] = sorted(targets, key=canonical)
            rows.setdefault(package, [])
            if normalized not in rows[package]:
                rows[package].append(normalized)
    else:
        raise ValueError("UNKNOWN_COMPATIBILITY_SHAPE")
    return {k: sorted(v, key=canonical) for k, v in sorted(rows.items())}


def inventory(data):
    need(isinstance(data, dict), "INDEX_NOT_OBJECT")
    bundles, compat = data.get("bundles"), data.get("compatibilities")
    need(isinstance(bundles, list) and 0 < len(bundles) <= 5000, "EMPTY_OR_EXCESSIVE_BUNDLES")
    need(isinstance(compat, (list, dict)) and len(compat) > 0, "EMPTY_COMPATIBILITIES")
    table = {str(k): compatibility(v) for k, v in (enumerate(compat) if isinstance(compat, list) else compat.items())}
    result, total, unknown, variants = {}, 0, 0, 0
    for bundle in bundles:
        need(isinstance(bundle, dict), "INVALID_BUNDLE")
        host, repo = bundle.get("source", "github"), bundle.get("repo")
        need(host in ("github", "gitlab") and isinstance(repo, str) and REPO.fullmatch(repo),
             "INVALID_PROVIDER")
        key = host + ":" + repo.lower()
        need(key not in result, "DUPLICATE_PROVIDER")
        patches = bundle.get("patches")
        need(isinstance(patches, list) and len(patches) <= 50000, "INVALID_PATCH_INVENTORY")
        if "patchCount" in bundle:
            need(type(bundle["patchCount"]) is int and bundle["patchCount"] == len(patches),
                 "PATCH_COUNT_MISMATCH")
        grouped = collections.defaultdict(list)
        apps = bundle.get("targetApps")
        need(isinstance(apps, list) and all(isinstance(a, str) and PKG.fullmatch(a) for a in apps),
             "INVALID_TARGET_APPS")
        for patch in patches:
            need(isinstance(patch, dict), "INVALID_PATCH")
            name = string(patch.get("name"), "PATCH_NAME")
            record = dict(patch)
            refs = [record.pop(field) for field in ("compatiblePackagesKey", "compatibilityKey") if field in record]
            need(len(refs) <= 1, "AMBIGUOUS_COMPATIBILITY_REFERENCE")
            resolved = {}
            if refs and refs[0] is not None:
                ref = refs[0]
                need(type(ref) in (int, str) and str(ref) in table, "MISSING_COMPATIBILITY_REFERENCE")
                resolved = table[str(ref)]
            record["compatibility"] = resolved
            record["applicability"] = "DECLARED" if resolved else "UNKNOWN"
            total += 1
            unknown += not resolved
            grouped[name].append(record)
        for name in grouped:
            grouped[name].sort(key=canonical)
            variants += max(0, len(grouped[name]) - 1)
        metadata = {k: v for k, v in bundle.items() if k not in VOLATILE | {"patches", "patchCount", "source", "repo"}}
        metadata["targetApps"] = sorted(set(apps))
        result[key] = dict(identity=key, source=host, repo=repo, metadata=metadata,
                           patches=dict(sorted(grouped.items())))
    need(total > 0, "ZERO_PATCH_COVERAGE")
    return dict(providers=dict(sorted(result.items())),
                coverage=dict(bundles=len(bundles), patches=total, compatibility_rows=len(table),
                              unknown_applicability_patches=unknown, duplicate_name_variants=variants))


def scope(targets):
    need(isinstance(targets, list) and targets, "INVALID_TARGETS")
    packages, wired, ids = set(), set(), set()
    for target in targets:
        need(isinstance(target, dict) and type(target.get("enabled")) is bool, "INVALID_TARGET")
        need(target.get("id") not in ids, "DUPLICATE_TARGET")
        ids.add(target.get("id"))
        if not target["enabled"]:
            continue
        package = target.get("package")
        need(isinstance(package, str) and PKG.fullmatch(package), "INVALID_TARGET_PACKAGE")
        packages.add(package)
        providers = target.get("candidates", []) + target.get("extra_bundles", [])
        need(providers, "EMPTY_WIRING")
        for p in providers:
            host = p.get("host", "github")
            repo = str(p.get("owner")) + "/" + str(p.get("repo"))
            need(host in ("github", "gitlab") and REPO.fullmatch(repo), "INVALID_WIRING")
            wired.add((package, host + ":" + repo.lower()))
    need(packages, "ZERO_ENABLED_TARGETS")
    return packages, wired


def patch_packages(records):
    return sorted({pkg for record in records for pkg in record["compatibility"]})


def fields_changed(before, after):
    keys = set().union(*(r.keys() for r in before + after))
    return sorted(k for k in keys if sorted((canonical(r.get(k)) for r in before)) !=
                  sorted((canonical(r.get(k)) for r in after)))


def compare(old_data, new_data, targets):
    old, new = inventory(old_data), inventory(new_data)
    packages, wired = scope(targets)
    events = []
    def event(kind, provider, before, after, name=None):
        if kind.startswith("PATCH_"):
            rows = before + after
            apps = patch_packages(rows)
            unknown = any(r["applicability"] == "UNKNOWN" for r in rows)
            fields = fields_changed(before, after)
            # Same-name patches can describe unrelated apps. Attribute only the
            # changed per-package projection, not every app in the name group.
            def projection(records, package):
                selected = []
                for record in records:
                    if package in record["compatibility"]:
                        item = dict(record)
                        item["compatibility"] = {package: record["compatibility"][package]}
                        selected.append(item)
                return sorted(selected, key=canonical)
            apps = [p for p in apps if projection(before, p) != projection(after, p)]
        else:
            rows = [r for r in (before, after) if r]
            apps = sorted({a for r in rows for a in r["metadata"]["targetApps"]} |
                          {a for r in rows for variants in r["patches"].values() for a in patch_packages(variants)})
            unknown = any(v["applicability"] == "UNKNOWN" for r in rows for variants in r["patches"].values() for v in variants)
            fields = sorted(k for k in set((before or {}).get("metadata", {})) | set((after or {}).get("metadata", {}))
                            if (before or {}).get("metadata", {}).get(k) != (after or {}).get("metadata", {}).get(k))
        affected = sorted(packages.intersection(apps))
        # Keep every event; relevance is classification, never a pre-comparison filter.
        events.append(dict(kind=kind, provider=provider, patch=name, changed_fields=fields,
                           packages=apps, affected_packages=affected,
                           applicability_unknown=unknown,
                           relevance="YOUR_APPS" if affected else "UNKNOWN_SCOPE" if unknown else "OTHER_APPS",
                           before=before, after=after))
    for key in sorted(set(old["providers"]) | set(new["providers"])):
        before, after = old["providers"].get(key), new["providers"].get(key)
        if before is None:
            event("PROVIDER_ADDED", key, None, after)
            continue
        if after is None:
            event("PROVIDER_REMOVED", key, before, None)
            continue
        if before["metadata"] != after["metadata"]:
            event("PROVIDER_METADATA_CHANGED", key, before, after)
        for name in sorted(set(before["patches"]) | set(after["patches"])):
            a, b = before["patches"].get(name, []), after["patches"].get(name, [])
            if a != b:
                kind = "PATCH_ADDED" if not a else "PATCH_REMOVED" if not b else "PATCH_CHANGED"
                event(kind, key, a, b, name)
    offers = []
    for key, provider in new["providers"].items():
        apps = {a for records in provider["patches"].values() for a in patch_packages(records)}
        for pkg in sorted(packages & apps):
            if (pkg, key) not in wired:
                offers.append(dict(package=pkg, provider=key, state="UNWIRED_REVIEW_REQUIRED"))
    return dict(schema="pf-community-diff-candidate-v1", status="CHANGED" if events else "NO_OBSERVED_CHANGE",
                old_coverage=old["coverage"], new_coverage=new["coverage"],
                old_semantic_sha256=digest(old["providers"]), new_semantic_sha256=digest(new["providers"]),
                event_count=len(events), relevant_events=sum(e["relevance"] == "YOUR_APPS" for e in events),
                unknown_scope_events=sum(e["relevance"] == "UNKNOWN_SCOPE" for e in events),
                events=events, unwired_offers=offers, limits=LIMITS)


def safe(value):
    return html.escape(str(value)).replace("@", "&#64;").replace("`", "&#96;").replace("\n", " ")


def render(report):
    lines = ["# Community changes: " + report["status"], "",
             "Compared " + str(report["old_coverage"]["bundles"]) + " -> " +
             str(report["new_coverage"]["bundles"]) + " providers; " + str(report["event_count"]) + " events.",
             "Relevant: " + str(report["relevant_events"]) + "; unknown scope: " + str(report["unknown_scope_events"]) + ".",
             "", *LIMITS, ""]
    # Full relevant inventory first. No top-N cuts before or after classification.
    for relevance in ("YOUR_APPS", "UNKNOWN_SCOPE", "OTHER_APPS"):
        lines += ["## " + relevance]
        for event in report["events"]:
            if event["relevance"] == relevance:
                lines += ["- " + safe(event["kind"]) + " | " + safe(event["provider"]) + " | " +
                          safe(event["patch"] or "(provider)") + " | fields: " +
                          safe(", ".join(event["changed_fields"])) + " | apps: " + safe(", ".join(event["packages"]))]
    lines += ["", "## Unwired providers for configured apps"]
    lines += ["- " + safe(row["package"]) + " | " + safe(row["provider"]) + " | review required"
              for row in report["unwired_offers"]]
    return "\n".join(lines) + "\n"
