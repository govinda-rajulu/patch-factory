#!/bin/bash
# Second store, same gates (owner design, 6 Oct 2026). Called by build.sh and
# source_download.sh after the configured store failed and before the qualified
# exact-version fallback. Trust does not change: the caller's package, version, SDK,
# pinned version-code and finished-identity gates still decide; only the store differs.
# Usage: try_other_store PKG APK_NAME APK_TYPE SRC RVER ANYVER ARCH DPI
try_other_store() {
  local pkg="$1" name="$2" type="$3" src="$4" rver="$5" anyver="$6" arch="$7" dpi="$8" alt rc
  if [ "$src" = "apkpure" ]; then alt=apkmirror; else alt=apkpure; fi
  if ! jq -e --arg p "$pkg" --arg s "$alt" '(.[$s][$p] // {}) | ((.list_url // .download_url) // "") | length > 0' src/build/helper/apps.json > /dev/null 2>&1; then
    echo "STORE_CHAIN no $alt mapping for $pkg; going to the qualified fallback"
    return 1
  fi
  echo "STORE_CHAIN $src failed for $pkg ${rver:-latest}; trying $alt"
  version="$rver"; lock_version=""; prefer_version=""
  if [ "$anyver" = "true" ]; then version=""; lock_version=1; fi
  if [ "$alt" = "apkpure" ]; then
    set +u; get_apkpure "$pkg" "$name" "$type"; rc=$?; set -u
  else
    near_version=1
    set +u; get_apk "$pkg" "$name" "$type" "$arch" "$dpi"; rc=$?; set -u
  fi
  if [ "$rc" -eq 0 ]; then echo "STORE_CHAIN used $alt"; fi
  return "$rc"
}
