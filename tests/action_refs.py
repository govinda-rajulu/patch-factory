"""Action identity/shape contracts, independent of a particular release number.

Behavior, permissions, ordering and runtime smoke remain separately mandatory.
This is not a declaration that an untested future major is compatible.
"""
import re


def references(text, action, pinned=False):
    values = re.findall(r"(?m)^\s*(?:-\s*)?uses:\s*" + re.escape(action) + r"@([^\s#]+)\s*(?:#.*)?$", text)
    if not values:
        raise ValueError("missing action: " + action)
    pattern = r"[0-9a-f]{40}" if pinned else r"(?:v[1-9][0-9]*(?:\.[0-9]+){0,2}|[0-9a-f]{40})"
    if not all(re.fullmatch(pattern, value) for value in values):
        raise ValueError("invalid immutable/versioned action reference: " + action)
    return set(values)


def same_reference(production, smoke, action, pinned=False):
    actual = references(production, action, pinned)
    exercised = references(smoke, action, pinned)
    if len(actual) != 1 or actual != exercised:
        raise ValueError("runtime smoke differs from production action: " + action)
    return actual
