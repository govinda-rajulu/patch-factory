"""Pure community-index comparison candidate. No network or repository writes.

Discovery evidence only: never approval to add providers, patches or builds.
Missing applicability means UNKNOWN, not universal and not irrelevant.
"""
import collections
import hashlib
import html
import json
import re
import sys as _sys
from pathlib import Path as _Path
try:
    import extra_providers as _extra_providers
except ImportError:  # direct callers may load this module without src/etc on sys.path
    _sys.path.insert(0, str(_Path(__file__).resolve().parent))
    import extra_providers as _extra_providers
_sys.path.insert(0, str(_Path(__file__).resolve().parent))  # W15e: readable.py lives beside this file

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
    # W16n (live 26 Oct 2026, run 40294788256): the index listed one repository twice and the
    # whole watch stopped with DUPLICATE_PROVIDER. Our identity is the repository (that is what a
    # target wires and builds from), so every bundle of one repository merges into one provider:
    # patch variants are all kept, identical records once, differing metadata kept as a sorted
    # list. Each merge is named in coverage and in the report, never silent.
    groups = collections.OrderedDict()
    for bundle in bundles:
        need(isinstance(bundle, dict), "INVALID_BUNDLE")
        host, repo = bundle.get("source", "github"), bundle.get("repo")
        need(host in ("github", "gitlab") and isinstance(repo, str) and REPO.fullmatch(repo),
             "INVALID_PROVIDER")
        groups.setdefault(host + ":" + repo.lower(), []).append(bundle)
    result, total, unknown, variants, merged = {}, 0, 0, 0, []
    for key, members in groups.items():
        if len(members) > 1:
            merged.append(dict(provider=key, bundles=len(members)))
        grouped = collections.defaultdict(list)
        apps_all, metas = set(), []
        for bundle in members:
            patches = bundle.get("patches")
            need(isinstance(patches, list) and len(patches) <= 50000, "INVALID_PATCH_INVENTORY")
            if "patchCount" in bundle:
                need(type(bundle["patchCount"]) is int and bundle["patchCount"] == len(patches),
                     "PATCH_COUNT_MISMATCH")
            apps = bundle.get("targetApps")
            need(isinstance(apps, list) and all(isinstance(a, str) and PKG.fullmatch(a) for a in apps),
                 "INVALID_TARGET_APPS")
            apps_all.update(apps)
            seen = collections.defaultdict(list)
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
                seen[name].append(record)
            for name, records in seen.items():
                # Within one bundle every variant stays; a record an earlier bundle of the same
                # repository already gave is not counted twice.
                earlier = list(grouped[name])
                for record in records:
                    if record in earlier:
                        earlier.remove(record)
                        continue
                    grouped[name].append(record)
            metas.append({k: v for k, v in bundle.items() if k not in VOLATILE | {"patches", "patchCount", "source", "repo", "targetApps"}})
        for name in grouped:
            grouped[name].sort(key=canonical)
            variants += max(0, len(grouped[name]) - 1)
            total += len(grouped[name])
            unknown += sum(r["applicability"] == "UNKNOWN" for r in grouped[name])
        metadata = {}
        for field in sorted({k for m in metas for k in m}):
            values = sorted({canonical(m.get(field)) for m in metas})
            metadata[field] = json.loads(values[0]) if len(values) == 1 else [json.loads(v) for v in values]
        metadata["targetApps"] = sorted(apps_all)
        # Order-independent display name: the sorted first of the spellings the index used.
        repo = sorted(m["repo"] for m in members)[0]
        result[key] = dict(identity=key, source=key.split(":", 1)[0], repo=repo, metadata=metadata,
                           patches=dict(sorted(grouped.items())))
    need(total > 0, "ZERO_PATCH_COVERAGE")
    return dict(providers=dict(sorted(result.items())),
                coverage=dict(bundles=len(bundles), patches=total, compatibility_rows=len(table),
                              unknown_applicability_patches=unknown, duplicate_name_variants=variants,
                              providers=len(result),
                              merged_providers=sorted(merged, key=lambda m: m["provider"])))


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



