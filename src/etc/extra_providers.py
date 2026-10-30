#!/usr/bin/env python3
"""Validated provider sources which are intentionally outside the community index.

These repositories are observation-only inputs.  They are never targets for automatic
adoption; callers use the rows to make an otherwise invisible source discoverable.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

PATH = Path(__file__).resolve().with_name("extra-providers.json")
_IDENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,100}$")
_PACKAGE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+$")


def validate(data) -> list[dict]:
    """Validate and normalize the small checked-in source list.

    An object with ``providers`` is accepted for forward compatibility, while the
    checked-in file is a plain array to keep reviews easy.  Unknown fields are
    rejected so adding a field cannot silently become an executable instruction.
    """
    rows = data.get("providers") if isinstance(data, dict) else data
    if not isinstance(rows, list) or not rows or len(rows) > 100:
        raise ValueError("extra providers must be a non-empty array")
    out = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"owner", "repo", "packages", "why"}:
            raise ValueError("extra provider rows require owner, repo, packages and why")
        owner, repo, why, packages = row["owner"], row["repo"], row["why"], row["packages"]
        if not isinstance(owner, str) or not _IDENT.fullmatch(owner):
            raise ValueError("invalid extra provider owner")
        if not isinstance(repo, str) or not _IDENT.fullmatch(repo):
            raise ValueError("invalid extra provider repo")
        if not isinstance(why, str) or not why.strip() or len(why) > 500 or any(ord(c) < 32 for c in why):
            raise ValueError("invalid extra provider reason")
        if not isinstance(packages, list) or not packages or len(packages) > 30:
            raise ValueError("extra provider packages must be a non-empty array")
        if any(not isinstance(p, str) or not _PACKAGE.fullmatch(p) for p in packages):
            raise ValueError("invalid extra provider package")
        key = (owner.lower(), repo.lower())
        if key in seen:
            raise ValueError("duplicate extra provider")
        seen.add(key)
        out.append({"owner": owner, "repo": repo, "packages": list(dict.fromkeys(packages)), "why": why})
    return out


def load(path: Path | str | None = None) -> list[dict]:
    path = Path(path) if path is not None else PATH
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("cannot read extra providers") from exc
    return validate(data)
