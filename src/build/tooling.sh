#!/bin/bash
# Download a pinned build tool and refuse it if the bytes are not the bytes we recorded.
# Pins live in src/build/TOOLING.sha256 as: name|url|sha256|outfile
# morphe-desktop is deliberately NOT pinned: build.sh asks for its "latest" release on purpose,
# because new provider bundles routinely need a newer patcher.
set -uo pipefail
P=src/build/TOOLING.sha256
NAME="${1:?usage: tooling.sh <name>}"
[ -f "$P" ] || { echo "::error::$P missing - cannot verify $NAME"; exit 1; }
LINE=$(grep -v '^#' "$P" | grep "^$NAME|" | head -1)
[ -n "$LINE" ] || { echo "::error::no pin for '$NAME' in $P"; exit 1; }
IFS='|' read -r _ URL WANT OUT <<<"$LINE"
[ -n "$URL" ] && [ -n "$WANT" ] && [ -n "$OUT" ] || { echo "::error::malformed pin line for $NAME"; exit 1; }
wget -q -O "$OUT" "$URL" || { echo "::error::$NAME download failed: $URL"; rm -f "$OUT"; exit 1; }
GOT=$(sha256sum "$OUT" | awk '{print $1}')
if [ "$GOT" != "$WANT" ]; then
  echo "::error::$NAME SHA256 MISMATCH - refusing to use it"
  echo "  url:      $URL"
  echo "  expected: $WANT"
  echo "  actual:   $GOT"
  echo "  If upstream legitimately re-uploaded, re-pin on purpose: bash src/build/repin.sh"
  rm -f "$OUT"
  exit 1
fi
echo "[+] $NAME verified ($(wc -c < "$OUT") bytes, sha256 ${GOT:0:16}...)"