def _version_values(value):
    """Collect version strings from the index's two compatibility shapes."""
    found = set()
    if isinstance(value, str) and value.strip():
        found.add(value.strip())
    elif isinstance(value, dict):
        for key, item in value.items():
            if key in ("version", "versionName", "currentVersion"):
                found.update(_version_values(item))
            elif key == "versions":
                found.update(_version_values(item))
            elif key == "targets":
                found.update(_version_values(item))
            elif isinstance(item, (dict, list)):
                found.update(_version_values(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_version_values(item))
    return found


def _target_current_version(target):
    """Use an explicit current app version when a target supplies one.

    ``max_app_version`` is a useful fallback for older target records; it is a
    ceiling, not silently treated as a current version when a better field is
    present.
    """
    for key in ("current_version", "current_app_version", "app_version", "version", "max_app_version"):
        value = target.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def rank_providers(index_data, targets):
    """Rank community providers for each configured app.

    Ranking is deliberately deterministic and observation-only. MorpheApp is
    official; it sorts before other providers, followed by applicable patch
    count, support for the configured app version, the number of supported
    versions, and freshness. ``better`` is true only when an alternative has a
    strictly better rank tuple than the configured provider. Missing current
    versions remain visible as unknown rather than being treated as support.
    """
    parsed = inventory(index_data)
    providers = parsed["providers"]
    extra_rows = _extra_providers.load()
    extra_by_key = {("github:" + r["owner"] + "/" + r["repo"]).lower(): r for r in extra_rows}
    out = []
    for target in targets:
        if not target.get("enabled"):
            continue
        package = target.get("package")
        if not isinstance(package, str):
            continue
        configured = {
            (str(p.get("owner")) + "/" + str(p.get("repo"))).lower()
            for p in target.get("candidates", []) + target.get("extra_bundles", [])
            if isinstance(p, dict) and not p.get("fallback")
        }
        current = _target_current_version(target)
        rows = []
        for key, provider in providers.items():
            if package not in (provider.get("metadata", {}).get("targetApps") or []):
                continue
            applicable = []
            for variants in provider.get("patches", {}).values():
                for patch in variants:
                    compat = patch.get("compatibility") or {}
                    if not compat or package not in compat:
                        # The index explicitly uses an empty compatibility
                        # record for a universal patch; unknown remains a
                        # countable finding but is not claimed applicable.
                        if compat == {} and patch.get("applicability") == "UNKNOWN":
                            applicable.append(patch)
                        elif compat == {} and patch.get("applicability") == "DECLARED":
                            applicable.append(patch)
                        continue
                    applicable.append(patch)
            supported = set()
            for variants in provider.get("patches", {}).values():
                for patch in variants:
                    compat = patch.get("compatibility") or {}
                    for record in compat.get(package, []):
                        supported.update(_version_values(record))
            meta = provider.get("metadata", {})
            freshness = meta.get("appUpdates", {}).get(package) if isinstance(meta.get("appUpdates"), dict) else None
            if freshness is None:
                freshness = meta.get("updatedAt") or 0
            if isinstance(freshness, list):
                # W16n: a merged provider keeps every updatedAt; rank on the newest one.
                numbers = [v for v in freshness if type(v) in (int, float)]
                freshness = max(numbers) if numbers else 0
            repo = provider.get("repo", "")
            owner = repo.split("/", 1)[0].lower() if "/" in repo else ""
            official = owner == "morpheapp"
            current_supported = current in supported if current else None
            # Unknown current support must not beat an explicit supported
            # version. It remains a visible field in the rendered rank.
            rank = (int(official), len(applicable), int(current_supported is True),
                    len(supported), freshness if isinstance(freshness, (int, float)) else 0)
            extra = extra_by_key.get((str(provider.get("source", "github")) + ":" + repo).lower())
            rows.append(dict(repo=repo, source=provider.get("source"), official=official,
                             patch_count=len(applicable), supported_versions=sorted(supported),
                             current_version=current, supports_current=current_supported,
                             freshness=freshness, configured=repo.lower() in configured, rank=rank,
                             **({"extra_watch": True, "why": extra["why"]} if extra else {})))
        # The community index intentionally omits the Hush* repositories.  Keep
        # their existence visible in the ranker as zero-evidence, configured
        # sources; no patch count or adoption decision is inferred.
        indexed = {(str(provider.get("source", "github")) + ":" + str(provider.get("repo", "")).lower())
                   for provider in providers.values()}
        for source in extra_rows:
            repo = source["owner"] + "/" + source["repo"]
            key = "github:" + repo.lower()
            if package not in source["packages"] or key in indexed:
                continue
            rows.append(dict(repo=repo, source="github", official=False,
                             patch_count=0, supported_versions=[], current_version=current,
                             supports_current=None, freshness=0,
                             configured=repo.lower() in configured, rank=(0, 0, 0, 0, 0),
                             extra_watch=True, why=source["why"]))
        rows.sort(key=lambda row: (row["rank"], row["repo"].lower()), reverse=True)
        configured_rows = [row for row in rows if row["configured"]]
        best_configured = max((row["rank"] for row in configured_rows), default=None)
        alternatives = [row for row in rows if not row["configured"]]
        better = [row for row in alternatives if best_configured is None or row["rank"] > best_configured]
        out.append(dict(app=target.get("id"), package=package, current_version=current,
                        configured=sorted(configured), providers=rows,
                        better=better, better_exists=bool(better)))
    return out


# Name used by callers that describe this as the Community provider ranker.
provider_ranker = rank_providers

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
    """W15e (owner, 22 Oct 2026): grouped tables; every event is still listed (no top-N cut),
    OTHER_APPS folded because it is the long one. Style: docs/review/REPORT-STYLE.md."""
    import collections
    import readable
    mine = [e for e in report["events"] if e["relevance"] == "YOUR_APPS"]
    lines = readable.headline("Community changes", report["status"], len(mine) + len(report["unwired_offers"]))
    lines += ["Compared " + str(report["old_coverage"]["bundles"]) + " -> " +
              str(report["new_coverage"]["bundles"]) + " providers; " + str(report["event_count"]) + " events.",
              "Relevant: " + str(report["relevant_events"]) + "; unknown scope: " + str(report["unknown_scope_events"]) + "."]
    merged = report["new_coverage"].get("merged_providers") or []
    if merged:
        lines += ["Merged (listed more than once in the index, kept as one provider): " +
                  ", ".join(safe(m["provider"]) + " x" + str(m["bundles"]) for m in merged) + "."]
    lines += [""]
    counts = collections.Counter(e["relevance"] for e in report["events"])
    lines += readable.table(["Group", "Events", "Meaning"], [
        ["YOUR_APPS", counts["YOUR_APPS"], "providers or patches for apps you build: read these"],
        ["UNKNOWN_SCOPE", counts["UNKNOWN_SCOPE"], "the index ties them to no app"],
        ["OTHER_APPS", counts["OTHER_APPS"], "apps you do not build (folded)"],
        ["Unwired providers", len(report["unwired_offers"]), "offers for your apps from providers you do not use yet"]])
    lines += [""] + readable.details("What this report does not prove", ["- " + x for x in LIMITS]) + [""]
    head = ["Kind", "Provider", "Patch", "Fields", "Apps"]
    row = lambda e: [safe(e["kind"]), safe(e["provider"]), safe(e["patch"] or "(provider)"),
                     safe(", ".join(e["changed_fields"])), safe(", ".join(e["packages"]))]
    for relevance in ("YOUR_APPS", "UNKNOWN_SCOPE", "OTHER_APPS"):
        events = [e for e in report["events"] if e["relevance"] == relevance]
        lines += ["## " + relevance + " (" + str(len(events)) + ")"]
        if not events:
            lines += ["- none", ""]
            continue
        rows = readable.table(head, [row(e) for e in events])
        lines += (readable.details("All %d events" % len(events), rows) if relevance == "OTHER_APPS" else rows) + [""]
    lines += ["## Unwired providers for configured apps (" + str(len(report["unwired_offers"])) + ")"]
    lines += readable.table(["App package", "Provider", "Next step"],
                            [[safe(r["package"]), safe(r["provider"]), "review required"] for r in report["unwired_offers"]]) \
        if report["unwired_offers"] else ["- none"]
    return "\n".join(lines) + "\n"
