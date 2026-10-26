#!/bin/bash
# Download a pinned build tool and refuse it if the bytes are not the bytes we recorded.
# Pins live in src/build/TOOLING.sha256 as: name|url|sha256|outfile
# morphe-desktop is deliberately NOT pinned: build.sh asks for its "latest" release on purpose,
# because new provider bundles routinely need a newer patcher.
set -euo pipefail
P=src/build/TOOLING.sha256
NAME="${1:?usage: tooling.sh <name>}"
[ -f "$P" ] || { echo "::error::$P missing - cannot verify $NAME"; exit 1; }
LINE=$(grep -v '^#' "$P" | grep "^$NAME|" | head -1)
[ -n "$LINE" ] || { echo "::error::no pin for '$NAME' in $P"; exit 1; }
IFS='|' read -r _ URL WANT OUT <<<"$LINE"
[ -n "$URL" ] && [ -n "$WANT" ] && [ -n "$OUT" ] || { echo "::error::malformed pin line for $NAME"; exit 1; }
# W16o: F-10, enforce HTTPS and GitHub's reviewed host before downloading.
# W16o round 1: MED-2, allow only GitHub's documented release redirect hosts.
github_effective_host_ok() {
  python3 - "$1" <<'PY_HOST'
import sys
from urllib.parse import urlsplit
u = urlsplit(sys.argv[1])
if u.scheme != 'https' or u.username or u.password or u.port not in (None, 443) or not u.hostname:
    raise SystemExit(1)
h = u.hostname.lower().rstrip('.')
if h not in {'github.com', 'objects.githubusercontent.com', 'release-assets.githubusercontent.com'}:
    raise SystemExit(1)
PY_HOST
}
case "$URL" in https://github.com/*) ;; *) echo "::error::$NAME pin is not an approved HTTPS URL"; exit 1 ;; esac
[[ "$WANT" =~ ^[0-9a-fA-F]{64}$ ]] || { echo "::error::$NAME pin has an invalid SHA256"; exit 1; }
OUT_DIR=$(dirname -- "$OUT")
OUT_BASE=$(basename -- "$OUT")
[ -d "$OUT_DIR" ] || { echo "::error::tool destination directory missing: $OUT_DIR"; exit 1; }
[ ! -L "$OUT" ] || { echo "::error::refusing symlinked tool destination: $OUT"; exit 1; }
# W16o: F-10, keep the candidate beside the destination for an atomic verified rename.
TMP=$(mktemp "$OUT_DIR/.${OUT_BASE}.XXXXXX")
cleanup() { rm -f -- "$TMP"; }
trap cleanup EXIT
EFFECTIVE=$(curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
  --max-redirs 3 --max-filesize "${PF_TOOL_MAX_BYTES:-200M}" -o "$TMP" -w '%{url_effective}' "$URL") \
  || { echo "::error::$NAME download failed"; exit 1; }
github_effective_host_ok "$EFFECTIVE" || { echo "::error::$NAME redirect host is not approved"; exit 1; }
GOT=$(sha256sum "$TMP" | awk '{print $1}')
if [ "$GOT" != "$WANT" ]; then
  echo "::error::$NAME SHA256 MISMATCH - refusing to use it"
  echo "  url:      $URL"
  echo "  expected: $WANT"
  echo "  actual:   $GOT"
  echo "  If upstream legitimately re-uploaded, re-pin on purpose: bash src/build/repin.sh --confirm-repin"
  exit 1
fi
[ -f "$TMP" ] && [ ! -L "$TMP" ] || { echo "::error::$NAME candidate is not a regular file"; exit 1; }
mv -f -- "$TMP" "$OUT"
trap - EXIT
echo "[+] $NAME verified ($(wc -c < "$OUT") bytes, sha256 ${GOT:0:16}...)"
