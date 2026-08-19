#!/bin/bash
# Fetch exactly one .mpp bundle from a github or gitlab release.
# Usage: fetch_bundle.sh HOST IDENT CHANNEL OUTPATH
#   HOST    github | gitlab
#   IDENT   OWNER/REPO for github, numeric project id for gitlab
#   CHANNEL prerelease | latest
# Prints PUB=, TAG=, SIZE= on success. Exits 1 with FB_ERROR on stderr otherwise.
set -uo pipefail
HOST="${1:?usage: fetch_bundle.sh HOST IDENT CHANNEL OUT}"
IDENT="${2:?ident required}"
CHANNEL="${3:-prerelease}"
OUT="${4:?out path required}"

if [ "$HOST" = "gitlab" ]; then
  J=$(curl -sSL "https://gitlab.com/api/v4/projects/$IDENT/releases?per_page=20")
  if [ "$CHANNEL" = "prerelease" ]; then
    Q='first(.[])'
  else
    Q='first(.[] | select(.tag_name | test("-dev") | not))'
  fi
  PUB=$(jq -r "$Q"' | .released_at // ""' <<<"$J")
  TAG=$(jq -r "$Q"' | .tag_name // ""' <<<"$J")
  URL=$(jq -r "$Q"' | .assets.links[]? | select(.name | test("[.]mpp$")) | .url' <<<"$J" | head -1)
else
  J=$(curl -sSL ${GITHUB_TOKEN:+-H "Authorization: token $GITHUB_TOKEN"} \
    "https://api.github.com/repos/$IDENT/releases")
  if [ "$CHANNEL" = "prerelease" ]; then
    Q='first(.[])'
  else
    Q='first(.[] | select(.prerelease==false))'
  fi
  PUB=$(jq -r "$Q"' | .published_at // ""' <<<"$J")
  TAG=$(jq -r "$Q"' | .tag_name // ""' <<<"$J")
  URL=$(jq -r "$Q"' | .assets[] | select(.name | test("[.]mpp$")) | .browser_download_url' <<<"$J" | head -1)
fi

[ -n "$PUB" ] && [ "$PUB" != "null" ] || { echo "FB_ERROR no release for $HOST $IDENT $CHANNEL" >&2; exit 1; }
[ -n "$URL" ] && [ "$URL" != "null" ] || { echo "FB_ERROR no mpp asset in tag $TAG" >&2; exit 1; }

mkdir -p "$(dirname "$OUT")"
curl -sSL "$URL" -o "$OUT" || { echo "FB_ERROR download failed $URL" >&2; exit 1; }
SZ=$(wc -c < "$OUT")
[ "$SZ" -gt 100000 ] || { echo "FB_ERROR bundle only $SZ bytes, not an mpp" >&2; rm -f "$OUT"; exit 1; }
echo "PUB=$PUB"
echo "TAG=$TAG"
echo "SIZE=$SZ"
