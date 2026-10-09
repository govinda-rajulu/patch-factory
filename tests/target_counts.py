"""Target counts read from src/targets.json, so adding or removing an app through
"5. Add target" does not break contracts that pinned 14 or 15 (W4, 8 Oct 2026)."""
import json
from pathlib import Path

TARGETS = json.loads((Path(__file__).resolve().parents[1] / 'src/targets.json').read_text(encoding='utf-8'))
TOTAL = len(TARGETS)
LIVE = [t for t in TARGETS if t.get('enabled') is True]
ENABLED = len(LIVE)
# Provider rows the watch reads: every candidate plus every extra bundle of every enabled target.
# A disabled app keeps its folders and record but is not watched, built or imported (W5, 9 Oct 2026).
ROWS = sum(len(t.get('candidates') or []) + len(t.get('extra_bundles') or []) for t in LIVE)
CANDIDATES = sum(len(t.get('candidates') or []) for t in LIVE)
GITHUB_ROWS = sum(1 for t in LIVE for r in (t.get('candidates') or []) + (t.get('extra_bundles') or [])
                  if (r.get('host') or 'github') == 'github')
