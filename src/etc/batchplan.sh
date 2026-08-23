#!/bin/bash
set -euo pipefail
python3 - <<'PY' > /tmp/m.json
import json, os
want = [x.strip() for x in os.environ["RAW"].split(",") if x.strip()]
known = {t["id"] for t in json.load(open("src/targets.json"))}
bad = [w for w in want if w not in known]
if bad: raise SystemExit("unknown target ids: " + ", ".join(bad))
if not want: raise SystemExit("no target ids given")
print(json.dumps({"target": want}))
PY
echo "matrix=$(cat /tmp/m.json)" >> "$GITHUB_OUTPUT"
echo "planned: $(cat /tmp/m.json)"
