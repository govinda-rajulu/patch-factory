#!/usr/bin/env python3
"""Owner decision memory, src/patches/DECISIONS.json (packet W16j, 25 Oct 2026).

The owner decides a patch name once per app; any provider that offers the same name later
gets the same answer. Read-only helpers used by Selection watch and Needs you.
"""
import json
import re
from pathlib import Path

PATH = 'src/patches/DECISIONS.json'


def norm(name):
    """'[Feed] Block feed auto refresh' and 'Block Facebook automatic refresh (573)' style names
    compare without their leading [Tag], trailing (version) and punctuation."""
    s = str(name or '').lower()
    s = re.sub(r'^\s*\[[^\]]{1,30}\]\s*', '', s)
    s = re.sub(r'\s*\([^)]{0,30}\)\s*$', '', s)
    return ' '.join(re.findall(r'[a-z0-9]+', s))


def load(root='.'):
    if root is None:
        return {'names': [], 'watch': [], 'drop_providers': []}
    p = Path(root) / PATH
    if not p.is_file():
        return {'names': [], 'watch': [], 'drop_providers': []}
    d = json.loads(p.read_text(encoding='utf-8'))
    for k in ('names', 'watch', 'drop_providers'):
        d.setdefault(k, [])
    return d


def call(memory, target, name):
    """The owner's call ('take' or 'drop') for this app and name, with its row, or (None, None)."""
    key = norm(name)
    for row in memory.get('names', []):
        if row.get('target') == target and norm(row.get('name')) == key and row.get('call') in ('take', 'drop'):
            return row['call'], row
    return None, None


def provider_state(memory, target, repo):
    """'drop' for a provider the owner dropped, 'watch' (with its row) for a watched one, else None."""
    r = str(repo or '').lower()
    for row in memory.get('drop_providers', []):
        if row.get('target') == target and str(row.get('repo', '')).lower() == r:
            return 'drop', row
    for row in memory.get('watch', []):
        if row.get('target') == target and str(row.get('repo', '')).lower() == r:
            return 'watch', row
    return None, None
