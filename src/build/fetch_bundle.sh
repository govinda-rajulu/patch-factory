#!/bin/bash
# Fetch and verify exactly one .mpp bundle; preserve the caller's PUB/TAG/SIZE contract.
# Usage: fetch_bundle.sh HOST IDENT CHANNEL OUTPATH [EXPECTED_SHA256]
#   HOST    github | gitlab
#   IDENT   OWNER/REPO for github, numeric project id for gitlab
#   CHANNEL prerelease | latest
# Optional EXPECTED_SHA256 is a reviewed target extra-bundle pin.
# Prints PUB=, TAG=, SIZE= and SHA256= on success. Exits 1 with FB_ERROR on stderr otherwise.
set -euo pipefail
HOST="${1:?usage: fetch_bundle.sh HOST IDENT CHANNEL OUT}"
IDENT="${2:?ident required}"
CHANNEL="${3:-prerelease}"
OUT="${4:?out path required}"
EXPECTED="${5-}"
[[ "$#" -le 5 ]] || { echo "FB_ERROR too many arguments" >&2; exit 1; }

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ -n "$EXPECTED" ]]; then
  exec python3 "$SCRIPT_DIR/extra_bundle.py" "$HOST" "$IDENT" "$CHANNEL" "$OUT" "$EXPECTED"
fi
exec python3 "$SCRIPT_DIR/extra_bundle.py" "$HOST" "$IDENT" "$CHANNEL" "$OUT"
