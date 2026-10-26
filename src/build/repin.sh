#!/bin/bash
# Recompute every pin from its own URL. Run deliberately by hand, never in a build.
set -euo pipefail
[ "${1:-}" = "--confirm-repin" ] || { echo "usage: $0 --confirm-repin" >&2; exit 2; }
P=src/build/TOOLING.sha256
[ -f "$P" ] && [ ! -L "$P" ] || { echo "::error::pin file missing or symlinked" >&2; exit 1; }
P_DIR=$(dirname -- "$P")
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
TMP_DIR=$(mktemp -d "${RUNNER_TEMP:-/tmp}/pf-repin.XXXXXX")
TMP_PIN=$(mktemp "$P_DIR/.TOOLING.sha256.repin.XXXXXX")
cleanup() { rm -rf -- "$TMP_DIR"; rm -f -- "$TMP_PIN"; }
trap cleanup EXIT
while IFS= read -r l || [ -n "$l" ]; do
  case "$l" in ''|'#'*) printf '%s\n' "$l" >> "$TMP_PIN"; continue ;; esac
  IFS='|' read -r n u w o <<<"$l"
  case "$u" in https://github.com/*) ;; *) echo "  FAILED    $n ($u) - URL is not approved HTTPS"; printf '%s\n' "$l" >> "$TMP_PIN"; continue ;; esac
  f=$(mktemp "$TMP_DIR/download.XXXXXX")
  if effective=$(curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
      --max-redirs 3 --max-filesize "${PF_TOOL_MAX_BYTES:-200M}" -o "$f" -w '%{url_effective}' "$u") && github_effective_host_ok "$effective"; then
    g=$(sha256sum "$f" | awk '{print $1}')
    if [ "$g" = "$w" ]; then echo "  unchanged $n"; else echo "  REPINNED  $n: ${w:0:16} -> ${g:0:16}"; fi
    printf '%s|%s|%s|%s\n' "$n" "$u" "$g" "$o" >> "$TMP_PIN"
  else
    echo "  FAILED    $n ($u) - keeping the old pin"; printf '%s\n' "$l" >> "$TMP_PIN"
  fi
  rm -f -- "$f"
done < "$P"
[ -s "$TMP_PIN" ] || { echo "::error::repin candidate is empty" >&2; exit 1; }
mv -f -- "$TMP_PIN" "$P"
trap - EXIT
rm -rf -- "$TMP_DIR"
# name|url|sha256|outfile   Regenerate deliberately: bash src/build/repin.sh --confirm-repin
