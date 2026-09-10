#!/bin/bash
# Fetch and verify exactly one .mpp bundle; preserve the caller's PUB/TAG/SIZE contract.
# Usage: fetch_bundle.sh HOST IDENT CHANNEL OUTPATH
#   HOST    github | gitlab
#   IDENT   OWNER/REPO for github, numeric project id for gitlab
#   CHANNEL prerelease | latest
# Prints PUB=, TAG=, SIZE= on success. Exits 1 with FB_ERROR on stderr otherwise.
set -euo pipefail
HOST="${1:?usage: fetch_bundle.sh HOST IDENT CHANNEL OUT}"
IDENT="${2:?ident required}"
CHANNEL="${3:-prerelease}"
OUT="${4:?out path required}"

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec python3 "$SCRIPT_DIR/extra_bundle.py" "$HOST" "$IDENT" "$CHANNEL" "$OUT"
