"""Target counts read from src/targets.json, so adding or removing an app through
"5. Add target" does not break contracts that pinned 14 or 15 (W4, 8 Oct 2026)."""
import json
from pathlib import Path

TARGETS = json.loads((Path(__file__).resolve().parents[1] / 'src/targets.json').read_text(encoding='utf-8'))
TOTAL = len(TARGETS)
ENABLED = sum(t.get('enabled') is True for t in TARGETS)
# Provider rows the watch reads: every candidate plus every extra bundle of every target.
ROWS = sum(len(t.get('candidates') or []) + len(t.get('extra_bundles') or []) for t in TARGETS)
CANDIDATES = sum(len(t.get('candidates') or []) for t in TARGETS)
GITHUB_ROWS = sum(1 for t in TARGETS for r in (t.get('candidates') or []) + (t.get('extra_bundles') or [])
                  if (r.get('host') or 'github') == 'github')
