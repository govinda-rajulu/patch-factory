#!/usr/bin/env python3
"""Longest build first (owner, 21 Oct 2026, W15c).

A matrix with max-parallel 6 finishes sooner when the longest jobs start first: on the
20 Oct batch (run 39481109866) the measured minutes give 12.1 min in the requested order and
10.8 min longest first. Only the order changes; the set of apps is exactly the request.
Minutes live in src/etc/build-minutes.json. An app not listed starts first, because an unknown
job is safest treated as long. Equal minutes keep the requested order.
"""
import json
import math
from pathlib import Path

FILE = 'src/etc/build-minutes.json'


def minutes(root):
    p = Path(root) / FILE
    if not p.is_file():
        return {}
    doc = json.loads(p.read_text(encoding='utf-8'))
    table = doc.get('minutes') if isinstance(doc, dict) else None
    if not isinstance(table, dict) or not all(
            isinstance(k, str) and type(v) in (int, float) and math.isfinite(v) and v > 0 for k, v in table.items()):
        raise ValueError('build-minutes.json: minutes must map app ids to positive numbers')
    return table


def order(root, ids):
    table = minutes(root)
    ranked = sorted(enumerate(ids), key=lambda p: (-table.get(p[1], math.inf), p[0]))
    return [i for _, i in ranked]
